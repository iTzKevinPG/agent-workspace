"""
MCP de filesystem: leer y escribir archivos dentro del proyecto activo.
Los agentes solo pueden operar dentro de projects_path del namespace.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    path: str = Field(description="Ruta relativa al archivo dentro del proyecto activo")


class WriteFileInput(BaseModel):
    path: str = Field(description="Ruta relativa al archivo a escribir")
    content: str = Field(description="Contenido completo del archivo")


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="Ruta relativa al directorio a listar")


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "Lee el contenido de un archivo del proyecto activo."
    args_schema: type[BaseModel] = ReadFileInput
    project_root: Path = Path(".")

    def _run(self, path: str) -> str:
        target = self._safe_path(path)
        if not target:
            return f"Error: ruta fuera del proyecto permitido: {path}"
        if not target.exists():
            return f"Error: archivo no encontrado: {path}"
        return target.read_text(encoding="utf-8")

    def _safe_path(self, path: str) -> Optional[Path]:
        resolved = (self.project_root / path).resolve()
        if not str(resolved).startswith(str(self.project_root.resolve())):
            return None
        return resolved


class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = (
        "Escribe o sobreescribe un archivo en el proyecto activo. "
        "Crea los directorios intermedios si no existen."
    )
    args_schema: type[BaseModel] = WriteFileInput
    project_root: Path = Path(".")
    modified_files: list = Field(default_factory=list)

    def _run(self, path: str, content: str) -> str:
        target = self._safe_path(path)
        if not target:
            return f"Error: ruta fuera del proyecto permitido: {path}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.modified_files.append(str(Path(path)))
        return f"Archivo escrito: {path} ({len(content)} caracteres)"

    def _safe_path(self, path: str) -> Optional[Path]:
        resolved = (self.project_root / path).resolve()
        if not str(resolved).startswith(str(self.project_root.resolve())):
            return None
        return resolved


class ListDirTool(BaseTool):
    name: str = "list_dir"
    description: str = "Lista archivos y carpetas de un directorio del proyecto activo."
    args_schema: type[BaseModel] = ListDirInput
    project_root: Path = Path(".")

    def _run(self, path: str = ".") -> str:
        target = self._safe_path(path)
        if not target:
            return f"Error: ruta fuera del proyecto permitido: {path}"
        if not target.exists():
            return f"Error: directorio no encontrado: {path}"
        if not target.is_dir():
            return f"Error: no es un directorio: {path}"

        entries = []
        for entry in sorted(target.iterdir()):
            prefix = "📁 " if entry.is_dir() else "   "
            entries.append(f"{prefix}{entry.name}")

        return "\n".join(entries) if entries else "(directorio vacio)"

    def _safe_path(self, path: str) -> Optional[Path]:
        resolved = (self.project_root / path).resolve()
        if not str(resolved).startswith(str(self.project_root.resolve())):
            return None
        return resolved


def get_filesystem_tools(project_root: Path) -> tuple[list[BaseTool], "WriteFileTool"]:
    """Retorna las tools de filesystem configuradas para un proyecto."""
    write_tool = WriteFileTool(project_root=project_root)
    return [
        ReadFileTool(project_root=project_root),
        write_tool,
        ListDirTool(project_root=project_root),
    ], write_tool  # retornamos write_tool para poder leer modified_files
