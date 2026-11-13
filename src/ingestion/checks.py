"""Quality checks on freshly extracted files, run before anything is loaded into SQL Server.

Checks per downloaded file (driven by the manifests extract.py writes):
- schema: every column in the file must exist in the raw table's DDL under sql/raw/. A new column means
  nflverse changed the file format and the load would fail, so this catches it before touching the database.
- row count: rows must not drop below quality.min_rows_vs_previous_ratio of the previous download of the
  same dataset and season. The first download of a file has nothing to compare against and passes.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.utilities.config import Config

DEFAULT_MIN_ROWS_RATIO = 0.99


@dataclass(frozen=True)
class Finding:
    level: str  # "error" or "warning"
    dataset: str
    season: int | None
    check: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper()} {self.check} {self.dataset} {self.season or 'all'}: {self.message}"


def ddl_columns(sql_dir: Path, schema: str, table: str) -> list[str] | None:
    """Source columns (excluding _metadata) of CREATE TABLE <schema>.<table> in sql_dir, or None if absent."""
    pattern = re.compile(rf"CREATE TABLE\s+\[?{re.escape(schema)}\]?\.\[?{re.escape(table)}\]?\s*\(", re.I)
    for path in sorted(sql_dir.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if match:
            block = text[match.end():].split("\n    );", 1)[0]
            cols = re.findall(r"^\s+\[([^\]]+)\]", block, flags=re.M)
            return [c for c in cols if not c.startswith("_")]
    return None


def file_header(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh), [])


def previous_manifest(cfg: Config, manifest: dict) -> dict | None:
    """The manifest of the most recent earlier download of the same dataset and season."""
    current = cfg.raw_files_dir / manifest["file"]
    load_dir = next(p for p in current.parents if p.name.startswith("load_date="))
    relative = current.relative_to(load_dir)
    earlier = sorted(
        (p for p in load_dir.parent.glob("load_date=*") if p.is_dir() and p.name < load_dir.name),
        reverse=True,
    )
    for older in earlier:
        candidate = older / relative
        meta = candidate.with_name(candidate.name + ".manifest.json")
        if meta.is_file():
            return json.loads(meta.read_text(encoding="utf-8"))
    return None


def check_downloads(cfg: Config, manifests: list[dict]) -> list[Finding]:
    """Run every check on the manifests returned in extract()['downloaded']."""
    registry: dict[str, dict] = cfg.get("source.datasets")
    schema = cfg.get("database.schemas.raw")
    sql_raw = cfg.path("paths.sql") / "raw"
    min_ratio = float(cfg.get("quality.min_rows_vs_previous_ratio", DEFAULT_MIN_ROWS_RATIO))
    findings: list[Finding] = []

    for m in manifests:
        dataset, season = m["dataset"], m["season"]
        table = registry[dataset]["table"]

        expected = ddl_columns(sql_raw, schema, table)
        if expected is None:
            findings.append(Finding("error", dataset, season, "schema", f"no DDL for {schema}.{table} in {sql_raw}"))
        else:
            new_cols = [c for c in file_header(cfg.raw_files_dir / m["file"]) if c not in expected]
            if new_cols:
                findings.append(Finding(
                    "error", dataset, season, "schema",
                    f"columns not in {schema}.{table}: {new_cols}. Update sql/raw and docs/data_profile.md.",
                ))

        prev = previous_manifest(cfg, m)
        if prev and prev["rows"] > 0:
            ratio = m["rows"] / prev["rows"]
            if ratio < min_ratio:
                findings.append(Finding(
                    "error", dataset, season, "row_count",
                    f"{m['rows']} rows vs {prev['rows']} in {prev['file']} ({ratio:.1%}, minimum {min_ratio:.0%})",
                ))

    return findings
