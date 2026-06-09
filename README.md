# TablePro

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-12%20passing-brightgreen.svg)](tests/)

**A free, open-source terminal database manager.** Browse tables, inspect
schemas, run SQL, and export results — all from a clean, rich-rendered
terminal UI. Works with **SQLite** out of the box; **Postgres** and **MySQL**
via optional drivers.

> Built from scratch to explore database introspection across dialects, safe
> identifier quoting, and building an ergonomic CLI + REPL on top of one small
> connection abstraction.

---

## Install

```bash
pip install -e .                 # core (SQLite)
pip install -e ".[postgres]"     # + Postgres (psycopg)
pip install -e ".[mysql]"        # + MySQL (PyMySQL)
```

## Use it in 30 seconds

```bash
python examples/seed_demo.py     # writes demo.sqlite
tablepro demo.sqlite             # open the interactive shell
```

```text
┌─────────┬─────────┬──────────┬────┐
│ column  │ type    │ nullable │ pk │
├─────────┼─────────┼──────────┼────┤
│ id      │ INTEGER │ yes      │ PK │
│ name    │ TEXT    │ no       │    │
│ country │ TEXT    │ yes      │    │
└─────────┴─────────┴──────────┴────┘
```

### One-shot commands (no shell)

```bash
tablepro demo.sqlite tables                       # list tables
tablepro demo.sqlite schema artists               # describe a table
tablepro demo.sqlite head albums -n 5             # preview rows
tablepro demo.sqlite query "SELECT * FROM artists"
tablepro demo.sqlite query "SELECT * FROM artists" --export out.csv
```

### Interactive shell (dot-commands)

```text
tablepro> .tables
tablepro> .schema artists
tablepro> .head albums 5
tablepro> SELECT ar.name, al.title, al.year
      ...> FROM albums al JOIN artists ar ON ar.id = al.artist_id
      ...> ORDER BY al.year;
tablepro> .export results.json
tablepro> .quit
```

## Connection strings

| Target | DSN |
|--------|-----|
| SQLite file | `mydata.sqlite` or `sqlite:///mydata.sqlite` |
| SQLite memory | `:memory:` |
| Postgres | `postgres://user:pass@host:5432/dbname` |
| MySQL | `mysql://user:pass@host:3306/dbname` |

## Design

```
cli.py        argparse front-end + one-shot subcommands
repl.py       interactive shell (SQL + dot-commands), remembers last result
db.py         Database: dialect detection, execution, introspection, quoting
format.py     rich-rendered tables / schema / result sets
export.py     CSV / TSV / JSON export
```

Everything funnels through one `Database` class, so a new dialect is one branch
in `db.py` and nothing downstream changes. Identifiers are always quoted per
dialect (a table literally named `weird "name` round-trips safely), and writes
report affected-row counts while SELECTs return a proper row set.

## Safety notes

- Identifier quoting is dialect-aware and escapes embedded quotes/backticks.
- Output is forced to UTF-8 so box-drawing and accents never crash a legacy
  Windows code-page console.
- Exporting refuses non-SELECT statements (nothing to write).

## Test

```bash
pytest -q        # 12 tests against a temp SQLite database
```

## License

MIT — see [LICENSE](LICENSE).
