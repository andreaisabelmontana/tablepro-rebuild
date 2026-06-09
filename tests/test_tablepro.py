"""Tests for TablePro against a temporary SQLite database."""

import json

import pytest

from tablepro import Database, export_result
from tablepro.cli import main


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.sqlite"
    d = Database(str(path))
    d.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER)")
    d.execute("INSERT INTO users (name, age) VALUES (?, ?)", ["Nino", 30])
    d.execute("INSERT INTO users (name, age) VALUES (?, ?)", ["Giorgi", 25])
    d.execute("CREATE TABLE empty_t (a TEXT)")
    yield d
    d.close()


def test_detects_sqlite_dialect(db):
    assert db.dialect == "sqlite"


def test_list_tables(db):
    assert db.list_tables() == ["empty_t", "users"]


def test_table_info_and_pk(db):
    cols = {c.name: c for c in db.table_info("users")}
    assert set(cols) == {"id", "name", "age"}
    assert cols["id"].primary_key is True
    assert cols["name"].nullable is False
    assert cols["age"].nullable is True


def test_row_count_and_preview(db):
    assert db.row_count("users") == 2
    res = db.preview("users", limit=1)
    assert res.is_rowset and len(res.rows) == 1


def test_select_returns_rowset(db):
    res = db.execute("SELECT name, age FROM users ORDER BY age")
    assert res.columns == ["name", "age"]
    assert res.rows == [("Giorgi", 25), ("Nino", 30)]


def test_write_returns_rowcount(db):
    res = db.execute("UPDATE users SET age = age + 1")
    assert not res.is_rowset
    assert res.rowcount == 2


def test_identifier_quoting_blocks_injection(db):
    # A weird table name must round-trip safely through quoting.
    db.execute('CREATE TABLE "weird ""name" (x INTEGER)')
    assert 'weird "name' in db.list_tables()
    assert db.row_count('weird "name') == 0


def test_export_csv_and_json(db, tmp_path):
    res = db.execute("SELECT name, age FROM users ORDER BY name")
    csv_path = tmp_path / "out.csv"
    json_path = tmp_path / "out.json"

    assert export_result(res, csv_path) == 2
    assert export_result(res, json_path) == 2

    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "name,age"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0] == {"name": "Giorgi", "age": 25}


def test_export_rejects_non_select(db):
    res = db.execute("UPDATE users SET age = 40 WHERE name = 'Nino'")
    with pytest.raises(ValueError):
        export_result(res, "nope.csv")


def test_unsupported_dsn_scheme():
    with pytest.raises(ValueError):
        Database("redis://localhost")


def test_cli_tables_and_query(db, tmp_path, capsys):
    path = db.dsn
    assert main([path, "tables"]) == 0
    assert main([path, "query", "SELECT COUNT(*) FROM users"]) == 0
    out = capsys.readouterr().out
    assert "users" in out


def test_cli_query_export(db, tmp_path):
    out_file = tmp_path / "export.json"
    rc = main([db.dsn, "query", "SELECT * FROM users", "--export", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    assert len(json.loads(out_file.read_text(encoding="utf-8"))) == 2
