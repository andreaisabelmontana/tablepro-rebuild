"""Database connection abstraction.

One small wrapper that speaks SQLite out of the box (stdlib) and, when the
optional drivers are installed, Postgres (psycopg) and MySQL (PyMySQL). The
rest of TablePro only ever touches this interface, so adding a dialect means
adding one branch here — nothing downstream changes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Sequence
from urllib.parse import urlparse


@dataclass
class Column:
    name: str
    type: str
    nullable: bool
    primary_key: bool


@dataclass
class QueryResult:
    """A SELECT result, or the affected-row count of a write."""
    columns: list[str]
    rows: list[tuple]
    rowcount: int = -1

    @property
    def is_rowset(self) -> bool:
        return bool(self.columns)


class Database:
    """Dialect-aware connection wrapper."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.dialect, self._conn = self._connect(dsn)

    # ---------------------------------------------------------------- connect --
    @staticmethod
    def _connect(dsn: str) -> tuple[str, Any]:
        # Only treat the input as a URL-style DSN if it starts with a known
        # network scheme. Anything else is a filesystem path for SQLite — this
        # avoids Windows drive letters ("C:\db.sqlite") being misread as a
        # URL scheme by urlparse.
        if "://" not in dsn:
            # Bare path -> SQLite file (":memory:" supported).
            conn = sqlite3.connect(dsn)
            conn.row_factory = sqlite3.Row
            return "sqlite", conn

        scheme = urlparse(dsn).scheme.lower()
        if scheme in ("sqlite", "file"):
            path = dsn.split("://", 1)[1] or ":memory:"
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            return "sqlite", conn
        if scheme in ("postgres", "postgresql"):
            try:
                import psycopg
            except ImportError as e:  # pragma: no cover - optional dep
                raise RuntimeError("Postgres support needs: pip install 'tablepro[postgres]'") from e
            return "postgres", psycopg.connect(dsn)
        if scheme == "mysql":
            try:
                import pymysql
            except ImportError as e:  # pragma: no cover - optional dep
                raise RuntimeError("MySQL support needs: pip install 'tablepro[mysql]'") from e
            p = urlparse(dsn)
            conn = pymysql.connect(
                host=p.hostname or "localhost", port=p.port or 3306,
                user=p.username, password=p.password, database=(p.path or "/").lstrip("/"),
            )
            return "mysql", conn

        raise ValueError(f"Unsupported DSN scheme: {scheme!r}")

    # ------------------------------------------------------------- identifiers --
    def quote_ident(self, name: str) -> str:
        """Safely quote a table/column identifier for the active dialect."""
        if self.dialect == "mysql":
            return "`" + name.replace("`", "``") + "`"
        return '"' + name.replace('"', '""') + '"'

    # -------------------------------------------------------------- execution --
    def execute(self, sql: str, params: Sequence[Any] | None = None) -> QueryResult:
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params or [])
            if cur.description:
                columns = [d[0] for d in cur.description]
                rows = [tuple(r) for r in cur.fetchall()]
                return QueryResult(columns=columns, rows=rows)
            self._conn.commit()
            return QueryResult(columns=[], rows=[], rowcount=cur.rowcount)
        finally:
            cur.close()

    # ----------------------------------------------------------- introspection --
    def list_tables(self) -> list[str]:
        if self.dialect == "sqlite":
            q = ("SELECT name FROM sqlite_master "
                 "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        elif self.dialect == "postgres":
            q = ("SELECT table_name FROM information_schema.tables "
                 "WHERE table_schema='public' ORDER BY table_name")
        else:  # mysql
            q = "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE()"
        return [r[0] for r in self.execute(q).rows]

    def table_info(self, table: str) -> list[Column]:
        if self.dialect == "sqlite":
            res = self.execute(f"PRAGMA table_info({self.quote_ident(table)})")
            # cid, name, type, notnull, dflt_value, pk
            return [Column(r[1], r[2] or "", not r[3], bool(r[5])) for r in res.rows]
        # ANSI information_schema path for postgres/mysql.
        res = self.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns WHERE table_name = %s "
            "ORDER BY ordinal_position"
            if self.dialect != "sqlite" else "",
            [table],
        )
        return [Column(r[0], r[1], r[2] == "YES", False) for r in res.rows]

    def row_count(self, table: str) -> int:
        res = self.execute(f"SELECT COUNT(*) FROM {self.quote_ident(table)}")
        return int(res.rows[0][0]) if res.rows else 0

    def preview(self, table: str, limit: int = 50, offset: int = 0) -> QueryResult:
        return self.execute(
            f"SELECT * FROM {self.quote_ident(table)} LIMIT {int(limit)} OFFSET {int(offset)}"
        )

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # pragma: no cover
            pass

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
