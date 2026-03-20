#!/usr/bin/env python3
"""
Punto de entrada principal.
Arranca el orquestador y mantiene la sesion interactiva activa.

Uso:
  python run/start.py --namespace ecommerce-web
  python run/start.py --namespace ecommerce-web --project mi-tienda
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Forzar UTF-8 en stdout/stderr para evitar errores de encoding en Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from dashboard.ui import print_error, print_info
from core.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Arranca el orquestador de agentes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python run/start.py --namespace ecommerce-web
  python run/start.py --namespace ecommerce-web --project mi-tienda

Comandos disponibles en sesion interactiva:
  <cualquier texto>       → ejecutar tarea
  proyecto <nombre>       → cambiar proyecto activo
  estado                  → refrescar dashboard
  salir / q               → terminar sesion
""",
    )
    parser.add_argument("--namespace", "-n", help="Nombre del namespace a usar")
    parser.add_argument("--project",   "-p", help="Proyecto activo (opcional)")
    args = parser.parse_args()

    # Validar API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print_error("ANTHROPIC_API_KEY no esta definida en .env")
        print_info("Edita el archivo .env y agrega tu API key de Anthropic")
        sys.exit(1)

    # Resolver namespace
    namespace = args.namespace or os.getenv("ACTIVE_NAMESPACE")
    if not namespace:
        print_error("Debes especificar un namespace: --namespace <nombre>")
        print_info("O define ACTIVE_NAMESPACE en tu .env")
        print_info("Para crear uno nuevo: python run/init.py")
        sys.exit(1)

    try:
        orchestrator = Orchestrator(
            namespace_name=namespace,
            project_name=args.project,
        )
        orchestrator.interactive_session()

    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print_info("\nSesion interrumpida.")
        sys.exit(0)


if __name__ == "__main__":
    main()
