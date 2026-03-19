"""
Orquestador principal.
- Carga namespace + agentes
- Planifica tareas
- Mantiene sesion interactiva esperando instrucciones
- Actualiza el dashboard en tiempo real
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from core.loader import NamespaceConfig, AgentConfig, load_namespace, load_namespace_agents
from core.memory import SessionMemory, TaskMemory
from core.logger import SessionLogger
from dashboard.state import DashboardState, TaskStatus
from dashboard.ui import Dashboard, print_welcome, print_error, print_info
from tools.mcps.filesystem import WriteFileTool
from tools.mcps.registry import get_mcp, missing_env

load_dotenv()


class Orchestrator:
    def __init__(self, namespace_name: str, project_name: str | None = None):
        self.ns: NamespaceConfig = load_namespace(namespace_name)
        self.project_name = project_name or ""
        self.project_root = self._resolve_project_root(project_name)

        self.agent_configs: list[AgentConfig] = load_namespace_agents(self.ns)
        self.memory = SessionMemory(namespace_name, project_name or "general")
        self.logger = SessionLogger(namespace_name, project_name or "general")
        self.state = DashboardState(
            namespace=namespace_name,
            project=project_name or "",
        )

        # write_tool para rastrear archivos modificados (se actualiza al cargar tools por agente)
        self._write_tool = WriteFileTool(project_root=self.project_root)

        # Poblar skills en el dashboard
        self.state.namespace_skills = [s.name for s in self.ns.namespace_skills]

    # ─── Sesion interactiva ──────────────────────────────────────────

    def interactive_session(self):
        """
        Loop principal: arranca el dashboard y espera tareas del usuario.
        El orquestador se mantiene encendido hasta que el usuario escriba 'salir'.
        """
        print_welcome(self.ns.name, self.project_name)

        with Dashboard(self.state) as dash:
            while True:
                dash.refresh()
                try:
                    raw = input("\n  tarea > ").strip()
                except (KeyboardInterrupt, EOFError):
                    break

                if not raw:
                    continue

                cmd = raw.lower()
                if cmd in ("salir", "exit", "q", "quit"):
                    break
                if cmd == "estado":
                    dash.refresh()
                    continue
                if cmd.startswith("proyecto "):
                    new_project = cmd.replace("proyecto ", "").strip()
                    self._switch_project(new_project)
                    print_info(f"Proyecto cambiado a: {new_project}")
                    dash.refresh()
                    continue

                # Ejecutar la tarea
                self.state.current_task_description = raw
                dash.refresh()
                self._run_task(raw, dash)

                # Actualizar metricas
                metrics = self.logger.summary()
                self.state.update_metrics(
                    tokens=metrics["tokens_input"] + metrics["tokens_output"],
                    cost=metrics["cost_usd"],
                    elapsed=metrics["elapsed"],
                )
                dash.refresh()

        print_info("Sesion terminada.")
        self.logger.summary()

    # ─── Ejecucion de una tarea ──────────────────────────────────────

    def _run_task(self, task_description: str, dash: Dashboard | None = None):
        """
        Planifica y ejecuta una tarea usando el Crew de agentes.
        Primero el arquitecto analiza, luego delega a los agentes correctos.
        """
        # 1. Planificacion inicial con el arquitecto (si esta activo)
        plan = self._plan_task(task_description)

        # 2. Crear tareas en el dashboard
        task_ids = []
        for step in plan:
            tid = str(uuid.uuid4())[:8]
            self.state.add_task(tid, step["description"], step["agent"])
            task_ids.append((tid, step))
            if dash:
                dash.refresh()

        # 3. Ejecutar cada paso del plan
        for tid, step in task_ids:
            self.state.start_task(tid)
            if dash:
                dash.refresh()

            try:
                result = self._execute_step(step, task_description)
                files = self._write_tool.modified_files.copy()
                self._write_tool.modified_files.clear()

                self.state.complete_task(tid, files=files, summary=result[:200])
                self.memory.add_task(TaskMemory(
                    task=step["description"],
                    agent=step["agent"],
                    status="done",
                    summary=result[:300],
                    files_modified=files,
                ))

            except Exception as e:
                error_msg = str(e)
                self.state.fail_task(tid, alert=error_msg[:120])
                self.memory.add_task(TaskMemory(
                    task=step["description"],
                    agent=step["agent"],
                    status="failed",
                    summary=error_msg,
                ))

            if dash:
                dash.refresh()

    # ─── Planificacion ───────────────────────────────────────────────

    def _plan_task(self, task_description: str) -> list[dict]:
        """
        El arquitecto (o el orquestador si no hay arquitecto) divide
        la tarea en pasos asignados a agentes especificos.
        """
        architect_cfg = next(
            (a for a in self.agent_configs if a.name == "architect"), None
        )

        if not architect_cfg:
            # Sin arquitecto: asignar al primer agente disponible
            first = self.agent_configs[0] if self.agent_configs else None
            if not first:
                return []
            return [{"agent": first.name, "description": task_description}]

        # Usar el arquitecto para planificar
        architect = self._build_crewai_agent(architect_cfg)
        plan_task = Task(
            description=f"""
