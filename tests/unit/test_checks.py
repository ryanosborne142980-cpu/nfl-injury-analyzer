from pathlib import Path

from src.ingestion import checks
from src.ingestion.extract import extract
from tests.unit.helpers import make_cfg, write_source

SQL_RAW = Path(__file__).resolve().parents[2] / "sql" / "raw"


def test_ddl_columns_reads_raw_table():
    cols = checks.ddl_columns(SQL_RAW, "raw", "injuries")
    assert cols[:2] == ["season", "season_type"]
    assert "date_modified" in cols and not any(c.startswith("_") for c in cols)


def test_ddl_columns_missing_table():
    assert checks.ddl_columns(SQL_RAW, "raw", "nope") is None


def test_first_download_passes(tmp_path):
    write_source(tmp_path, seasons=(2010,))
    cfg = make_cfg(tmp_path, end=2010)
    result = extract(cfg, load_date="2026-11-12")
    assert checks.check_downloads(cfg, result["downloaded"]) == []


def test_new_column_is_a_schema_error(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    (tmp_path / "source" / "injuries" / "injuries_2010.csv").write_text("season,team,week,new_col\n2010,ARI,1,x\n")
    cfg = make_cfg(tmp_path, end=2010)
    result = extract(cfg, datasets=["injuries"], load_date="2026-11-12")

    findings = checks.check_downloads(cfg, result["downloaded"])
    assert [(f.level, f.check) for f in findings] == [("error", "schema")]
    assert "new_col" in findings[0].message


def test_row_drop_vs_previous_download_is_an_error(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    cfg = make_cfg(tmp_path, end=2010)
    extract(cfg, datasets=["injuries"], load_date="2026-11-11")

    (tmp_path / "source" / "injuries" / "injuries_2010.csv").write_text("season,team,week\n2010,ARI,1\n")
    result = extract(cfg, datasets=["injuries"], load_date="2026-11-12")

    findings = checks.check_downloads(cfg, result["downloaded"])
    assert [(f.level, f.check) for f in findings] == [("error", "row_count")]
    assert "1 rows vs 2" in findings[0].message


def test_same_or_more_rows_passes(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    cfg = make_cfg(tmp_path, end=2010)
    extract(cfg, datasets=["injuries"], load_date="2026-11-10")
    write_source(tmp_path, seasons=(2010,), games=False)
    extract(cfg, datasets=["injuries"], load_date="2026-11-11")
    (tmp_path / "source" / "injuries" / "injuries_2010.csv").write_text(
        "season,team,week\n2010,ARI,1\n2010,ATL,1\n2010,BAL,1\n"
    )
    result = extract(cfg, datasets=["injuries"], load_date="2026-11-12")
    assert checks.check_downloads(cfg, result["downloaded"]) == []


def test_previous_manifest_picks_most_recent_earlier_download(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    cfg = make_cfg(tmp_path, end=2010)
    extract(cfg, datasets=["injuries"], load_date="2026-11-10")
    extract(cfg, datasets=["injuries"], load_date="2026-11-11")
    result = extract(cfg, datasets=["injuries"], load_date="2026-11-12")

    prev = checks.previous_manifest(cfg, result["downloaded"][0])
    assert prev["file"].startswith("injuries/load_date=2026-11-11/")
