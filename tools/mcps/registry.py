"""
Registry central de MCPs.
El orquestador usa este módulo para cargar las tools de cada agente
según los MCPs declarados en su YAML, sin hardcodear nada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from crewai.tools import BaseTool


@dataclass
class MCPDefinition:
    name: str
    description: str
    roles: list[str]           # qué roles se benefician de este MCP
    requires_env: list[str]    # vars de entorno requeridas (vacío = sin requisitos)
    optional_env: list[str]    # vars de entorno opcionales
    factory: Callable          # función que construye las tools
    install_hint: str = ""     # mensaje de ayuda si falta algo


# ─── Factories ───────────────────────────────────────────────────────
# Cada factory acepta **kwargs (incluye project_root cuando aplique)
# y retorna (list[BaseTool], dict) donde el dict tiene extras opcionales
# como {"write_tool": write_tool}.

def _filesystem_factory(project_root: Path | None = None, **kwargs) -> tuple[list[BaseTool], dict]:
    from tools.mcps.filesystem import get_filesystem_tools, WriteFileTool
    root = Path(project_root) if project_root else Path(".")
    tools, write_tool = get_filesystem_tools(root)
    return tools, {"write_tool": write_tool}


def _git_factory(project_root: Path | None = None, **kwargs) -> tuple[list[BaseTool], dict]:
    from tools.mcps.git import get_git_tools
    root = Path(project_root) if project_root else Path(".")
    return get_git_tools(root), {}


def _fetch_factory(**kwargs) -> tuple[list[BaseTool], dict]:
    from tools.mcps.fetch import get_fetch_tools
    return get_fetch_tools(), {}


def _shell_factory(project_root: Path | None = None, **kwargs) -> tuple[list[BaseTool], dict]:
    from tools.mcps.shell import get_shell_tools
    root = Path(project_root) if project_root else Path(".")
    return get_shell_tools(root), {}


def _sequential_thinking_factory(**kwargs) -> tuple[list[BaseTool], dict]:
    from tools.mcps.sequential_thinking import get_sequential_thinking_tools
    return get_sequential_thinking_tools(), {}


def _mermaid_factory(project_root: Path | None = None, **kwargs) -> tuple[list[BaseTool], dict]:
    from tools.mcps.mermaid import get_mermaid_tools
    root = Path(project_root) if project_root else Path(".")
    return get_mermaid_tools(root), {}


# ─── Registry ────────────────────────────────────────────────────────

MCP_REGISTRY: dict[str, MCPDefinition] = {
    "filesystem": MCPDefinition(
        name="filesystem",
        description="Lectura y escritura de archivos dentro del proyecto activo (sandboxed)",
        roles=["architect", "backend", "frontend", "qa", "devops"],
        requires_env=[],
        optional_env=[],
        factory=_filesystem_factory,
    ),
    "git": MCPDefinition(
        name="git",
        description="Inspección del repo git local (solo lectura: status, diff, log, branches)",
        roles=["architect", "backend", "frontend", "qa", "devops"],
        requires_env=[],
        optional_env=[],
        factory=_git_factory,
        install_hint="Instala git: https://git-scm.com/downloads",
    ),
    "fetch": MCPDefinition(
        name="fetch",
        description="Obtener documentación oficial y contenido de URLs",
        roles=["architect", "backend", "frontend", "devops"],
        requires_env=[],
        optional_env=[],
        factory=_fetch_factory,
    ),
    "shell": MCPDefinition(
        name="shell",
        description="Ejecutar comandos de build, tests y linting dentro del proyecto (whitelist)",
        roles=["backend", "frontend", "qa", "devops"],
        requires_env=[],
        optional_env=["SHELL_ALLOWED_COMMANDS", "SHELL_TIMEOUT"],
        factory=_shell_factory,
    ),
    "sequential_thinking": MCPDefinition(
        name="sequential_thinking",
        description="Razonamiento estructurado para problemas complejos de diseño",
        roles=["architect"],
        requires_env=[],
        optional_env=[],
        factory=_sequential_thinking_factory,
    ),
    "mermaid": MCPDefinition(
        name="mermaid",
        description="Generación y guardado de diagramas Mermaid (flujo, secuencia, ER, clases)",
        roles=["architect", "devops"],
        requires_env=[],
        optional_env=[],
        factory=_mermaid_factory,
    ),
}


# ─── API pública ─────────────────────────────────────────────────────

def get_mcp(name: str) -> MCPDefinition | None:
    """Retorna la definición de un MCP por nombre, o None si no existe."""
    return MCP_REGISTRY.get(name)


def list_available() -> list[str]:
    """Retorna los nombres de todos los MCPs disponibles."""
    return list(MCP_REGISTRY.keys())


def missing_env(mcp_name: str) -> list[str]:
    """
    Retorna la lista de variables de entorno requeridas que faltan.
    Lista vacía significa que el MCP está listo para usarse.
    """
    import os
    mcp = MCP_REGISTRY.get(mcp_name)
    if not mcp:
        return []
    return [var for var in mcp.requires_env if not os.getenv(var)]