Analiza esta tarea y dividela en pasos concretos.
Asigna cada paso al agente mas adecuado de: {[a.name for a in self.agent_configs]}.

Tarea: {task_description}

Contexto del namespace:
- Stack: {', '.join(self.ns.stack)}
- Proyecto activo: {self.project_name or 'sin proyecto'}
- Historial de sesion: {self.memory.summary_for_agents()}

Responde UNICAMENTE con una lista YAML con este formato exacto:
- agent: <nombre_agente>
  description: <descripcion clara del paso>
- agent: <nombre_agente>
  description: <descripcion clara del paso>

Maximo 5 pasos. Sin texto adicional.
""",
            agent=architect,
            expected_output="Lista YAML de pasos con agent y description",
        )

        crew = Crew(agents=[architect], tasks=[plan_task], verbose=False)
        result = crew.kickoff()

        return self._parse_plan(str(result))

    def _parse_plan(self, raw: str) -> list[dict]:
        """Parsea el YAML de plan retornado por el arquitecto."""
        import yaml
        import re

        # Limpiar markdown si el modelo envolvio en ```yaml
        clean = re.sub(r"```(?:yaml)?|```", "", raw).strip()
        try:
            steps = yaml.safe_load(clean)
            if isinstance(steps, list):
                valid = []
                for s in steps:
                    if isinstance(s, dict) and "agent" in s and "description" in s:
                        # Verificar que el agente existe
                        if any(a.name == s["agent"] for a in self.agent_configs):
                            valid.append(s)
                if valid:
                    return valid
        except Exception:
            pass

        # Fallback: asignar al primer agente no-arquitecto
        fallback_agent = next(
            (a.name for a in self.agent_configs if a.name != "architect"),
            self.agent_configs[0].name if self.agent_configs else "backend",
        )
        return [{"agent": fallback_agent, "description": raw[:200]}]

    # ─── Ejecucion de paso ───────────────────────────────────────────

    def _execute_step(self, step: dict, original_task: str) -> str:
        agent_name = step["agent"]
        agent_cfg = next((a for a in self.agent_configs if a.name == agent_name), None)
        if not agent_cfg:
            raise ValueError(f"Agente no encontrado: {agent_name}")

        crewai_agent = self._build_crewai_agent(agent_cfg)

        description = f"""
{step['description']}

Contexto completo:
- Tarea original: {original_task}
- Namespace: {self.ns.name} — {self.ns.description}
- Stack: {', '.join(self.ns.stack)}
- Proyecto activo: {self.project_root}
- Metodologia: {self.ns.methodology}
- Historial: {self.memory.summary_for_agents()}

Estandares a seguir:
{self.ns.standards[:800] if self.ns.standards else '(sin estandares definidos aun)'}

Reglas:
{self.ns.rules[:600] if self.ns.rules else '(sin reglas definidas aun)'}

