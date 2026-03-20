"""
Orquestador principal.
- Carga namespace + agentes
- Planifica tareas
- Mantiene sesion interactiva esperando instrucciones
- Actualiza el dashboard en tiempo real
"""
from __future__ import annotations

import logging
import os
import threading
import time
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

        # Flag para solicitar skip de tareas pendientes
        self._skip_event = threading.Event()

    # ─── Sesion interactiva ──────────────────────────────────────────

    def interactive_session(self):
        """
        Loop principal: arranca el dashboard y espera tareas del usuario.
        El orquestador se mantiene encendido hasta que el usuario escriba 'salir'.
        """
        with Dashboard(self.state) as dash:
            while True:
                dash.refresh()
                try:
                    raw = dash.get_input("\n  tarea > ").strip()
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

                # Ejecutar la tarea en hilo de fondo; hilo principal refresca el display
                self.state.current_task_description = raw
                self._skip_event.clear()
                dash.refresh()

                task_error: list[Exception | None] = [None]
                task_done = threading.Event()

                def _run():
                    try:
                        self._run_task(raw)
                    except Exception as e:
                        task_error[0] = e
                    finally:
                        task_done.set()

                threading.Thread(target=_run, daemon=True).start()

                while not task_done.wait(timeout=0.3):
                    dash.refresh()
                    if self._read_skip_key():
                        self._skip_event.set()
                        self.state.current_task_description = raw + "  [skip →]"

                if task_error[0]:
                    self._handle_task_error(task_error[0], dash)

                # Actualizar metricas
                metrics = self.logger.summary()
                self.state.update_metrics(
                    tokens=metrics["tokens_input"] + metrics["tokens_output"],
                    cost=metrics["cost_usd"],
                    elapsed=metrics["elapsed"],
                )
                dash.refresh()

        self.logger.log_session_end()
        print_info("Sesion terminada.")
        self.logger.summary()

    # ─── Ejecucion de una tarea ──────────────────────────────────────

    def _run_task(self, task_description: str):
        """
        Planifica y ejecuta una tarea usando el Crew de agentes.
        Primero el arquitecto analiza, luego delega a los agentes correctos.
        Se ejecuta en un hilo de fondo; solo actualiza el estado (self.state).
        """
        # 1. Planificacion inicial con el arquitecto (si esta activo)
        plan = self._plan_task(task_description)

        # 2. Crear tareas en el dashboard
        task_ids = []
        for step in plan:
            tid = str(uuid.uuid4())[:8]
            self.state.add_task(tid, step["description"], step["agent"])
            task_ids.append((tid, step))

        # 3. Ejecutar cada paso del plan
        for tid, step in task_ids:
            if self._skip_event.is_set():
                self.state.skip_task(tid)
                continue

            self.state.start_task(tid)

            try:
                result = self._execute_step(step, task_description)
                files = self._write_tool.modified_files.copy()
                self._write_tool.modified_files.clear()

                self.state.complete_task(tid, files=files, summary=result[:200])
                self.logger.log_agent_output(
                    agent=step["agent"],
                    task=step["description"],
                    output=result,
                    files=files,
                    status="done",
                )
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
                self.logger.log_agent_output(
                    agent=step["agent"],
                    task=step["description"],
                    output=error_msg,
                    files=[],
                    status="failed",
                )
                self.memory.add_task(TaskMemory(
                    task=step["description"],
                    agent=step["agent"],
                    status="failed",
                    summary=error_msg,
                ))


    # ─── Planificacion ───────────────────────────────────────────────

    _SINGLE_AGENT_KEYWORDS = (
        "lee ", "leer ", "revisa ", "revisar ", "analiza ", "analizar ",
        "muestra ", "mostrar ", "explica ", "explicar ", "busca ", "buscar ",
        "lista ", "listar ", "describe ", "describir ", "resume ", "resumir ",
    )

    def _plan_task(self, task_description: str) -> list[dict]:
        """
        El arquitecto divide la tarea en pasos.
        Para tareas de lectura/analisis simples, asigna directamente sin
        llamar al arquitecto para ahorrar tokens.
        """
        architect_cfg = next(
            (a for a in self.agent_configs if a.name == "architect"), None
        )

        # Deteccion rapida: tareas que claramente son de un solo agente
        task_lower = task_description.lower().strip()
        is_simple = any(task_lower.startswith(kw) for kw in self._SINGLE_AGENT_KEYWORDS)
        if is_simple or not architect_cfg:
            target = self._guess_agent(task_description)
            return [{"agent": target, "description": task_description}]

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

        try:
            usage = result.token_usage
            if usage:
                self.logger.log_llm_call(
                    model=architect_cfg.model,
                    input_tokens=getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0),
                    output_tokens=getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0),
                    agent="architect",
                    task=f"plan: {task_description[:60]}",
                )
        except Exception:
            pass

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

    _RATE_LIMIT_SIGNALS = ("429", "too many requests", "rate limit", "invalid response from llm call")
    _RETRY_WAITS = [30, 60, 120]  # segundos entre reintentos

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(sig in msg for sig in Orchestrator._RATE_LIMIT_SIGNALS)

    def _execute_step(self, step: dict, original_task: str) -> str:
        log = logging.getLogger("agent-workspace")
        for attempt, wait in enumerate([0] + Orchestrator._RETRY_WAITS):
            if wait:
                log.warning(
                    f"[retry {attempt}/{len(Orchestrator._RETRY_WAITS)}] "
                    f"agente '{step['agent']}' — esperando {wait}s antes de reintentar..."
                )
                time.sleep(wait)
            try:
                return self._call_crew(step, original_task)
            except Exception as e:
                if self._is_rate_limit_error(e) and attempt < len(Orchestrator._RETRY_WAITS):
                    continue
                raise

    def _call_crew(self, step: dict, original_task: str) -> str:
        agent_name = step["agent"]
        agent_cfg = next((a for a in self.agent_configs if a.name == agent_name), None)
        if not agent_cfg:
            raise ValueError(f"Agente no encontrado: {agent_name}")

        crewai_agent = self._build_crewai_agent(agent_cfg)

        description = f"""
{step['description']}

Contexto:
- Tarea: {original_task[:200]}
- Stack: {', '.join(self.ns.stack)}
- Proyecto: {self.project_root}
- Historial: {self.memory.summary_for_agents()}

Estandares (fragmento):
{self.ns.standards[:400] if self.ns.standards else '(sin estandares)'}

Reglas (fragmento):
{self.ns.rules[:300] if self.ns.rules else '(sin reglas)'}

- Lee archivos antes de modificar. Resume en 2-3 lineas al terminar.
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

        # Registrar tokens reales del resultado
        try:
            usage = result.token_usage
            if usage:
                self.logger.log_llm_call(
                    model=agent_cfg.model,
                    input_tokens=getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0),
                    output_tokens=getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0),
                    agent=agent_name,
                    task=step.get("description", "")[:80],
                )
        except Exception:
            pass

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
            lines.append(f"- **{s.name}**: {s.description}")
            lines.append(f"  Instruccion en: {s.path / 'setup.md'}")

        lines.append(
            "\nAntes de aplicar una skill, lee su setup.md con la herramienta de lectura de archivos."
        )
        return "\n".join(lines)

    def _guess_agent(self, task_description: str) -> str:
        """Elige el agente mas probable sin llamar al LLM."""
        task_lower = task_description.lower()
        names = {a.name for a in self.agent_configs}
        if "frontend" in names and any(w in task_lower for w in ("front", "react", "componente", "ui", "css", "tsx", "jsx", "page", "vista")):
            return "frontend"
        if "backend" in names and any(w in task_lower for w in ("back", "api", "endpoint", "service", "controller", "dto", "entity", "migration", "c#", ".net")):
            return "backend"
        if "qa" in names and any(w in task_lower for w in ("test", "prueba", "spec", "e2e", "playwright")):
            return "qa"
        # fallback: primer agente no-arquitecto
        return next((a.name for a in self.agent_configs if a.name != "architect"), self.agent_configs[0].name)

    # ─── Skip de tareas ──────────────────────────────────────────────

    @staticmethod
    def _read_skip_key() -> bool:
        """Devuelve True si el usuario presiono 's' o 'S'. No bloquea."""
        try:
            import msvcrt  # Windows
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                return ch in (b"s", b"S")
        except ImportError:
            import select, sys, tty, termios
            if select.select([sys.stdin], [], [], 0)[0]:
                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                try:
                    tty.setraw(fd)
                    return sys.stdin.read(1).lower() == "s"
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return False

    # ─── Manejo de errores ───────────────────────────────────────────

    def _handle_task_error(self, error: Exception, dash: "Dashboard"):
        """Muestra errores de tarea de forma limpia sin crashear la sesion."""
        from anthropic import AuthenticationError

        if isinstance(error, AuthenticationError):
            msg = "API key invalida. Edita .env y agrega tu ANTHROPIC_API_KEY real."
        else:
            msg = str(error)[:200]

        print_error(msg)
        self.state.current_task_description = f"[error] {msg[:80]}"
        dash.refresh()

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
