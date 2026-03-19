"""
MCP de razonamiento estructurado.
No llama a ninguna API externa — estructura el problema en un formato
que ayuda al agente a pensar con mayor claridad y sistematicidad.
"""
from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ─── Schema ──────────────────────────────────────────────────────────

class ThinkInput(BaseModel):
    problem: str = Field(description="El problema o decision a analizar")
    context: str = Field(default="", description="Contexto adicional relevante (opcional)")
    constraints: str = Field(default="", description="Restricciones o requisitos no negociables (opcional)")


# ─── Tool ────────────────────────────────────────────────────────────

class ThinkStepByStepTool(BaseTool):
    name: str = "think_step_by_step"
    description: str = (
        "Estructura un problema complejo en pasos de razonamiento sistematico. "
        "Util antes de tomar decisiones de arquitectura, diseno, o cuando la tarea tiene multiples enfoques posibles. "
        "Retorna un analisis estructurado con supuestos, opciones, riesgos y recomendacion."
    )
    args_schema: type[BaseModel] = ThinkInput

    def _run(self, problem: str, context: str = "", constraints: str = "") -> str:
        sections = []

        sections.append("# Analisis estructurado\n")

        sections.append(f"## Problema\n{problem}\n")

        if context:
            sections.append(f"## Contexto\n{context}\n")

        if constraints:
            sections.append(f"## Restricciones (no negociables)\n{constraints}\n")

        sections.append(
            "## Pasos de analisis\n"
            "Responde cada punto antes de llegar a la recomendacion:\n\n"
            "1. **¿Que se pide exactamente?**  \n"
            "   Describe el objetivo en una frase sin ambiguedades.\n\n"
            "2. **¿Que informacion falta o es incierta?**  \n"
            "   Lista lo que no sabes y el impacto de cada incognita.\n\n"
            "3. **¿Cuales son las opciones principales?**  \n"
            "   Al menos 2 enfoques distintos. Para cada uno: pros, contras, esfuerzo estimado.\n\n"
            "4. **¿Que riesgos o efectos secundarios hay?**  \n"
            "   Consecuencias no obvias de cada opcion.\n\n"
            "5. **¿Cuales son los criterios de decision?**  \n"
            "   ¿Que importa mas: velocidad, mantenibilidad, costo, compatibilidad?\n\n"
            "6. **¿Hay precedentes en el codebase?**  \n"
            "   Usa read_file y list_dir para verificar patrones existentes antes de proponer uno nuevo.\n"
        )

        sections.append(
            "## Recomendacion\n"
            "Despues de completar el analisis anterior, escribe:\n"
            "- La opcion elegida y por que\n"
            "- Los pasos concretos de implementacion\n"
            "- Senales de alerta que indicarian que hay que replantear\n"
        )

        return "\n".join(sections)


# ─── Factory ─────────────────────────────────────────────────────────

def get_sequential_thinking_tools() -> list[BaseTool]:
    """Retorna las tools de razonamiento estructurado."""
    return [
        ThinkStepByStepTool(),
    ]
