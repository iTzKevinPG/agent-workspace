"""
MCP de Fetch: obtener contenido de URLs y documentación de librerías.
Usa solo urllib de stdlib — sin dependencias externas.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_USER_AGENT = "agent-workspace/1.0"
_TIMEOUT = 15

# Mapa de librerías a su URL de documentación oficial
_DOCS_MAP: dict[str, str] = {
    "nestjs":        "https://docs.nestjs.com",
    "nest":          "https://docs.nestjs.com",
    "nextjs":        "https://nextjs.org/docs",
    "next":          "https://nextjs.org/docs",
    "react":         "https://react.dev/reference/react",
    "tailwindcss":   "https://tailwindcss.com/docs",
    "tailwind":      "https://tailwindcss.com/docs",
    "prisma":        "https://www.prisma.io/docs",
    "typescript":    "https://www.typescriptlang.org/docs",
    "ts":            "https://www.typescriptlang.org/docs",
    "docker":        "https://docs.docker.com",
    "gitlab-ci":     "https://docs.gitlab.com/ee/ci",
    "gitlab":        "https://docs.gitlab.com",
    "vite":          "https://vitejs.dev/guide",
    "vitest":        "https://vitest.dev/guide",
    "playwright":    "https://playwright.dev/docs/intro",
    "fastapi":       "https://fastapi.tiangolo.com",
    "python":        "https://docs.python.org/3",
    "crewai":        "https://docs.crewai.com",
}


# ─── HTML → texto plano ───────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """Extrae texto plano de HTML, ignorando script/style/nav/header/footer."""
    _SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.texts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.texts.append(stripped)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(parser.texts)
    # Colapsar whitespace excesivo
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def _fetch_text(url: str, max_chars: int = 6000) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8", errors="replace")
            if "html" in content_type.lower():
                text = _html_to_text(raw)
            else:
                text = raw
            if len(text) > max_chars:
                return text[:max_chars] + f"\n\n[... contenido truncado a {max_chars} chars]"
            return text
    except urllib.error.HTTPError as e:
        return f"Error HTTP {e.code}: {e.reason} — {url}"
    except urllib.error.URLError as e:
        return f"Error de red: {e.reason} — {url}"
    except Exception as e:
        return f"Error inesperado al obtener {url}: {e}"


# ─── Schemas ─────────────────────────────────────────────────────────

class FetchURLInput(BaseModel):
    url: str = Field(description="URL a obtener")
    max_chars: int = Field(default=6000, description="Máximo de caracteres a retornar")

class FetchDocsInput(BaseModel):
    library: str = Field(description="Nombre de la librería (ej: nestjs, react, prisma)")


# ─── Tools ───────────────────────────────────────────────────────────

class FetchURLTool(BaseTool):
    name: str = "fetch_url"
    description: str = (
        "Obtiene el contenido de una URL y lo retorna como texto plano. "
        "Útil para leer documentación, issues, o páginas de referencia."
    )
    args_schema: type[BaseModel] = FetchURLInput

    def _run(self, url: str, max_chars: int = 6000) -> str:
        if not url.startswith(("http://", "https://")):
            return f"Error: URL debe empezar con http:// o https://. Recibido: {url}"
        return _fetch_text(url, max_chars=max_chars)


class FetchDocsTool(BaseTool):
    name: str = "fetch_docs"
    description: str = (
        "Obtiene la página principal de documentación oficial de una librería. "
        f"Librerías conocidas: {', '.join(sorted(_DOCS_MAP.keys()))}. "
        "Para otras librerías intenta docs.<library>.com."
    )
    args_schema: type[BaseModel] = FetchDocsInput

    def _run(self, library: str) -> str:
        lib = library.lower().strip()
        url = _DOCS_MAP.get(lib, f"https://docs.{lib}.com")
        result = _fetch_text(url, max_chars=6000)
        return f"[Fuente: {url}]\n\n{result}"


# ─── Factory ─────────────────────────────────────────────────────────

def get_fetch_tools() -> list[BaseTool]:
    """Retorna las tools de fetch (no requieren project_root)."""
    return [
        FetchURLTool(),
        FetchDocsTool(),
    ]
