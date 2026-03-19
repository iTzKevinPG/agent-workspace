"""
Skill de documentación.
Genera secciones de README, extrae endpoints y genera JSDoc/docstrings.
Sin dependencias externas — solo stdlib.
"""
from __future__ import annotations

import re
from typing import Any


class DocsSkill:
    """Utilidades de documentación para usar desde el orquestador o los agentes."""

    def generate_readme_section(self, title: str, content_description: str) -> str:
        """
        Genera una sección de README en Markdown dado un título y descripción
        de qué debe contener. Retorna el bloque listo para editar.
        """
        slug = title.lower().replace(" ", "-").replace("/", "-")
        return (
            f"## {title}\n\n"
            f"<!-- TODO: {content_description} -->\n\n"
            f"_(Sección pendiente de completar)_\n"
        )

    def extract_endpoints(
        self, file_content: str, framework: str
    ) -> list[dict[str, str]]:
        """
        Extrae endpoints de un archivo de código.
        Soporta: nestjs, fastapi, express.
        Retorna lista de {"method", "path", "description"}.
        """
        fw = framework.lower().strip()
        endpoints: list[dict[str, str]] = []

        if fw in ("nestjs", "nest"):
            # NestJS: @Get('/ruta'), @Post('/ruta'), etc.
            pattern = re.compile(
                r"@(Get|Post|Put|Patch|Delete|Head|Options)\s*\(\s*['\"]([^'\"]*)['\"]",
                re.IGNORECASE,
            )
            lines = file_content.splitlines()
            for i, line in enumerate(lines):
                for m in pattern.finditer(line):
                    method = m.group(1).upper()
                    path = m.group(2) or "/"
                    # Buscar descripción en la línea siguiente (decorador ApiOperation si existe)
                    desc = ""
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        op_match = re.search(r"ApiOperation\s*\(\s*\{[^}]*summary:\s*['\"]([^'\"]+)['\"]", next_line)
                        if op_match:
                            desc = op_match.group(1)
                    endpoints.append({"method": method, "path": path, "description": desc})

        elif fw == "fastapi":
            # FastAPI: @app.get('/ruta'), @router.post('/ruta'), etc.
            pattern = re.compile(
                r"@\w+\.(get|post|put|patch|delete|head|options)\s*\(\s*['\"]([^'\"]*)['\"]",
                re.IGNORECASE,
            )
            lines = file_content.splitlines()
            for i, line in enumerate(lines):
                for m in pattern.finditer(line):
                    method = m.group(1).upper()
                    path = m.group(2) or "/"
                    # Buscar docstring en la función siguiente
                    desc = ""
                    for j in range(i + 1, min(i + 5, len(lines))):
                        doc_match = re.search(r'"""([^"]+)"""', lines[j])
                        if doc_match:
                            desc = doc_match.group(1).strip()
                            break
                    endpoints.append({"method": method, "path": path, "description": desc})

        elif fw == "express":
            # Express: router.get('/ruta', ...), app.post('/ruta', ...)
            pattern = re.compile(
                r"\w+\.(get|post|put|patch|delete|head|options)\s*\(\s*['\"]([^'\"]*)['\"]",
                re.IGNORECASE,
            )
            for m in pattern.finditer(file_content):
                method = m.group(1).upper()
                path = m.group(2) or "/"
                endpoints.append({"method": method, "path": path, "description": ""})

        return endpoints

    def generate_jsdoc(self, function_signature: str, description: str) -> str:
        """
        Genera el bloque JSDoc o docstring Python para una función.
        Detecta automáticamente el lenguaje por la sintaxis de la firma.
        """
        # Detectar si es Python (def ...) o JS/TS
        is_python = function_signature.strip().startswith("def ") or "->" in function_signature

        # Extraer parámetros
        params = self._extract_params(function_signature)

        if is_python:
            lines = [f'"""', description]
            if params:
                lines.append("")
                lines.append("Args:")
                for p, ptype in params:
                    type_hint = f" ({ptype})" if ptype else ""
                    lines.append(f"    {p}{type_hint}: TODO — describir parámetro")
                lines.append("")
                lines.append("Returns:")
                lines.append("    TODO — describir retorno")
            lines.append('"""')
            return "\n".join(lines)
        else:
            lines = ["/**", f" * {description}"]
            if params:
                lines.append(" *")
                for p, ptype in params:
                    type_hint = f" {{{ptype}}}" if ptype else ""
                    lines.append(f" * @param{type_hint} {p} TODO — describir parámetro")
                lines.append(" * @returns TODO — describir retorno")
            lines.append(" */")
            return "\n".join(lines)

    def _extract_params(self, signature: str) -> list[tuple[str, str]]:
        """Extrae (nombre, tipo) de los parámetros de una firma de función."""
        # Extraer lo que hay entre paréntesis
        match = re.search(r"\(([^)]*)\)", signature)
        if not match:
            return []

        raw = match.group(1)
        params: list[tuple[str, str]] = []
        for part in raw.split(","):
            part = part.strip()
            if not part or part in ("self", "cls", "*args", "**kwargs"):
                continue
            # Python: "nombre: Tipo = default"
            py_match = re.match(r"(\w+)\s*:\s*([\w\[\], |]+?)(?:\s*=.*)?$", part)
            if py_match:
                params.append((py_match.group(1), py_match.group(2).strip()))
                continue
            # TS: "nombre: Tipo" o "nombre?: Tipo"
            ts_match = re.match(r"(\w+)\??\s*:\s*([\w<>\[\], |]+)", part)
            if ts_match:
                params.append((ts_match.group(1), ts_match.group(2).strip()))
                continue
            # Solo nombre
            name_match = re.match(r"(\w+)", part)
            if name_match:
                params.append((name_match.group(1), ""))

        return params


# Instancia por defecto
docs = DocsSkill()