Instrucciones:
- Usa las herramientas disponibles para leer archivos existentes antes de escribir
- Sigue los estandares del namespace
- Si encuentras algo que bloquea la tarea, describelo claramente
- Al terminar, resume que hiciste en 2-3 lineas
"""
        skills_ctx = self._namespace_skills_context(agent_cfg.name)
        if skills_ctx:
            description += f"\n\n{skills_ctx}"

        task = Task(
            description=description,
            agent=crewai_agent,
            expected_output="Resumen de lo implementado y archivos modificados",
        )

        crew = Crew(
            agents=[crewai_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=os.getenv("LOG_LEVEL", "INFO") == "DEBUG",
        )

        result = crew.kickoff()
        return str(result)

    # ─── Construccion de agentes CrewAI ─────────────────────────────

    def _load_tools_for_agent(self, agent_cfg: AgentConfig) -> list:
        """
        Carga las tools del agente segun los MCPs declarados en su YAML.
        Usa el registry central — no hardcodea ninguna tool.
        """
        tools = []
        for mcp_name in agent_cfg.mcps:
            mcp_def = get_mcp(mcp_name)
            if not mcp_def:
                print(f"[warn] MCP '{mcp_name}' desconocido — omitido para agente '{agent_cfg.name}'")
                continue
            missing = missing_env(mcp_name)
            if missing:
                print(f"[warn] MCP '{mcp_name}' omitido: faltan variables de entorno: {missing}")
                continue
            try:
                agent_tools, extras = mcp_def.factory(project_root=self.project_root)
                tools.extend(agent_tools)
                if "write_tool" in extras:
                    self._write_tool = extras["write_tool"]
            except Exception as e:
                print(f"[warn] Error cargando MCP '{mcp_name}': {e}")
        return tools

    def _build_crewai_agent(self, cfg: AgentConfig) -> Agent:
        from crewai import LLM

        llm = LLM(
            model=f"anthropic/{cfg.model}",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

        return Agent(
            role=cfg.role,
            goal=cfg.goal,
            backstory=cfg.backstory,
            llm=llm,
            tools=self._load_tools_for_agent(cfg),
            max_iter=cfg.max_iter,
            verbose=cfg.verbose,
        )

    # ─── Namespace skills ────────────────────────────────────────────

    def _namespace_skills_context(self, agent_role: str) -> str:
        """
        Genera el bloque de contexto de namespace skills para un agente.
        Solo incluye las skills cuyo `roles` incluye el rol del agente,
        o todas si `roles` esta vacio.
        """
        skills = [
            s for s in self.ns.namespace_skills
            if not s.roles or agent_role in s.roles
        ]
        if not skills:
            return ""

        lines = ["## Namespace skills disponibles para instalar en proyectos"]
        lines.append(
            "Puedes instalar cualquiera de estas skills en el proyecto activo "
            "si el usuario lo solicita o si identificas que el proyecto la necesita."
        )
        lines.append(
            "Para instalar una skill, lee su instruccion completa y sigue los pasos.\n"
        )
        for s in skills:
            lines.append(f"### {s.name}")
            lines.append(f"{s.description}")
            lines.append(f"Instruccion completa:\n{s.instruction}\n")

        return "\n".join(lines)

    # ─── Cambio de proyecto ──────────────────────────────────────────

    def _switch_project(self, project_name: str):
        self.project_name = project_name
        self.project_root = self._resolve_project_root(project_name)
        self._write_tool = WriteFileTool(project_root=self.project_root)
        self.state.project = project_name

    def _resolve_project_root(self, project_name: str | None) -> Path:
        if not project_name:
            return self.ns.projects_path

        # Buscar en la carpeta de proyectos del namespace
        candidate = self.ns.projects_path / project_name
        if candidate.exists():
            return candidate.resolve()

        # Si no existe, usar projects_path como raiz y avisar
        print_info(f"Proyecto '{project_name}' no encontrado en {self.ns.projects_path}. Usando raiz del namespace.")
        return self.ns.projects_path.resolve()
