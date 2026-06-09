"""Command-line entry point.

    tablepro mydb.sqlite                 # open the interactive shell
    tablepro mydb.sqlite tables          # list tables and exit
    tablepro mydb.sqlite schema users    # describe a table
    tablepro mydb.sqlite query "SELECT 1"
    tablepro mydb.sqlite query "SELECT * FROM users" --export users.csv

Works with SQLite paths, or postgres:// / mysql:// DSNs (optional drivers).
"""

from __future__ import annotations

import argparse
import sys

from . import format as fmt
from .db import Database
from .export import export_result
from .repl import Repl


def main(argv: list[str] | None = None) -> int:
    # Ensure non-ASCII output (box-drawing, accents, separators) never crashes
    # on a legacy code-page console such as Windows cp1252.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        prog="tablepro",
        description="A free, open-source terminal database manager.",
    )
    parser.add_argument("dsn", help="SQLite path or postgres://… / mysql://… DSN")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("tables", help="List tables and exit.")

    p_schema = sub.add_parser("schema", help="Describe a table.")
    p_schema.add_argument("table")

    p_head = sub.add_parser("head", help="Preview the first rows of a table.")
    p_head.add_argument("table")
    p_head.add_argument("-n", type=int, default=20)

    p_query = sub.add_parser("query", help="Run a SQL statement.")
    p_query.add_argument("sql")
    p_query.add_argument("--export", metavar="FILE", help="Write results to .csv/.tsv/.json")

    args = parser.parse_args(argv)

    try:
        db = Database(args.dsn)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        if args.command is None:
            Repl(db).run()
        elif args.command == "tables":
            fmt.render_tables(db.list_tables())
        elif args.command == "schema":
            fmt.render_schema(args.table, db.table_info(args.table), db.row_count(args.table))
        elif args.command == "head":
            fmt.render_result(db.preview(args.table, limit=args.n), title=args.table)
        elif args.command == "query":
            result = db.execute(args.sql)
            fmt.render_result(result)
            if args.export and result.is_rowset:
                n = export_result(result, args.export)
                print(f"Exported {n} row(s) to {args.export}")
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
