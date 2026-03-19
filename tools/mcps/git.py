"""
MCP de Git: inspeccion del repo local (solo lectura).
Los agentes pueden leer el estado del repo pero NUNCA escriben en git.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ─── Schemas ─────────────────────────────────────────────────────────

class GitDiffInput(BaseModel):
    file_path: str = Field(default="", description="Ruta relativa al archivo a differenciar (vacio = todo)")

class GitLogInput(BaseModel):
    limit: int = Field(default=20, description="Numero de commits a mostrar (max 30)")

class GitShowFileInput(BaseModel):
    ref: str = Field(description="Ref git (commit hash, rama, tag). Ej: HEAD, main, abc1234")
    file_path: str = Field(description="Ruta relativa al archivo dentro del repo")

class EmptyInput(BaseModel):
    pass


# ─── Helpers ─────────────────────────────────────────────────────────

def _git_available() -> bool:
    return shutil.which("git") is not None

def _run_git(args: list[str], cwd: Path) -> tuple[str, int]:
    """Ejecuta un comando git y retorna (output, returncode)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=15,
    )
    output = result.stdout or result.stderr
    return output.strip(), result.returncode


# ─── Tools ───────────────────────────────────────────────────────────

class GitStatusTool(BaseTool):
    name: str = "git_status"
    description: str = "Muestra el estado actual del repo git (archivos modificados, staged, untracked)."
    args_schema: type[BaseModel] = EmptyInput
    project_root: Path = Path(".")

    def _run(self) -> str:
        if not _git_available():
            return "Error: git no esta instalado en el sistema."
        out, code = _run_git(["status", "--short", "--branch"], self.project_root)
        if code != 0:
            return f"Error ejecutando git status: {out}"
        return out or "(nada que reportar — working tree limpio)"


class GitDiffTool(BaseTool):
    name: str = "git_diff"
    description: str = "Muestra los cambios no commiteados. Acepta un archivo especifico (opcional)."
    args_schema: type[BaseModel] = GitDiffInput
    project_root: Path = Path(".")

    def _run(self, file_path: str = "") -> str:
        if not _git_available():
            return "Error: git no esta instalado en el sistema."
        args = ["diff"]
        if file_path:
            args.append("--")
            args.append(file_path)
        out, code = _run_git(args, self.project_root)
        if code != 0:
            return f"Error ejecutando git diff: {out}"
        if not out:
            return "(sin cambios no commiteados)"
        return out[:4000] + ("\n[... diff truncado a 4000 chars]" if len(out) > 4000 else "")


class GitLogTool(BaseTool):
    name: str = "git_log"
    description: str = "Muestra el historial de commits recientes."
    args_schema: type[BaseModel] = GitLogInput
    project_root: Path = Path(".")

    def _run(self, limit: int = 20) -> str:
        if not _git_available():
            return "Error: git no esta instalado en el sistema."
        limit = min(max(1, limit), 30)
        out, code = _run_git(
            ["log", f"--max-count={limit}", "--oneline", "--decorate", "--graph"],
            self.project_root,
        )
        if code != 0:
            return f"Error ejecutando git log: {out}"
        return out or "(sin commits aun)"


class GitBranchesTool(BaseTool):
    name: str = "git_branches"
    description: str = "Lista las ramas del repo ordenadas por fecha de ultimo commit."
    args_schema: type[BaseModel] = EmptyInput
    project_root: Path = Path(".")

    def _run(self) -> str:
        if not _git_available():
            return "Error: git no esta instalado en el sistema."
        out, code = _run_git(
            ["branch", "-a", "--sort=-committerdate", "--format=%(refname:short)  %(committerdate:relative)"],
            self.project_root,
        )
        if code != 0:
            return f"Error ejecutando git branch: {out}"
        return out or "(sin ramas)"


class GitShowFileTool(BaseTool):
    name: str = "git_show_file"
    description: str = "Muestra el contenido de un archivo en un ref git especifico (ej: HEAD, main, commit-hash)."
    args_schema: type[BaseModel] = GitShowFileInput
    project_root: Path = Path(".")

    def _run(self, ref: str, file_path: str) -> str:
        if not _git_available():
            return "Error: git no esta instalado en el sistema."
        # Sanitizar el ref: no permitir caracteres peligrosos
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-~^@{}")
        if not all(c in safe_chars for c in ref):
            return f"Error: ref invalido: {ref}"
        out, code = _run_git(["show", f"{ref}:{file_path}"], self.project_root)
        if code != 0:
            return f"Error: {out}"
        return out[:6000] + ("\n[... truncado]" if len(out) > 6000 else "")


# ─── Factory ─────────────────────────────────────────────────────────

def get_git_tools(project_root: Path) -> list[BaseTool]:
    """Retorna las tools de git configuradas para un proyecto."""
    return [
        GitStatusTool(project_root=project_root),
        GitDiffTool(project_root=project_root),
        GitLogTool(project_root=project_root),
        GitBranchesTool(project_root=project_root),
        GitShowFileTool(project_root=project_root),
    ]
