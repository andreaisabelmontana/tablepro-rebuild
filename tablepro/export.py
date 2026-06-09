"""Export query results to CSV or JSON."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .db import QueryResult


def export_result(result: QueryResult, path: str | Path) -> int:
    """Write a result set to ``path``; format inferred from extension.
    Returns the number of data rows written."""
    path = Path(path)
    if not result.is_rowset:
        raise ValueError("Cannot export a non-SELECT statement.")

    fmt = path.suffix.lower().lstrip(".")
    if fmt == "json":
        records = [dict(zip(result.columns, row)) for row in result.rows]
        path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    elif fmt in ("csv", "tsv"):
        delim = "\t" if fmt == "tsv" else ","
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, delimiter=delim)
            writer.writerow(result.columns)
            writer.writerows(result.rows)
    else:
        raise ValueError(f"Unsupported export format: {fmt!r} (use .csv, .tsv or .json)")
    return len(result.rows)
