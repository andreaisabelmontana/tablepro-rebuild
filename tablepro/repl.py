"""Interactive shell.

Type SQL (terminated by ``;``) to run it, or use a dot-command for common
chores. The last result set is remembered so you can ``.export`` it.
"""

from __future__ import annotations

from .db import Database
from . import format as fmt
from .export import export_result

HELP = """\
[bold]TablePro commands[/bold]
  [cyan].tables[/cyan]               list tables
  [cyan].schema <table>[/cyan]      show a table's columns + row count
  [cyan].head <table> [n][/cyan]    preview first n rows (default 20)
  [cyan].export <file>[/cyan]       export the last result to .csv/.tsv/.json
  [cyan].help[/cyan]                show this help
  [cyan].quit[/cyan]                exit
Anything else is run as SQL (end statements with ;).
"""


class Repl:
    def __init__(self, db: Database):
        self.db = db
        self.last_result = None
        self.console = fmt.console

    def run(self) -> None:
        self.console.print(
            f"[bold green]TablePro[/bold green] — connected to "
            f"[cyan]{self.db.dsn}[/cyan] ([magenta]{self.db.dialect}[/magenta]). "
            "Type [cyan].help[/cyan]."
        )
        buffer = ""
        while True:
            try:
                prompt = "tablepro> " if not buffer else "      ...> "
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]bye[/dim]")
                break

            stripped = line.strip()
            if not buffer and stripped.startswith("."):
                if self._dot_command(stripped):
                    break
                continue

            buffer += line + "\n"
            if ";" in line:
                self._run_sql(buffer.strip().rstrip(";"))
                buffer = ""

    # ---------------------------------------------------------- dot-commands --
    def _dot_command(self, line: str) -> bool:
        """Return True to signal exit."""
        parts = line.split()
        cmd, args = parts[0], parts[1:]
        if cmd in (".quit", ".exit", ".q"):
            return True
        if cmd == ".help":
            self.console.print(HELP)
        elif cmd in (".tables", ".dt"):
            fmt.render_tables(self.db.list_tables())
        elif cmd in (".schema", ".d"):
            if not args:
                self.console.print("[red]usage: .schema <table>[/red]")
            else:
                self._schema(args[0])
        elif cmd == ".head":
            if not args:
                self.console.print("[red]usage: .head <table> [n][/red]")
            else:
                n = int(args[1]) if len(args) > 1 else 20
                self.last_result = self.db.preview(args[0], limit=n)
                fmt.render_result(self.last_result, title=args[0])
        elif cmd == ".export":
            self._export(args)
        else:
            self.console.print(f"[red]unknown command {cmd!r}[/red] — try .help")
        return False

    def _schema(self, table: str) -> None:
        try:
            cols = self.db.table_info(table)
            n = self.db.row_count(table)
            fmt.render_schema(table, cols, n)
        except Exception as e:  # noqa: BLE001
            self.console.print(f"[red]{e}[/red]")

    def _export(self, args) -> None:
        if not args:
            self.console.print("[red]usage: .export <file.csv|.tsv|.json>[/red]")
            return
        if not self.last_result or not self.last_result.is_rowset:
            self.console.print("[yellow]No result to export. Run a SELECT first.[/yellow]")
            return
        try:
            n = export_result(self.last_result, args[0])
            self.console.print(f"[green]Exported {n} row(s) to {args[0]}[/green]")
        except Exception as e:  # noqa: BLE001
            self.console.print(f"[red]{e}[/red]")

    # ----------------------------------------------------------------- SQL ----
    def _run_sql(self, sql: str) -> None:
        if not sql:
            return
        try:
            self.last_result = self.db.execute(sql)
            fmt.render_result(self.last_result)
        except Exception as e:  # noqa: BLE001
            self.console.print(f"[red]Error:[/red] {e}")
