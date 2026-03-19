"""
MCP de Shell: ejecucion de comandos sandboxed dentro del proyecto activo.
Whitelist configurable via env SHELL_ALLOWED_COMMANDS.
Timeout configurable via env SHELL_TIMEOUT.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_DEFAULT_ALLOWED = (
    "npm,npx,yarn,pnpm,python,pytest,pip,node,tsc,eslint,prettier,"
    "docker,docker-compose,make,cat,ls,find,grep"
)
_DEFAULT_TIMEOUT = 30
_MAX_OUTPUT = 5000

# Patrones nunca permitidos independientemente de la whitelist
_NEVER_ALLOW = ["rm -rf", "sudo", "curl | sh", "wget | sh", "bash -c", "sh -c", "| bash", "| sh"]


def _get_whitelist() -> set[str]:
    raw = os.getenv("SHELL_ALLOWED_COMMANDS", _DEFAULT_ALLOWED)
    return {cmd.strip() for cmd in raw.split(",") if cmd.strip()}


def _get_timeout() -> int:
    try:
        return int(os.getenv("SHELL_TIMEOUT", str(_DEFAULT_TIMEOUT)))
    except ValueError:
        return _DEFAULT_TIMEOUT


# ─── Schema ──────────────────────────────────────────────────────────

class RunCommandInput(BaseModel):
    command: str = Field(description="Comando a ejecutar dentro del proyecto activo")


# ─── Tool ────────────────────────────────────────────────────────────

class RunCommandTool(BaseTool):
    name: str = "run_command"
    description: str = (
        "Ejecuta un comando del proyecto (build, tests, linting) dentro del directorio activo. "
        f"Comandos permitidos por defecto: {_DEFAULT_ALLOWED}. "
        "Retorna stdout, stderr y codigo de salida."
    )
    args_schema: type[BaseModel] = RunCommandInput
    project_root: Path = Path(".")

    def _run(self, command: str) -> str:
        # Validar contra patrones nunca permitidos
        cmd_lower = command.lower()
        for forbidden in _NEVER_ALLOW:
            if forbidden in cmd_lower:
                return f"Error: comando no permitido (contiene '{forbidden}'): {command}"

        # Obtener el primer token del comando
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            return f"Error parseando el comando: {e}"

        if not tokens:
            return "Error: comando vacio."

        first_token = Path(tokens[0]).name  # solo el nombre base, no la ruta
        whitelist = _get_whitelist()
        if first_token not in whitelist:
            return (
                f"Error: '{first_token}' no esta en la whitelist de comandos permitidos.\n"
                f"Whitelist actual: {', '.join(sorted(whitelist))}\n"
                f"Para agregar comandos, edita SHELL_ALLOWED_COMMANDS en .env"
            )

        timeout = _get_timeout()
        try:
            result = subprocess.run(
                tokens,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: comando expiro despues de {timeout}s: {command}"
        except FileNotFoundError:
            return f"Error: comando no encontrado en el sistema: {tokens[0]}"
        except Exception as e:
            return f"Error ejecutando '{command}': {e}"

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        combined = ""
        if stdout:
            combined += f"STDOUT:\n{stdout}\n"
        if stderr:
            combined += f"STDERR:\n{stderr}\n"
        combined += f"EXIT CODE: {result.returncode}"

        if len(combined) > _MAX_OUTPUT:
            combined = combined[:_MAX_OUTPUT] + f"\n[... salida truncada a {_MAX_OUTPUT} chars]"

        return combined


# ─── Factory ─────────────────────────────────────────────────────────

def get_shell_tools(project_root: Path) -> list[BaseTool]:
    """Retorna las tools de shell configuradas para un proyecto."""
    return [
        RunCommandTool(project_root=project_root),
    ]
