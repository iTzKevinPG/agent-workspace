"""
Modelo de estado del dashboard.
El orquestador actualiza este estado; la UI lo lee y renderiza.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    WAITING  = "waiting"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    BLOCKED  = "blocked"
    SKIPPED  = "skipped"


@dataclass
class TaskState:
    id: str
    description: str
    agent: str
    status: TaskStatus = TaskStatus.WAITING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    files_modified: list[str] = field(default_factory=list)
    alert: str | None = None          # mensaje de alerta para el dev
    output_summary: str | None = None # resumen de lo que hizo el agente

    def elapsed(self) -> str:
        if not self.started_at:
            return "—"
        end = self.finished_at or datetime.now()
        delta = end - self.started_at
        m, s = divmod(int(delta.total_seconds()), 60)
        return f"{m}m {s:02d}s"


@dataclass
class DashboardState:
    namespace: str = ""
    project: str = ""
    current_task_description: str = ""
    tasks: list[TaskState] = field(default_factory=list)
    tokens_today: int = 0
    cost_today: float = 0.0
    session_elapsed: str = "0m 00s"
    paused: bool = False
    namespace_skills: list[str] = field(default_factory=list)

    # ─── Mutaciones que llama el orquestador ─────────────────────────

    def add_task(self, task_id: str, description: str, agent: str) -> TaskState:
        t = TaskState(id=task_id, description=description, agent=agent)
        self.tasks.append(t)
        return t

    def start_task(self, task_id: str):
        t = self._get(task_id)
        if t:
            t.status = TaskStatus.RUNNING
            t.started_at = datetime.now()

    def complete_task(self, task_id: str, files: list[str] = None, summary: str = None):
        t = self._get(task_id)
        if t:
            t.status = TaskStatus.DONE
            t.finished_at = datetime.now()
            t.files_modified = files or []
            t.output_summary = summary

    def fail_task(self, task_id: str, alert: str):
        t = self._get(task_id)
        if t:
            t.status = TaskStatus.FAILED
            t.finished_at = datetime.now()
            t.alert = alert

    def block_task(self, task_id: str, reason: str):
        t = self._get(task_id)
        if t:
            t.status = TaskStatus.BLOCKED
            t.alert = reason

    def skip_task(self, task_id: str):
        t = self._get(task_id)
        if t:
            t.status = TaskStatus.SKIPPED
            t.finished_at = datetime.now()

    def update_metrics(self, tokens: int, cost: float, elapsed: str):
        self.tokens_today = tokens
        self.cost_today = cost
        self.session_elapsed = elapsed

    def alerts(self) -> list[TaskState]:
        return [t for t in self.tasks if t.alert and t.status in (TaskStatus.FAILED, TaskStatus.BLOCKED)]

    def _get(self, task_id: str) -> TaskState | None:
        return next((t for t in self.tasks if t.id == task_id), None)
