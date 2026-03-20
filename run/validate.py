#!/usr/bin/env python3
"""
Valida que el entorno este correctamente configurado antes de arrancar.
Corre automaticamente desde setup.sh.

Uso manual:
  python run/validate.py
  python run/validate.py --namespace ecommerce-web
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

OK  = "[green]✓[/]"
ERR = "[red]✗[/]"
WRN = "[yellow]⚠[/]"


def check(label: str, ok: bool, detail: str = "", warn: bool = False) -> bool:
    icon = OK if ok else (WRN if warn else ERR)
    console.print(f"  {icon}  {label}", end="")
    if detail:
        console.print(f"  [dim]{detail}[/]", end="")
    console.print()
    return ok


def validate_env() -> bool:
    console.print("\n[bold]Variables de entorno[/]")
    ok = True

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    ok &= check("ANTHROPIC_API_KEY", bool(api_key and not api_key.endswith("xxx")),
                "(vacia o con valor de ejemplo)" if not api_key else "")

    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    check("ANTHROPIC_MODEL", True, model)

    cost_alert = os.getenv("COST_ALERT_USD", "2.00")
    check("COST_ALERT_USD", True, f"${cost_alert}")

    return ok


def validate_deps() -> bool:
    console.print("\n[bold]Dependencias Python[/]")
    ok = True
    deps = ["crewai", "anthropic", "dotenv", "yaml", "rich", "questionary"]
    for dep in deps:
        try:
            import importlib
            importlib.import_module(dep.replace("-", "_"))
            check(dep, True)
        except ImportError:
            check(dep, False, "ejecuta: pip install -e .")
            ok = False
    return ok


def validate_namespace(name: str) -> bool:
    console.print(f"\n[bold]Namespace: {name}[/]")
    ok = True
    ns_dir = ROOT / "namespaces" / name

    ok &= check("Directorio existe", ns_dir.exists(),
                f"Crea con: python run/init.py --name {name}")

    if ns_dir.exists():
        ok &= check("namespace.yaml", (ns_dir / "namespace.yaml").exists())
        check("standards.md", (ns_dir / "standards.md").exists(), warn=True)
        check("rules.md", (ns_dir / "rules.md").exists(), warn=True)

        projects_dir = ns_dir / "projects"
        check("projects/", projects_dir.exists(),
              "crea symlinks a tus repos aqui" if not projects_dir.exists() else "")

        if projects_dir.exists():
            projects = list(projects_dir.iterdir())
            check(
                "Proyectos en projects/",
                len(projects) > 0,
                f"{len(projects)} encontrados" if projects else "agrega symlinks con ln -s",
                warn=(len(projects) == 0),
            )

        # Validar projects_path del namespace y MCPs activos
        try:
            import yaml as _yaml
            data = _yaml.safe_load((ns_dir / "namespace.yaml").read_text(encoding="utf-8"))
            pp = Path(data.get("projects_path", ""))
            check("projects_path existe en disco", pp.exists(),
                  str(pp) if not pp.exists() else "")

            # Validar MCPs activos
            active_mcps = data.get("mcps", [])
            if "git" in active_mcps:
                import shutil
                git_ok = shutil.which("git") is not None
                check("git instalado (MCP git activo)", git_ok,
                      "instala git: https://git-scm.com/downloads" if not git_ok else "")

            # Validar namespace skills
            skills_cfg = data.get("namespace_skills") or []
            if skills_cfg:
                console.print(f"\n  [bold]Namespace skills ({len(skills_cfg)})[/]")
                t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", pad_edge=False)
                t.add_column("SKILL", width=16)
                t.add_column("CARPETA", width=6)
                t.add_column("SETUP.MD", width=9)
                t.add_column("TEMPLATES/", width=11)
                t.add_column("RUTA")
                for skill_cfg in skills_cfg:
                    skill_name = skill_cfg.get("name", "?") if isinstance(skill_cfg, dict) else str(skill_cfg)
                    skill_rel  = skill_cfg.get("path", f"skills/{skill_name}") if isinstance(skill_cfg, dict) else f"skills/{skill_name}"
                    skill_path = ns_dir / skill_rel
                    dir_ok      = skill_path.exists()
                    setup_ok    = (skill_path / "setup.md").exists() if dir_ok else False
                    has_tpl     = (skill_path / "templates").is_dir() if dir_ok else False
                    t.add_row(
                        skill_name,
                        f"[green]{OK}[/]" if dir_ok else f"[red]{ERR}[/]",
                        f"[green]{OK}[/]" if setup_ok else f"[red]{ERR}[/]",
                        f"[green]{OK}[/]" if has_tpl else f"[yellow]{WRN}[/]",
                        str(skill_path.relative_to(ROOT)) if dir_ok else str(skill_rel),
                    )
                console.print(t)
        except Exception:
            pass

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", "-n", help="Namespace a validar")
    args = parser.parse_args()

    console.print("\n[bold green]agent-workspace — validacion de entorno[/]")

    env_ok = validate_env()
    deps_ok = validate_deps()

    ns_ok = True
    namespace = args.namespace or os.getenv("ACTIVE_NAMESPACE")
    if namespace:
        ns_ok = validate_namespace(namespace)

    console.print()
    if env_ok and deps_ok and ns_ok:
        console.print("[bold green]✓ Todo listo para arrancar.[/]\n")
        sys.exit(0)
    else:
        console.print("[bold red]✗ Hay errores que corregir antes de arrancar.[/]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
