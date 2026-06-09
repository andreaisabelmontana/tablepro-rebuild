"""Render result sets and schemas as terminal tables (via rich)."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .db import Column, QueryResult

console = Console()


def render_result(result: QueryResult, title: str | None = None, max_cell: int = 60) -> None:
    if not result.is_rowset:
        console.print(f"[green]OK[/green] — {result.rowcount} row(s) affected.")
        return
    if not result.rows:
        console.print("[yellow](no rows)[/yellow]")
        return

    table = Table(title=title, header_style="bold cyan", row_styles=["", "dim"])
    for col in result.columns:
        table.add_column(str(col), overflow="fold")
    for row in result.rows:
        table.add_row(*[_cell(v, max_cell) for v in row])
    console.print(table)
    console.print(f"[dim]{len(result.rows)} row(s)[/dim]")


def render_schema(table_name: str, columns: list[Column], n_rows: int) -> None:
    t = Table(title=f"{table_name}  ·  {n_rows} rows", header_style="bold cyan")
    t.add_column("column")
    t.add_column("type")
    t.add_column("nullable")
    t.add_column("pk")
    for c in columns:
        t.add_row(c.name, c.type, "yes" if c.nullable else "no",
                  "PK" if c.primary_key else "")
    console.print(t)


def render_tables(names: list[str]) -> None:
    if not names:
        console.print("[yellow]No tables found.[/yellow]")
        return
    t = Table(title=f"{len(names)} table(s)", header_style="bold cyan")
    t.add_column("#", justify="right")
    t.add_column("table")
    for i, name in enumerate(names, 1):
        t.add_row(str(i), name)
    console.print(t)


def _cell(value, max_cell: int) -> str:
    if value is None:
        return "[dim]NULL[/dim]"
    s = str(value)
    return s if len(s) <= max_cell else s[: max_cell - 1] + "…"
