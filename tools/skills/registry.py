"""
Registry central de Skills.
Permite al orquestador y otros módulos descubrir y cargar skills por nombre.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SkillDefinition:
    name: str
    description: str
    roles: list[str]   # qué roles se benefician de esta skill
    cls: type          # la clase a instanciar


SKILL_REGISTRY: dict[str, SkillDefinition] = {
    "codegen": SkillDefinition(
        name="codegen",
        description="Aplicar estándares de código, generar headers, detectar stack",
        roles=["architect", "backend", "frontend", "devops"],
        cls=None,  # se asigna lazy para evitar import circular
    ),
    "testing": SkillDefinition(
        name="testing",
        description="Detectar y ejecutar tests, obtener reportes de cobertura",
        roles=["backend", "frontend", "qa"],
        cls=None,
    ),
    "docs": SkillDefinition(
        name="docs",
        description="Generar secciones de README, extraer endpoints, generar JSDoc/docstrings",
        roles=["architect", "backend", "frontend", "devops"],
        cls=None,
    ),
}


def _init_registry():
    """Carga las clases lazy para evitar imports en el arranque del módulo."""
    from tools.skills.codegen import CodegenSkill
    from tools.skills.testing import TestingSkill
    from tools.skills.docs import DocsSkill
    SKILL_REGISTRY["codegen"].cls = CodegenSkill
    SKILL_REGISTRY["testing"].cls = TestingSkill
    SKILL_REGISTRY["docs"].cls = DocsSkill


def get_skill(name: str):
    """Retorna una instancia de la skill por nombre, o None si no existe."""
    _init_registry()
    definition = SKILL_REGISTRY.get(name)
    if not definition or not definition.cls:
        return None
    return definition.cls()


def list_available() -> list[str]:
    """Retorna los nombres de todas las skills disponibles."""
    return list(SKILL_REGISTRY.keys())
