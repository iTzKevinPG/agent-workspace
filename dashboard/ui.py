"""
Dashboard de terminal usando Rich.
Se actualiza en tiempo real mientras el orquestador trabaja.
"""
from __future__ import annotations

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from dashboard.state import DashboardState, TaskStatus

console = Console()

# ─── Iconos y colores por estado ─────────────────────────────────────

STATUS_STYLE = {
    TaskStatus.WAITING:  ("○", "dim"),
    TaskStatus.RUNNING:  ("⟳", "yellow"),
    TaskStatus.DONE:     ("✓", "green"),
    TaskStatus.FAILED:   ("✗", "red"),
    TaskStatus.BLOCKED:  ("⚠", "magenta"),
    TaskStatus.SKIPPED:  ("–", "dim"),
}


def _tasks_table(state: DashboardState) -> Table:
    t = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold dim",
        pad_edge=False,
        expand=True,
    )
    t.add_column("AGENTE",   style="dim",  width=12)
    t.add_column("TAREA",                  ratio=1)
    t.add_column("ESTADO",                 width=12)
    t.add_column("TIEMPO",   justify="right", width=9)

    for task in state.tasks:
        icon, style = STATUS_STYLE.get(task.status, ("?", "white"))
        status_text = Text(f"{icon} {task.status.value}", style=style)

        # Tarea: truncar si es muy larga
        desc = task.description
        if len(desc) > 60:
            desc = desc[:57] + "..."

        t.add_row(
            task.agent,
            desc,
            status_text,
            task.elapsed(),
        )

    return t


def _files_table(state: DashboardState) -> Table | None:
    all_files: list[tuple[str, str]] = []
    for task in state.tasks:
        if task.files_modified:
            for f in task.files_modified:
                all_files.append((task.agent, f))

    if not all_files:
        return None

    t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", pad_edge=False)
    t.add_column("AGENTE", style="dim", width=12)
    t.add_column("ARCHIVO MODIFICADO")

    for agent, filepath in all_files[-8:]:  # máximo últimos 8
        t.add_row(agent, Text(filepath, style="cyan"))

    return t


def _alerts_panel(state: DashboardState) -> Panel | None:
    alerts = state.alerts()
    if not alerts:
        return None

    lines = []
    for task in alerts:
        icon = "⚠" if task.status == TaskStatus.BLOCKED else "✗"
        lines.append(Text.assemble(
            (f"  {icon} ", "yellow" if task.status == TaskStatus.BLOCKED else "red"),
            (f"[{task.agent}] ", "dim"),
            (task.description[:50], "white"),
            ("\n", ""),
            (f"    → {task.alert}", "dim"),
        ))

    content = Text("\n").join(lines)
    return Panel(content, title="[bold yellow]necesita tu atención[/]", border_style="yellow", padding=(0, 1))


def _footer(state: DashboardState) -> Text:
    t = Text(justify="left", style="dim")
    t.append(f"  tokens: {state.tokens_today:,}  ·  ")
    t.append(f"costo: ${state.cost_today:.4f}  ·  ")
    t.append(f"sesión: {state.session_elapsed}")
    t.append("      ")
    t.append("[q]", style="bold white")
    t.append(" salir  ")
    t.append("[s]", style="bold white")
    t.append(" skip  ")
    t.append("[↵]", style="bold white")
    t.append(" nueva tarea")
    return t


def build_layout(state: DashboardState) -> Panel:
    """Construye el panel completo del dashboard."""
    sections = []

    # Header
    header = Text.assemble(
        ("  ", ""),
        (state.namespace, "bold green"),
        ("  ·  ", "dim"),
        (state.project or "sin proyecto activo", "white"),
    )
    if state.namespace_skills:
        header.append("  ·  skills: " + ", ".join(state.namespace_skills), style="dim cyan")
    if state.current_task_description:
        header.append(f"\n  {state.current_task_description[:80]}", style="dim")

    sections.append(Panel(header, border_style="green", padding=(0, 0)))

    # Tareas
    if state.tasks:
        sections.append(Panel(
            _tasks_table(state),
            title="[bold]tareas[/]",
            border_style="dim",
            padding=(0, 1),
        ))

    # Archivos modificados
    files_t = _files_table(state)
    if files_t:
        sections.append(Panel(
            files_t,
            title="[bold]archivos modificados[/]",
            border_style="dim",
            padding=(0, 1),
        ))

    # Alertas
    alerts_panel = _alerts_panel(state)
    if alerts_panel:
        sections.append(alerts_panel)

    # Footer con métricas
    sections.append(_footer(state))

    # Combinar todo en un panel maestro
    from rich.console import Group
    return Panel(
        Group(*sections),
        title="[bold green]agent-workspace[/]",
        border_style="green",
        padding=(0, 0),
    )


class Dashboard:
    """
    Wrapper para usar el dashboard como contexto:

        with Dashboard(state) as dash:
            # el orquestador actualiza state
            dash.refresh()
    """

    def __init__(self, state: DashboardState):
        self.state = state
        self._live: Live | None = None

    def __enter__(self):
        self._live = Live(
            build_layout(self.state),
            console=console,
            refresh_per_second=2,
            screen=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)

    def refresh(self):
        if self._live:
            self._live.update(build_layout(self.state))

    def print_final(self):
        """Imprime el estado final una vez cerrado el Live."""
        console.print(build_layout(self.state))


def print_welcome(namespace: str, project: str):
    console.print(Panel(
        Text.assemble(
            ("agent-workspace\n", "bold green"),
            (f"namespace: {namespace}\n", "white"),
            (f"proyecto:  {project or '(ninguno)'}\n", "white"),
            ("\nEscribe una tarea o 'salir' para terminar.", "dim"),
        ),
        border_style="green",
        padding=(1, 2),
    ))


def print_error(msg: str):
    console.print(f"[red]✗[/] {msg}")


def print_info(msg: str):
    console.print(f"[dim]→[/] {msg}")
