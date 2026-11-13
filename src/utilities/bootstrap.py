"""Build the database from nothing. Safe to re-run.

Steps: create the database (options and file sizes from database.bootstrap), optionally tune the SQL Server
instance, apply sql/<layer>/*.sql in order while recording each file's hash in meta.schema_version, then
verify the expected schemas and raw tables exist.

A file whose hash changed since it was applied stops the run: the DDL is written to be re-runnable, not to
alter existing tables, so a changed file needs a deliberate migration. Pass --accept-changes to re-run it.

Usage:
    python -m src.utilities.bootstrap
    python -m src.utilities.bootstrap --tune-instance
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
from pathlib import Path

from src.utilities.config import Config, load_config

log = logging.getLogger("bootstrap")

LAYERS = ("raw", "staging", "dim", "fact")
RECOVERY_MODELS = {"SIMPLE", "FULL", "BULK_LOGGED"}
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

META_DDL = """
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'meta') EXEC('CREATE SCHEMA meta');
IF OBJECT_ID('meta.schema_version', 'U') IS NULL
    CREATE TABLE meta.schema_version (
        file_path   NVARCHAR(260) NOT NULL CONSTRAINT PK_meta_schema_version PRIMARY KEY,
        file_sha256 CHAR(64)      NOT NULL,
        applied_at  DATETIME2(0)  NOT NULL CONSTRAINT DF_meta_schema_version_applied DEFAULT SYSUTCDATETIME()
    );
"""


class BootstrapError(Exception):
    """The bootstrap could not complete."""


def _ident(name: str) -> str:
    if not _IDENT.match(str(name)):
        raise BootstrapError(f"unsafe SQL identifier: {name!r}")
    return name


def _q(name: str) -> str:
    return "[" + _ident(name) + "]"


def _lit(value: str) -> str:
    return "N'" + value.replace("'", "''") + "'"


def ensure_database(master_conn, cfg: Config) -> bool:
    """Create the database if missing and set its options. Needs an autocommit connection. Returns True if created."""
    name = _ident(cfg.get("database.name"))
    opts = cfg.get("database.bootstrap", {}) or {}
    recovery = str(opts.get("recovery_model", "SIMPLE")).upper()
    if recovery not in RECOVERY_MODELS:
        raise BootstrapError(f"recovery_model must be one of {sorted(RECOVERY_MODELS)}, got {recovery!r}")

    cur = master_conn.cursor()
    cur.execute("SELECT recovery_model_desc, is_read_committed_snapshot_on FROM sys.databases WHERE name = ?", name)
    row = cur.fetchone()
    created = row is None
    if created:
        collation = opts.get("collation")
        sql = f"CREATE DATABASE {_q(name)}"
        if collation:
            sql += f" COLLATE {_ident(collation)}"
        cur.execute(sql)
        log.info("created database %s", name)
        _size_files(cur, name, opts)
        current_recovery, current_rcsi = None, False
    else:
        current_recovery, current_rcsi = row[0], bool(row[1])

    if current_recovery != recovery:
        cur.execute(f"ALTER DATABASE {_q(name)} SET RECOVERY {recovery}")
    want_rcsi = bool(opts.get("read_committed_snapshot", True))
    # Changing RCSI needs exclusive access, so only touch it when it differs.
    if current_rcsi != want_rcsi:
        state = "ON" if want_rcsi else "OFF"
        cur.execute(f"ALTER DATABASE {_q(name)} SET READ_COMMITTED_SNAPSHOT {state} WITH ROLLBACK IMMEDIATE")
    return created


def _size_files(cur, name: str, opts: dict) -> None:
    """Grow the new database's files to the configured size. Never shrinks."""
    targets = {"ROWS": opts.get("data_file_mb"), "LOG": opts.get("log_file_mb")}
    growth = opts.get("file_growth_mb")
    cur.execute("SELECT name, type_desc, size / 128 FROM sys.master_files WHERE database_id = DB_ID(?)", name)
    for logical, kind, current_mb in cur.fetchall():
        target = targets.get(kind)
        if not target or int(target) <= int(current_mb):
            continue
        change = f"SIZE = {int(target)}MB"
        if growth:
            change += f", FILEGROWTH = {int(growth)}MB"
        cur.execute(f"ALTER DATABASE {_q(name)} MODIFY FILE (NAME = {_lit(logical)}, {change})")


