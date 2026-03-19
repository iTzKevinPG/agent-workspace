#!/usr/bin/env python3
"""
Lanza una sola tarea sin sesión interactiva.
Útil para automatizaciones o scripts externos.

Uso:
  python run/task.py --namespace ecommerce-web --project mi-tienda \
    --task "crear endpoint GET /products con paginación"
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

from dashboard.ui import print_error, print_info
from core.orchestrator import Orchestrator
from dashboard.ui import Dashboard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", "-n", required=True)
    parser.add_argument("--project",   "-p", default=None)
    parser.add_argument("--task",      "-t", required=True, help="Descripción de la tarea")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print_error("ANTHROPIC_API_KEY no está definida en .env")
        sys.exit(1)

    try:
        orch = Orchestrator(
            namespace_name=args.namespace,
            project_name=args.project,
        )
        orch.state.current_task_description = args.task

        with Dashboard(orch.state) as dash:
            orch._run_task(args.task, dash)
            metrics = orch.logger.summary()
            orch.state.update_metrics(
                tokens=metrics["tokens_input"] + metrics["tokens_output"],
                cost=metrics["cost_usd"],
                elapsed=metrics["elapsed"],
            )
            dash.refresh()

    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print_info("Interrumpido.")
        sys.exit(0)


if __name__ == "__main__":
    main()
