"""SQL Server helpers. pyodbc is imported lazily so unit tests don't need it installed."""
from __future__ import annotations

from pathlib import Path

from src.utilities.config import Config


def connect(cfg: Config, autocommit: bool = False):
    import pyodbc

    return pyodbc.connect(cfg.connection_string(), autocommit=autocommit)


def apply_sql_dir(conn, directory: Path) -> list[str]:
    """Run every *.sql file in a directory in name order, one batch per file. Returns the names applied."""
    applied = []
    cur = conn.cursor()
    for path in sorted(Path(directory).glob("*.sql")):
        cur.execute(path.read_text(encoding="utf-8"))
        conn.commit()
        applied.append(path.name)
    return applied
