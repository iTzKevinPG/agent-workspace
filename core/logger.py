"""
Logger de sesión: tokens consumidos, costos, tiempos y errores.
Alimenta el dashboard con métricas en tiempo real.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOGS_DIR = ROOT / "logs"

# Precios Anthropic por modelo (por millón de tokens)
MODEL_PRICES = {
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":           {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":             {"input": 15.00, "output": 75.00},
}


class SessionLogger:
    def __init__(self, namespace: str, project: str):
        LOGS_DIR.mkdir(exist_ok=True)
        self.namespace = namespace
        self.project = project
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.start_time = datetime.now()

        # Archivo de log de sesión
        log_path = LOGS_DIR / f"{namespace}_{project}_{self.session_id}.jsonl"
        self._log_path = log_path

        # Logger estándar Python
        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self._log = logging.getLogger("agent-workspace")

    def log_llm_call(self, model: str, input_tokens: int, output_tokens: int, agent: str, task: str):
        prices = MODEL_PRICES.get(model, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost

        entry = {
            "ts": datetime.now().isoformat(),
            "agent": agent,
            "task": task[:80],
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Alerta de costo
        alert = float(os.getenv("COST_ALERT_USD", "2.00"))
        if self.total_cost_usd >= alert:
            self._log.warning(
                f"Alerta de costo: ${self.total_cost_usd:.2f} USD acumulados "
                f"(límite: ${alert})"
            )

    def elapsed(self) -> str:
        delta = datetime.now() - self.start_time
        m, s = divmod(int(delta.total_seconds()), 60)
        return f"{m}m {s:02d}s"

    def summary(self) -> dict:
        return {
            "tokens_input": self.total_input_tokens,
            "tokens_output": self.total_output_tokens,
            "cost_usd": round(self.total_cost_usd, 4),
            "elapsed": self.elapsed(),
        }
