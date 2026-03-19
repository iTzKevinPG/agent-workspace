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
    problem: str = Field(description="El problema o decisión a analizar")
    context: str = Field(default="", description="Contexto adicional relevante (opcional)")
    constraints: str = Field(default="", description="Restricciones o requisitos no negociables (opcional)")


# ─── Tool ────────────────────────────────────────────────────────────

class ThinkStepByStepTool(BaseTool):
    name: str = "think_step_by_step"
    description: str = (
        "Estructura un problema complejo en pasos de razonamiento sistemático. "
        "Útil antes de tomar decisiones de arquitectura, diseño, o cuando la tarea tiene múltiples enfoques posibles. "
        "Retorna un análisis estructurado con supuestos, opciones, riesgos y recomendación."
    )
    args_schema: type[BaseModel] = ThinkInput

    def _run(self, problem: str, context: str = "", constraints: str = "") -> str:
        sections = []

        sections.append("# Análisis estructurado\n")

        sections.append(f"## Problema\n{problem}\n")

        if context:
            sections.append(f"## Contexto\n{context}\n")

        if constraints:
            sections.append(f"## Restricciones (no negociables)\n{constraints}\n")

        sections.append(
            "## Pasos de análisis\n"
            "Responde cada punto antes de llegar a la recomendación:\n\n"
            "1. **¿Qué se pide exactamente?**  \n"
            "   Describe el objetivo en una frase sin ambigüedades.\n\n"
            "2. **¿Qué información falta o es incierta?**  \n"
            "   Lista lo que no sabes y el impacto de cada incógnita.\n\n"
            "3. **¿Cuáles son las opciones principales?**  \n"
            "   Al menos 2 enfoques distintos. Para cada uno: pros, contras, esfuerzo estimado.\n\n"
            "4. **¿Qué riesgos o efectos secundarios hay?**  \n"
            "   Consecuencias no obvias de cada opción.\n\n"
            "5. **¿Cuáles son los criterios de decisión?**  \n"
            "   ¿Qué importa más: velocidad, mantenibilidad, costo, compatibilidad?\n\n"
            "6. **¿Hay precedentes en el codebase?**  \n"
            "   Usa read_file y list_dir para verificar patrones existentes antes de proponer uno nuevo.\n"
        )

        sections.append(
            "## Recomendación\n"
            "Después de completar el análisis anterior, escribe:\n"
            "- La opción elegida y por qué\n"
            "- Los pasos concretos de implementación\n"
            "- Señales de alerta que indicarían que hay que replantear\n"
        )

        return "\n".join(sections)


# ─── Factory ─────────────────────────────────────────────────────────

def get_sequential_thinking_tools() -> list[BaseTool]:
    """Retorna las tools de razonamiento estructurado."""
    return [
        ThinkStepByStepTool(),
    ]
