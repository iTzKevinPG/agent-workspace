#!/usr/bin/env python3
"""
Wizard interactivo para crear un namespace nuevo.
Lee las preguntas de templates/namespace/init_questions.yaml
y genera los archivos en namespaces/<name>/.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import questionary
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates" / "namespace"
NAMESPACES_DIR = ROOT / "namespaces"

console = Console()


def load_questions() -> list[dict]:
    path = TEMPLATES_DIR / "init_questions.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("questions", [])


def ask_questions(questions: list[dict]) -> dict[str, str]:
    answers = {}

    for q in questions:
        key = q["key"]
        prompt = q["prompt"]
        qtype = q.get("type", "text")
        required = q.get("required", False)
        hint = q.get("hint", "")
        default = q.get("default", None)

        if hint:
            console.print(f"  [dim]{hint}[/]")

        if qtype == "text":
            val = questionary.text(
                prompt,
                default=default or "",
            ).ask()
            if val is None:
                sys.exit(0)
            if required and not val.strip():
                console.print("[red]Este campo es obligatorio.[/]")
                val = questionary.text(prompt).ask() or ""
            answers[key] = val.strip()

        elif qtype == "path":
            while True:
                val = questionary.path(prompt, default=default or "").ask()
                if val is None:
                    sys.exit(0)
                val = val.strip()
                validate = q.get("validate")
                if validate == "exists" and not Path(val).exists():
                    console.print(f"[red]La ruta no existe: {val}[/]")
                    continue
                answers[key] = val
                break

        elif qtype == "list":
            val = questionary.text(
                prompt,
                default=default or "",
            ).ask()
            if val is None:
                sys.exit(0)
            items = [x.strip() for x in val.split(",") if x.strip()]
            answers[key] = items

        elif qtype == "choice":
            options = q.get("options", [])
            choices = []
            values = {}
            for opt in options:
                if isinstance(opt, dict):
                    label = opt["label"]
                    value = opt["value"]
                else:
                    label = value = opt
                choices.append(label)
                values[label] = value

            chosen = questionary.select(prompt, choices=choices).ask()
            if chosen is None:
                sys.exit(0)
            answers[key] = values[chosen]

        elif qtype == "multiselect":
            opts = q.get("options", [])
            defaults = q.get("default", [])
            chosen = questionary.checkbox(
                prompt,
                choices=[
                    questionary.Choice(o, checked=(o in defaults))
                    for o in opts
                ],
            ).ask()
            if chosen is None:
                sys.exit(0)
            answers[key] = chosen

    return answers


def render_template(template_path: Path, answers: dict) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key, value in answers.items():
        placeholder = f"{{{{{key}}}}}"
        if isinstance(value, list):
            rendered = yaml_list(value)
        else:
            rendered = str(value) if value else ""
        content = content.replace(placeholder, rendered)
    return content


def yaml_list(items: list) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def create_namespace(answers: dict):
    name = answers["name"]
    ns_dir = NAMESPACES_DIR / name

    if ns_dir.exists():
        overwrite = questionary.confirm(
            f"El namespace '{name}' ya existe. ¿Sobreescribir?",
            default=False,
        ).ask()
        if not overwrite:
            console.print("[yellow]Cancelado.[/]")
            return

    ns_dir.mkdir(parents=True, exist_ok=True)
    (ns_dir / "projects").mkdir(exist_ok=True)

    # Renderizar y guardar cada template
    files_created = []
    for tpl_file in TEMPLATES_DIR.glob("*.tpl"):
        output_name = tpl_file.stem  # quita .tpl
        output_path = ns_dir / output_name
        content = render_template(tpl_file, answers)
        output_path.write_text(content, encoding="utf-8")
        files_created.append(str(output_path.relative_to(ROOT)))

    # Mostrar resumen
    console.print()
    console.print(Panel(
        Text.assemble(
            (f"✓ Namespace '{name}' creado\n\n", "bold green"),
            *[(f"  {f}\n", "dim") for f in files_created],
            ("\nPróximos pasos:\n", "bold white"),
            (f"  1. Edita namespaces/{name}/standards.md con tus convenciones\n", "dim"),
            (f"  2. Edita namespaces/{name}/rules.md con tus restricciones\n", "dim"),
            (f"  3. Agrega symlinks en namespaces/{name}/projects/\n", "dim"),
            (f"     ln -s /ruta/a/tu/repo namespaces/{name}/projects/mi-repo\n", "dim"),
            (f"  4. Arranca el orquestador:\n", "dim"),
            (f"     python run/start.py --namespace {name}\n", "green"),
        ),
        border_style="green",
        padding=(1, 2),
    ))


def main():
    parser = argparse.ArgumentParser(description="Crear un namespace nuevo")
    parser.add_argument("--name", help="Nombre del namespace (omitir para modo wizard)")
    args = parser.parse_args()

    console.print(Panel(
        Text.assemble(
            ("agent-workspace\n", "bold green"),
            ("Configuración de namespace nuevo\n\n", "white"),
            ("Responde las preguntas para personalizar tu entorno.\n", "dim"),
            ("Podrás editar los archivos generados después.", "dim"),
        ),
        border_style="green",
        padding=(1, 2),
    ))

    questions = load_questions()

    # Pre-rellenar nombre si se pasó como argumento
    if args.name:
        questions = [q for q in questions if q["key"] != "name"]
        answers = ask_questions(questions)
        answers["name"] = args.name
    else:
        answers = ask_questions(questions)

    create_namespace(answers)


if __name__ == "__main__":
    main()
