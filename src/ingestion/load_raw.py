"""Load downloaded CSVs from raw_files/ into the raw.* tables in SQL Server.

Every source column lands as text; empty fields become NULL. Each file load is logged in raw.load_batch.
Loads are idempotent: a per-season file replaces that season's rows, a single-file dataset replaces the table.
Columns in a file that are missing from the table fail the load (schema drift). Columns missing from a
file load as NULL and log a warning.

Usage:
    python -m src.ingestion.load_raw --apply-ddl
    python -m src.ingestion.load_raw --datasets injuries --seasons 2025
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import sys
from pathlib import Path
from typing import Any, Iterator

from src.utilities.config import Config, load_config

log = logging.getLogger("load_raw")

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CHUNK_ROWS = 5000


class LoadError(Exception):
    """A load failed or could not start."""


class SchemaDriftError(LoadError):
    """The file has columns the raw table does not."""


def _ident(name: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"unsafe SQL identifier: {name!r}")
    return name


def _q(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def discover_files(raw_dir: Path, dataset: str) -> dict[int | None, Path]:
    """Map season (None for single-file datasets) to the file from the most recent load_date."""
    found: dict[int | None, Path] = {}
    base = raw_dir / dataset
    if not base.is_dir():
        return found
    for load_dir in sorted(p for p in base.glob("load_date=*") if p.is_dir()):
        for path in sorted(load_dir.rglob("*.csv")):
            season = None
            for part in path.relative_to(load_dir).parts:
                if part.startswith("season="):
                    season = int(part.split("=", 1)[1])
            found[season] = path
    return found


def table_columns(cursor, schema: str, table: str) -> list[str]:
    """Source columns of a raw table in order, excluding the _metadata columns."""
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
        schema,
        table,
    )
    return [r[0] for r in cursor.fetchall() if not r[0].startswith("_")]


def read_rows(path: Path, table_cols: list[str]) -> Iterator[tuple[Any, ...]]:
    """Yield one tuple per CSV row, ordered as table_cols. Empty fields become None."""
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        unexpected = [c for c in header if c not in table_cols]
        if unexpected:
            raise SchemaDriftError(f"{path.name} has columns not in the raw table: {unexpected}")
        missing = [c for c in table_cols if c not in header]
        if missing:
            log.warning("%s is missing columns, loading NULL: %s", path.name, missing)
        index = {c: i for i, c in enumerate(header)}
        positions = [index.get(c) for c in table_cols]
        for row in reader:
            yield tuple(
                None if (p is None or p >= len(row) or row[p] == "") else row[p] for p in positions
            )


def _file_facts(path: Path) -> tuple[str, int]:
    sha = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            sha.update(chunk)
    with path.open("r", newline="", encoding="utf-8") as fh:
        rows = sum(1 for _ in csv.reader(fh)) - 1
    return sha.hexdigest(), rows


def load_file(conn, cfg: Config, dataset: str, spec: dict, path: Path, season: int | None) -> int:
    """Load one file. Returns the number of rows loaded. Raises LoadError if row counts don't reconcile."""
    schema = _ident(cfg.get("database.schemas.raw"))
    table = _ident(spec["table"])
    full = f"{schema}.{table}"
    source_file = path.relative_to(cfg.raw_files_dir).as_posix()
    cur = conn.cursor()

    cols = table_columns(cur, schema, table)
    if not cols:
        raise LoadError(f"{full} not found. Run with --apply-ddl first.")

    sha, rows_in_file = _file_facts(path)
    cur.execute(
        f"INSERT INTO {schema}.load_batch (dataset, source_file, file_sha256, rows_in_file, status) "
        "OUTPUT INSERTED.batch_id VALUES (?, ?, ?, ?, 'running')",
        dataset,
        source_file,
        sha,
        rows_in_file,
    )
    batch_id = cur.fetchone()[0]
    conn.commit()

    try:
        if season is not None:
            cur.execute(f"DELETE FROM {full} WHERE [season] = ?", str(season))
        else:
            cur.execute(f"DELETE FROM {full}")

        insert_cols = ["_batch_id", "_source_file", *cols]
        insert_sql = (
            f"INSERT INTO {full} ({', '.join(_q(c) for c in insert_cols)}) "
            f"VALUES ({', '.join('?' for _ in insert_cols)})"
        )
        cur.fast_executemany = True
        loaded, buffer = 0, []
        for row in read_rows(path, cols):
            buffer.append((batch_id, source_file, *row))
            if len(buffer) >= CHUNK_ROWS:
                cur.executemany(insert_sql, buffer)
                loaded += len(buffer)
                buffer = []
        if buffer:
            cur.executemany(insert_sql, buffer)
            loaded += len(buffer)

        if loaded != rows_in_file:
            raise LoadError(f"row count mismatch for {source_file}: file={rows_in_file} loaded={loaded}")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        cur.execute(
            f"UPDATE {schema}.load_batch SET status = 'failed', finished_at = SYSUTCDATETIME(), error = ? "
            "WHERE batch_id = ?",
            str(exc)[:4000],
            batch_id,
        )
        conn.commit()
        raise

    cur.execute(
        f"UPDATE {schema}.load_batch SET status = 'succeeded', rows_loaded = ?, finished_at = SYSUTCDATETIME() "
        "WHERE batch_id = ?",
        loaded,
        batch_id,
    )
    conn.commit()
    return loaded


def load_all(conn, cfg: Config, datasets: list[str] | None = None, seasons: list[int] | None = None) -> list[dict]:
    registry: dict[str, dict] = cfg.get("source.datasets")
    names = datasets or list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise LoadError(f"unknown datasets: {unknown}. Configured: {list(registry)}")

    summary = []
    for name in names:
        files = discover_files(cfg.raw_files_dir, name)
        if not files:
            raise LoadError(f"no files for {name} under {cfg.raw_files_dir}. Run the extract first.")
        for season, path in sorted(files.items(), key=lambda kv: (kv[0] is None, kv[0])):
            if seasons and season is not None and season not in seasons:
                continue
            rows = load_file(conn, cfg, name, registry[name], path, season)
            log.info("%s %s: loaded %d rows", name, season or "all", rows)
            summary.append({"dataset": name, "season": season, "rows": rows})
    return summary


def main(argv: list[str] | None = None) -> int:
    from src.utilities.db import apply_sql_dir, connect

    parser = argparse.ArgumentParser(description="Load raw_files/ into SQL Server raw.* tables")
    parser.add_argument("--env", default=None)
    parser.add_argument("--datasets", nargs="+")
    parser.add_argument("--seasons", nargs="+", type=int)
    parser.add_argument("--apply-ddl", action="store_true", help="run sql/raw/*.sql first")
    args = parser.parse_args(argv)

    cfg = load_config(args.env)
    logging.basicConfig(level=cfg.get("logging.level", "INFO"), format="%(asctime)s %(levelname)s %(message)s")

    conn = connect(cfg)
    try:
        if args.apply_ddl:
            applied = apply_sql_dir(conn, cfg.path("paths.sql") / "raw")
            log.info("applied DDL: %s", ", ".join(applied))
        summary = load_all(conn, cfg, args.datasets, args.seasons)
    finally:
        conn.close()

    print(f"loaded {len(summary)} files, {sum(s['rows'] for s in summary)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
