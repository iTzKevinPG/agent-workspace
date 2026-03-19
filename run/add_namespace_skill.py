#!/usr/bin/env python3
"""
Agrega una namespace skill a un namespace existente.

Uso:
  # Desde template versionado en este repo:
  python run/add_namespace_skill.py --namespace ecommerce-web --skill stripe --from-template

  # Skill vacia para escribir desde cero:
  python run/add_namespace_skill.py --namespace ecommerce-web --skill mi-skill
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

ROOT = Path(__file__).parent.parent
NAMESPACES_DIR = ROOT / "namespaces"
SKILLS_TEMPLATES_DIR = ROOT / "templates" / "namespace-skills"

console = Console()


def _extract_description(setup_md: Path) -> str:
    """
    Extrae la descripcion de un setup.md: el primer parrafo bajo '## Que hace',
    o como fallback la primera linea de texto significativa del archivo.
    """
    text = setup_md.read_text(encoding="utf-8")

    # Buscar seccion "## Que hace"
    match = re.search(r"##\s+Que hace\s*\n(.+?)(?:\n#|\Z)", text, re.DOTALL)
    if match:
        paragraph = match.group(1).strip().splitlines()
        first_line = next((l.strip() for l in paragraph if l.strip()), "")
        if first_line:
            return first_line

    # Fallback: primera linea que no sea un heading
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:120]

    return ""


def _update_namespace_yaml(ns_yaml: Path, skill_name: str, description: str, skill_path_rel: str, roles: list[str]):
    """
    Agrega la entrada de la skill bajo namespace_skills en el namespace.yaml.
    Preserva el formato existente del archivo.
    """
    content = ns_yaml.read_text(encoding="utf-8")

    roles_yaml = "[" + ", ".join(roles) + "]" if roles else "[]"
    entry = (
        f"  - name: {skill_name}\n"
        f"    description: \"{description}\"\n"
        f"    path: {skill_path_rel}\n"
        f"    roles: {roles_yaml}\n"
    )

    # Si ya existe esta skill, no duplicar
    if f"name: {skill_name}" in content:
        console.print(f"  [yellow]⚠[/]  La skill '{skill_name}' ya esta en namespace.yaml — no se duplica")
        return

    # Reemplazar "namespace_skills: []" por la lista con la nueva entrada
    if "namespace_skills: []" in content:
        new_content = content.replace(
            "namespace_skills: []",
            f"namespace_skills:\n{entry}"
        )
        ns_yaml.write_text(new_content, encoding="utf-8")
        return

    # Si ya hay una lista, agregar al final de ella
    if "namespace_skills:" in content:
        # Insertar antes del primer comentario despues de namespace_skills o al final
        lines = content.splitlines(keepends=True)
        insert_idx = None
        in_section = False
        for i, line in enumerate(lines):
            if line.strip().startswith("namespace_skills:"):
                in_section = True
                continue
            if in_section:
                stripped = line.strip()
                # Seguir mientras sean elementos de la lista o lineas vacias
                if stripped.startswith("- ") or stripped.startswith("  ") or stripped == "":
                    insert_idx = i + 1
                else:
                    break

        if insert_idx is not None:
            lines.insert(insert_idx, entry)
            ns_yaml.write_text("".join(lines), encoding="utf-8")
            return

    # Fallback: agregar al final del archivo
    with open(ns_yaml, "a", encoding="utf-8") as f:
        f.write(f"\nnamespace_skills:\n{entry}")


def main():
    parser = argparse.ArgumentParser(description="Agregar una namespace skill a un namespace")
    parser.add_argument("--namespace", "-n", required=True, help="Nombre del namespace")
    parser.add_argument("--skill", "-s", required=True, help="Nombre de la skill")
    parser.add_argument(
        "--from-template",
        action="store_true",
        help="Copiar desde templates/namespace-skills/<skill>/ (debe existir en el repo)",
    )
    parser.add_argument(
        "--roles",
        default="backend,devops",
        help="Roles que pueden instalar la skill, separados por coma (default: backend,devops)",
    )
    args = parser.parse_args()

    ns_dir = NAMESPACES_DIR / args.namespace
    if not ns_dir.exists():
        console.print(f"[red]✗[/]  Namespace '{args.namespace}' no encontrado en namespaces/")
        console.print(f"   Crealo con: python run/init.py --name {args.namespace}")
        sys.exit(1)

    ns_yaml = ns_dir / "namespace.yaml"
    if not ns_yaml.exists():
        console.print(f"[red]✗[/]  {ns_yaml} no encontrado — namespace mal configurado")
        sys.exit(1)

    dest_dir = ns_dir / "skills" / args.skill

    if dest_dir.exists():
        console.print(f"[yellow]⚠[/]  La skill ya existe en {dest_dir.relative_to(ROOT)}")
        console.print("   Usa --force para sobreescribir (no implementado aun)")
        sys.exit(1)

    # ── Determinar origen ─────────────────────────────────────────────────────

    if args.from_template:
        src_dir = SKILLS_TEMPLATES_DIR / args.skill
        if not src_dir.exists():
            console.print(f"[red]✗[/]  Template '{args.skill}' no encontrado en templates/namespace-skills/")
            console.print(f"   Skills disponibles: {[d.name for d in SKILLS_TEMPLATES_DIR.iterdir() if d.is_dir() and not d.name.startswith('_')]}")
            sys.exit(1)
    else:
        src_dir = SKILLS_TEMPLATES_DIR / "_template"
        if not src_dir.exists():
            console.print("[red]✗[/]  _template no encontrado en templates/namespace-skills/")
            sys.exit(1)

    # ── Copiar archivos ───────────────────────────────────────────────────────

    shutil.copytree(src_dir, dest_dir)

    # Si se copio desde _template, renombrar setup.md.tpl → setup.md
    tpl_setup = dest_dir / "setup.md.tpl"
    if tpl_setup.exists():
        final_setup = dest_dir / "setup.md"
        tpl_content = tpl_setup.read_text(encoding="utf-8").replace("{{SKILL_NAME}}", args.skill)
        final_setup.write_text(tpl_content, encoding="utf-8")
        tpl_setup.unlink()

    # ── Extraer descripcion y actualizar namespace.yaml ───────────────────────

    setup_md = dest_dir / "setup.md"
    description = _extract_description(setup_md) if setup_md.exists() else ""

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    skill_path_rel = f"skills/{args.skill}"

    _update_namespace_yaml(ns_yaml, args.skill, description, skill_path_rel, roles)

    # ── Resumen ───────────────────────────────────────────────────────────────

    files_created = sorted(str(p.relative_to(ROOT)) for p in dest_dir.rglob("*") if p.is_file())

    console.print()
    console.print(Panel(
        Text.assemble(
            (f"✓ Skill '{args.skill}' agregada al namespace '{args.namespace}'\n\n", "bold green"),
            *[(f"  {f}\n", "dim") for f in files_created],
            ("\nProximos pasos:\n", "bold white"),
            (f"  1. Edita namespaces/{args.namespace}/skills/{args.skill}/setup.md\n", "dim"),
            (f"     para personalizar la instruccion al stack de tu proyecto\n", "dim"),
            (f"  2. Agrega templates en skills/{args.skill}/templates/ si aplica\n", "dim"),
            (f"  3. Arranca el orquestador y dile al agente:\n", "dim"),
            (f'     "instala la skill {args.skill} en este proyecto"\n', "green"),
        ),
        border_style="green",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
