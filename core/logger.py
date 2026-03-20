"""
Logger de sesion: tokens consumidos, costos, tiempos y errores.
Alimenta el dashboard con metricas en tiempo real y persiste el historial.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOGS_DIR = ROOT / "logs"
USAGE_FILE = LOGS_DIR / "usage_history.json"

# Precios Anthropic por modelo (por millon de tokens)
MODEL_PRICES = {
    "claude-haiku-4-5":            {"input": 0.80,  "output": 4.00},
    "claude-haiku-4-5-20251001":   {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":           {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":             {"input": 15.00, "output": 75.00},
}


def _load_history() -> dict:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_input_tokens": 0, "total_output_tokens": 0, "total_cost_usd": 0.0, "sessions": []}


def _save_history(data: dict):
    LOGS_DIR.mkdir(exist_ok=True)
    USAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_total_cost() -> float:
    return _load_history().get("total_cost_usd", 0.0)


def get_total_tokens() -> int:
    h = _load_history()
    return h.get("total_input_tokens", 0) + h.get("total_output_tokens", 0)


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

        self._log_path = LOGS_DIR / f"{namespace}_{project}_{self.session_id}.jsonl"
        self._outputs_path = LOGS_DIR / f"{namespace}_{project}_{self.session_id}_outputs.jsonl"

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
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Persistir inmediatamente para no perder datos si la app muere
        self._flush_to_history()

        alert = float(os.getenv("COST_ALERT_USD", "2.00"))
        if self.total_cost_usd >= alert:
            self._log.warning(
                f"Alerta de costo: ${self.total_cost_usd:.2f} USD en esta sesion "
                f"(limite: ${alert})"
            )

    def _flush_to_history(self):
        """
        Upsert de la sesion actual en usage_history.json.
        Recalcula los totales desde todas las sesiones para evitar duplicados.
        """
        if self.total_input_tokens == 0 and self.total_output_tokens == 0:
            return

        history = _load_history()

        session_entry = {
            "id": self.session_id,
            "namespace": self.namespace,
            "project": self.project,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cost_usd": round(self.total_cost_usd, 6),
            "elapsed": self.elapsed(),
            "status": "active",
        }

        # Upsert: reemplazar entrada existente de esta sesion o agregar nueva
        sessions = history.get("sessions", [])
        idx = next((i for i, s in enumerate(sessions) if s.get("id") == self.session_id), None)
        if idx is not None:
            sessions[idx] = session_entry
        else:
            sessions.append(session_entry)
        history["sessions"] = sessions

        # Recalcular totales desde todas las sesiones (evita doble conteo)
        history["total_input_tokens"] = sum(s["input_tokens"] for s in sessions)
        history["total_output_tokens"] = sum(s["output_tokens"] for s in sessions)
        history["total_cost_usd"] = round(sum(s["cost_usd"] for s in sessions), 6)

        _save_history(history)

    def log_agent_output(self, agent: str, task: str, output: str, files: list[str], status: str):
        """Persiste el output completo de un agente en el archivo de outputs de la sesion."""
        entry = {
            "ts": datetime.now().isoformat(),
            "agent": agent,
            "task": task[:200],
            "status": status,
            "files_modified": files,
            "output": output,
        }
        with open(self._outputs_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_session_end(self):
        """Marca la sesion como completada en usage_history.json."""
        if self.total_input_tokens == 0 and self.total_output_tokens == 0:
            return

        history = _load_history()
        sessions = history.get("sessions", [])
        idx = next((i for i, s in enumerate(sessions) if s.get("id") == self.session_id), None)
        if idx is not None:
            sessions[idx]["status"] = "done"
            sessions[idx]["elapsed"] = self.elapsed()
        history["sessions"] = sessions
        _save_history(history)

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
