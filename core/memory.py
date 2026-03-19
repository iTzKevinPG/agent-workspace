"""
Memoria compartida entre agentes durante una sesión.
Guarda decisiones, archivos modificados y resumen de tareas anteriores.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
MEMORY_DIR = ROOT / "memory"


@dataclass
class TaskMemory:
    task: str
    agent: str
    status: str          # done | failed | blocked
    summary: str
    files_modified: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SessionMemory:
    """Memoria de la sesión actual — se limpia al arrancar."""

    def __init__(self, namespace: str, project: str):
        self.namespace = namespace
        self.project = project
        self.tasks: list[TaskMemory] = []
        self.decisions: list[str] = []
        self.context_notes: list[str] = []

    def add_task(self, task: TaskMemory):
        self.tasks.append(task)
        self._persist()

    def add_decision(self, decision: str):
        self.decisions.append(decision)
        self._persist()

    def add_note(self, note: str):
        self.context_notes.append(note)

    def summary_for_agents(self) -> str:
        """Resumen compacto para incluir en el contexto de cada agente."""
        if not self.tasks and not self.decisions:
            return "Primera tarea de esta sesión."

        lines = []
        if self.decisions:
            lines.append("Decisiones tomadas esta sesión:")
            lines.extend(f"  - {d}" for d in self.decisions)

        done = [t for t in self.tasks if t.status == "done"]
        if done:
            lines.append(f"\nTareas completadas ({len(done)}):")
            for t in done[-5:]:  # máximo últimas 5
                lines.append(f"  - [{t.agent}] {t.task}")
                if t.files_modified:
                    lines.append(f"    archivos: {', '.join(t.files_modified[:3])}")

        return "\n".join(lines) if lines else "Sin historial relevante aún."

    def _persist(self):
        """Guarda estado en disco para poder inspeccionar entre sesiones."""
        MEMORY_DIR.mkdir(exist_ok=True)
        path = MEMORY_DIR / f"{self.namespace}_{self.project}.json"
        data = {
            "namespace": self.namespace,
            "project": self.project,
            "tasks": [t.__dict__ for t in self.tasks],
            "decisions": self.decisions,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
