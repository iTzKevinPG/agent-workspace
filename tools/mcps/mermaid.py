"""
MCP de Mermaid: generación y guardado de diagramas.
Genera código Mermaid a partir de descripciones en lenguaje natural
y puede guardarlos en archivos .md dentro del proyecto.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_SUPPORTED_TYPES = ["flowchart", "sequenceDiagram", "classDiagram", "erDiagram", "gitGraph", "architecture"]

_TEMPLATES: dict[str, str] = {
    "flowchart": """\
flowchart TD
    A[Inicio] --> B{{¿Condición?}}
    B -- Sí --> C[Proceso A]
    B -- No --> D[Proceso B]
    C --> E[Fin]
    D --> E
""",
    "sequenceDiagram": """\
sequenceDiagram
    participant Cliente
    participant API
    participant DB
    Cliente->>API: POST /endpoint
    API->>DB: query()
    DB-->>API: resultado
    API-->>Cliente: 200 OK
""",
    "classDiagram": """\
classDiagram
    class Entidad {
        +String id
        +String nombre
        +metodo() String
    }
    class Servicio {
        -Repository repo
        +crear(dto) Entidad
        +buscar(id) Entidad
    }
    Servicio --> Entidad : gestiona
""",
    "erDiagram": """\
erDiagram
    USUARIO {
        string id PK
        string email
        string nombre
        datetime createdAt
    }
    ORDEN {
        string id PK
        string usuarioId FK
        float total
        string estado
    }
    USUARIO ||--o{ ORDEN : "realiza"
""",
    "gitGraph": """\
gitGraph
    commit id: "init"
    branch develop
    checkout develop
    commit id: "feat: base"
    branch feature/nueva-feature
    checkout feature/nueva-feature
    commit id: "feat: implementar"
    checkout develop
    merge feature/nueva-feature
    checkout main
    merge develop tag: "v1.0.0"
""",
    "architecture": """\
flowchart TB
    subgraph Frontend
        UI[Next.js App]
    end
    subgraph Backend
        API[NestJS API]
        Worker[Queue Worker]
    end
    subgraph Datos
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end
    UI --> API
    API --> DB
    API --> Cache
    Worker --> DB
""",
}


# ─── Schemas ─────────────────────────────────────────────────────────

class GenerateDiagramInput(BaseModel):
    diagram_type: str = Field(
        description=f"Tipo de diagrama: {', '.join(_SUPPORTED_TYPES)}"
    )
    description: str = Field(
        description="Descripción en lenguaje natural de lo que debe representar el diagrama"
    )

class SaveDiagramInput(BaseModel):
    diagram_code: str = Field(description="Código Mermaid a guardar")
    file_path: str = Field(description="Ruta relativa del archivo .md donde guardar el diagrama")
    title: str = Field(default="", description="Título opcional del diagrama")


# ─── Tools ───────────────────────────────────────────────────────────

class GenerateDiagramTool(BaseTool):
    name: str = "generate_diagram"
    description: str = (
        "Genera código Mermaid para un diagrama dado un tipo y descripción. "
        f"Tipos soportados: {', '.join(_SUPPORTED_TYPES)}. "
        "Retorna el bloque Mermaid listo para usar o guardar."
    )
    args_schema: type[BaseModel] = GenerateDiagramInput

    def _run(self, diagram_type: str, description: str) -> str:
        dtype = diagram_type.lower().strip()
        # Normalizar alias
        if dtype in ("flow", "flowchart"):
            dtype = "flowchart"
        elif dtype in ("sequence", "sequencediagram"):
            dtype = "sequenceDiagram"
        elif dtype in ("class", "classdiagram"):
            dtype = "classDiagram"
        elif dtype in ("er", "erdiagram"):
            dtype = "erDiagram"
        elif dtype in ("git", "gitgraph"):
            dtype = "gitGraph"
        elif dtype in ("arch", "architecture"):
            dtype = "architecture"

        if dtype not in _TEMPLATES:
            return (
                f"Error: tipo de diagrama '{diagram_type}' no soportado.\n"
                f"Tipos disponibles: {', '.join(_SUPPORTED_TYPES)}"
            )

        template = _TEMPLATES[dtype]

        return (
            f"## Instrucciones para el diagrama\n\n"
            f"**Descripción solicitada:** {description}\n\n"
            f"**Tipo:** `{dtype}`\n\n"
            f"Usa la siguiente plantilla como base y adáptala a la descripción. "
            f"Después usa `save_diagram` para guardar el resultado.\n\n"
            f"**Plantilla base:**\n"
            f"```mermaid\n{template}```\n\n"
            f"Adapta los nodos, relaciones y etiquetas según: {description}"
        )


class SaveDiagramTool(BaseTool):
    name: str = "save_diagram"
    description: str = (
        "Guarda un diagrama Mermaid en un archivo .md dentro del proyecto activo, "
        "correctamente formateado con bloque ```mermaid```."
    )
    args_schema: type[BaseModel] = SaveDiagramInput
    project_root: Path = Path(".")

    def _run(self, diagram_code: str, file_path: str, title: str = "") -> str:
        target = self._safe_path(file_path)
        if not target:
            return f"Error: ruta fuera del proyecto permitido: {file_path}"

        # Asegurar extensión .md
        if not file_path.endswith(".md"):
            file_path = file_path + ".md"
            target = self._safe_path(file_path)
            if not target:
                return f"Error: ruta fuera del proyecto permitido: {file_path}"

        # Limpiar el código (remover bloques mermaid si ya los tiene)
        code = diagram_code.strip()
        if code.startswith("```mermaid"):
            code = code[len("```mermaid"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        heading = f"# {title}\n\n" if title else ""
        content = f"{heading}```mermaid\n{code}\n```\n"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Diagrama guardado en: {file_path}"

    def _safe_path(self, path: str) -> Optional[Path]:
        resolved = (self.project_root / path).resolve()
        if not str(resolved).startswith(str(self.project_root.resolve())):
            return None
        return resolved


# ─── Factory ─────────────────────────────────────────────────────────

def get_mermaid_tools(project_root: Path) -> list[BaseTool]:
    """Retorna las tools de Mermaid configuradas para un proyecto."""
    return [
        GenerateDiagramTool(),
        SaveDiagramTool(project_root=project_root),
    ]
