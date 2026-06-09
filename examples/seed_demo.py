"""Create a small demo SQLite database to try TablePro against.

    python examples/seed_demo.py            # writes demo.sqlite
    tablepro demo.sqlite                     # then explore it
"""

import sqlite3
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "demo.sqlite"
c = sqlite3.connect(path)
c.executescript(
    """
    DROP TABLE IF EXISTS albums;
    DROP TABLE IF EXISTS artists;
    CREATE TABLE artists (id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT);
    CREATE TABLE albums  (id INTEGER PRIMARY KEY, artist_id INTEGER, title TEXT, year INTEGER,
                          FOREIGN KEY (artist_id) REFERENCES artists(id));
    """
)
c.executemany("INSERT INTO artists (name, country) VALUES (?, ?)",
              [("Sevdaliza", "NL"), ("Rosalía", "ES"), ("Hozier", "IE"), ("FKA twigs", "UK")])
c.executemany("INSERT INTO albums (artist_id, title, year) VALUES (?, ?, ?)",
              [(1, "ISON", 2017), (2, "Motomami", 2022), (3, "Unreal Unearth", 2023)])
c.commit()
c.close()
print(f"Wrote {path}")