def tune_instance(master_conn, cfg: Config) -> list[str]:
    """Apply instance-wide settings from database.bootstrap.instance. Returns the setting names changed."""
    wanted = {
        "max server memory (MB)": "max_server_memory_mb",
        "max degree of parallelism": "max_degree_of_parallelism",
        "cost threshold for parallelism": "cost_threshold_for_parallelism",
    }
    inst = cfg.get("database.bootstrap.instance", {}) or {}
    cur = master_conn.cursor()
    cur.execute("EXEC sp_configure 'show advanced options', 1")
    cur.execute("RECONFIGURE")
    changed = []
    for setting, key in wanted.items():
        if inst.get(key) is not None:
            cur.execute(f"EXEC sp_configure {_lit(setting)}, {int(inst[key])}")
            changed.append(setting)
    cur.execute("RECONFIGURE")
    return changed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_migrations(conn, cfg: Config, accept_changes: bool = False) -> list[str]:
    """Apply sql/<layer>/*.sql not yet recorded in meta.schema_version. Returns the files applied."""
    cur = conn.cursor()
    cur.execute(META_DDL)
    conn.commit()
    cur.execute("SELECT file_path, file_sha256 FROM meta.schema_version")
    recorded = {r[0]: r[1] for r in cur.fetchall()}

    sql_root = cfg.path("paths.sql")
    files = [
        (f"{layer}/{p.name}", p)
        for layer in LAYERS
        for p in sorted((sql_root / layer).glob("*.sql"))
    ]
    hashes = {rel: _sha256(p) for rel, p in files}

    drifted = [rel for rel in hashes if rel in recorded and recorded[rel] != hashes[rel]]
    if drifted and not accept_changes:
        raise BootstrapError(
            f"files changed since they were applied: {', '.join(drifted)}. "
            "Write a migration, or re-run with --accept-changes if the file is safe to re-run."
        )

    applied = []
    for rel, path in files:
        if rel in recorded and rel not in drifted:
            continue
        cur.execute(path.read_text(encoding="utf-8"))
        cur.execute("DELETE FROM meta.schema_version WHERE file_path = ?", rel)
        cur.execute("INSERT INTO meta.schema_version (file_path, file_sha256) VALUES (?, ?)", rel, hashes[rel])
        conn.commit()
        applied.append(rel)
        log.info("applied %s", rel)
    return applied


def verify(conn, cfg: Config) -> None:
    """Raise BootstrapError if a configured schema or raw table is missing."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.schemas")
    schemas = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT s.name + '.' + t.name FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id")
    tables = {r[0] for r in cur.fetchall()}

    raw = cfg.get("database.schemas.raw")
    missing = [f"schema {s}" for s in (cfg.get("database.schemas", {}) or {}).values() if s not in schemas]
    needed = [f"{raw}.load_batch", "meta.schema_version"]
    needed += [f"{raw}.{spec['table']}" for spec in (cfg.get("source.datasets", {}) or {}).values()]
    missing += [f"table {t}" for t in needed if t not in tables]
    if missing:
        raise BootstrapError("bootstrap verification failed, missing: " + ", ".join(missing))


def bootstrap(cfg: Config, tune: bool = False, accept_changes: bool = False) -> dict:
    from src.utilities.db import connect

    master = connect(cfg, autocommit=True, database="master")
    try:
        created = ensure_database(master, cfg)
        tuned = tune_instance(master, cfg) if tune else []
    finally:
        master.close()

    conn = connect(cfg)
    try:
        applied = apply_migrations(conn, cfg, accept_changes)
        verify(conn, cfg)
    finally:
        conn.close()
    return {"created": created, "tuned": tuned, "applied": applied}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the database and apply the schema scripts")
    parser.add_argument("--env", default=None)
    parser.add_argument("--tune-instance", action="store_true", help="also set instance-wide memory and parallelism")
    parser.add_argument("--accept-changes", action="store_true", help="re-run SQL files changed since applied")
    args = parser.parse_args(argv)

    cfg = load_config(args.env)
    logging.basicConfig(level=cfg.get("logging.level", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    try:
        result = bootstrap(cfg, args.tune_instance, args.accept_changes)
    except BootstrapError as exc:
        log.error("%s", exc)
        return 1
    print(
        f"database {'created' if result['created'] else 'already existed'}; "
        f"applied {len(result['applied'])} files; tuned {len(result['tuned'])} instance settings"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
