"""Keep the raw DDL in sync with real nflverse file headers (tests/fixtures hold header + 2 rows each)."""
import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SQL_RAW = ROOT / "sql" / "raw"
FIXTURES = ROOT / "tests" / "fixtures"

CASES = {
    "010_raw_injuries.sql": ["injuries_2023.csv", "injuries_2026.csv"],  # 2025+ files swap date_modified for season_type
    "020_raw_rosters_weekly.sql": ["rosters_weekly_2023.csv"],
    "030_raw_players.sql": ["players.csv"],
    "040_raw_games.sql": ["games.csv"],
}


def ddl_columns(path: Path) -> list[str]:
    block = path.read_text(encoding="utf-8").split("CREATE TABLE", 1)[1].split("\n    );", 1)[0]
    return re.findall(r"^\s+\[([^\]]+)\]", block, flags=re.M)


def fixture_header(name: str) -> list[str]:
    with (FIXTURES / name).open(newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh))


@pytest.mark.parametrize("ddl_file, fixtures", CASES.items())
def test_ddl_columns_match_source_headers(ddl_file, fixtures):
    all_cols = ddl_columns(SQL_RAW / ddl_file)
    assert all_cols[:3] == ["_batch_id", "_source_file", "_loaded_at"]
    source_cols = [c for c in all_cols if not c.startswith("_")]
    assert len(source_cols) == len(set(source_cols)), "duplicate column in DDL"

    expected = set()
    for name in fixtures:
        expected |= set(fixture_header(name))
    assert set(source_cols) == expected


def test_every_raw_table_has_a_case():
    ddl_tables = {p.name for p in SQL_RAW.glob("*_raw_*.sql") if "load_batch" not in p.name}
    assert ddl_tables == set(CASES)


def test_load_batch_has_columns_the_loader_uses():
    block = (SQL_RAW / "005_raw_load_batch.sql").read_text().split("CREATE TABLE", 1)[1].split("\n    );", 1)[0]
    cols = set(re.findall(r"^\s+(\w+)\s+\w+", block, flags=re.M))
    needed = {"batch_id", "dataset", "source_file", "file_sha256", "rows_in_file", "rows_loaded", "status",
              "finished_at", "error"}
    assert needed <= cols
