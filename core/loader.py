"""
Carga y valida los archivos YAML de namespace y agentes.
Retorna objetos Python listos para usar en el orquestador.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parent.parent
NAMESPACES_DIR = ROOT / "namespaces"
AGENTS_DIR = ROOT / "agents"


# ─── Modelos de datos ────────────────────────────────────────────────

@dataclass
class AgentConfig:
    name: str
    role: str
    goal: str
    backstory: str
    model: str
    skills: list[str]
    mcps: list[str]
    responsibilities: list[str] = field(default_factory=list)
    max_iter: int = 10
    verbose: bool = False


@dataclass
class NamespaceSkill:
    name: str
    description: str
    path: Path              # ruta absoluta a la carpeta de la skill
    roles: list[str]        # agentes que pueden instalarla (vacio = todos)
    has_templates: bool     # si existe la subcarpeta templates/
    has_python: bool        # si existe skill.py
    instruction: str        # contenido de setup.md ya leido


@dataclass
class NamespaceConfig:
    name: str
    description: str
    projects_path: Path
    stack: list[str]
    methodology: str
    branching: str
    commits: str
    agents: list[str]
    mcps: list[str]
    skills: list[str]
    standards: str = ""
    rules: str = ""
    namespace_skills: list[NamespaceSkill] = field(default_factory=list)


# ─── Loaders ─────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_base_agent() -> dict[str, Any]:
    base_path = AGENTS_DIR / "_base.yaml"
    return _load_yaml(base_path) if base_path.exists() else {}


def load_agent(name: str) -> AgentConfig:
    """Carga un agente fusionando _base.yaml con <name>.yaml."""
    path = AGENTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Agente no encontrado: agents/{name}.yaml")

    base = _load_base_agent()
    data = _load_yaml(path)
    merged = {**base, **data}

    return AgentConfig(
        name=merged["name"],
        role=merged["role"],
        goal=merged["goal"].strip(),
        backstory=merged["backstory"].strip(),
        model=merged.get("model", os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")),
        skills=merged.get("skills", []),
        mcps=merged.get("mcps", []),
        responsibilities=merged.get("responsibilities", []),
        max_iter=merged.get("max_iter", 10),
        verbose=merged.get("verbose", False),
    )


def _validate_projects_path(raw: str, namespace_name: str) -> Path:
    p = Path(raw)
    if not p.exists():
        raise FileNotFoundError(
            f"projects_path '{p}' no existe en disco.\n"
            f"Verifica namespaces/{namespace_name}/namespace.yaml"
        )
    return p


def load_namespace(name: str) -> NamespaceConfig:
    """Carga un namespace y todos sus archivos de contexto."""
    ns_dir = NAMESPACES_DIR / name
    if not ns_dir.exists():
        raise FileNotFoundError(
            f"Namespace '{name}' no encontrado en namespaces/.\n"
            f"Crealo con: python run/init.py --name {name}"
        )

    data = _load_yaml(ns_dir / "namespace.yaml")
    workflow = data.get("workflow", {})

    # Leer archivos de contexto
    standards = _read_md(ns_dir / "standards.md")
    rules = _read_md(ns_dir / "rules.md")

    ns_skills = load_namespace_skills(ns_dir, data.get("namespace_skills") or [])

    return NamespaceConfig(
        name=data["name"],
        description=data.get("description", ""),
        projects_path=_validate_projects_path(data["projects_path"], name),
        stack=data.get("stack", []),
        methodology=workflow.get("methodology", "libre"),
        branching=workflow.get("branching", "feature"),
        commits=workflow.get("commits", "libre"),
        agents=data.get("agents", []),
        mcps=data.get("mcps", ["filesystem"]),
        skills=data.get("skills", ["codegen"]),
        standards=standards,
        rules=rules,
        namespace_skills=ns_skills,
    )


def _read_md(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_namespace_skills(ns_dir: Path, skills_config: list) -> list[NamespaceSkill]:
    """
    Carga las namespace skills declaradas en el namespace.yaml.
    Cada skill debe tener un setup.md; si no existe, se omite con warning.
    """
    skills = []
    for entry in skills_config:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        if not name:
            continue
        rel_path = entry.get("path", f"skills/{name}")
        skill_dir = ns_dir / rel_path
        setup_md = skill_dir / "setup.md"
        if not setup_md.exists():
            print(f"[loader] Advertencia: skill '{name}' sin setup.md en {skill_dir} — omitida")
            continue
        skills.append(NamespaceSkill(
            name=name,
            description=entry.get("description", ""),
            path=skill_dir,
            roles=entry.get("roles", []),
            has_templates=(skill_dir / "templates").is_dir(),
            has_python=(skill_dir / "skill.py").exists(),
            instruction="",  # se lee bajo demanda, no al arrancar
        ))
    return skills


def load_namespace_agents(ns: NamespaceConfig) -> list[AgentConfig]:
    """Carga todos los agentes activos del namespace."""
    agents = []
    for agent_name in ns.agents:
        try:
            agents.append(load_agent(agent_name))
        except FileNotFoundError as e:
            print(f"[loader] Advertencia: {e}")
    return agents
