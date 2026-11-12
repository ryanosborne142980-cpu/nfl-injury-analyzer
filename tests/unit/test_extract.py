import hashlib
import json
from datetime import date

import pytest

from src.ingestion import extract as ex
from tests.unit.helpers import make_cfg, write_source


@pytest.mark.parametrize(
    "today, expected",
    [(date(2026, 11, 12), 2026), (date(2026, 9, 1), 2026), (date(2026, 8, 31), 2025), (date(2026, 3, 1), 2025)],
)
def test_latest_season(today, expected):
    assert ex.latest_season(today) == expected


def test_extract_downloads_files_and_manifests(tmp_path):
    write_source(tmp_path, seasons=(2010, 2011))
    cfg = make_cfg(tmp_path, end=2011)
    result = ex.extract(cfg, load_date="2026-11-12")

    assert result["failed"] == [] and result["skipped"] == []
    assert len(result["downloaded"]) == 3  # 2 injury seasons + games

    inj = cfg.raw_files_dir / "injuries" / "load_date=2026-11-12" / "season=2010" / "injuries_2010.csv"
    games = cfg.raw_files_dir / "games" / "load_date=2026-11-12" / "games.csv"
    assert inj.is_file() and games.is_file()

    manifest = json.loads(inj.with_name(inj.name + ".manifest.json").read_text())
    assert manifest["rows"] == 2
    assert manifest["sha256"] == hashlib.sha256(inj.read_bytes()).hexdigest()
    assert manifest["file"] == "injuries/load_date=2026-11-12/season=2010/injuries_2010.csv"
    assert not list(cfg.raw_files_dir.rglob("*.part"))


def test_open_ended_last_season_not_published_is_skipped(tmp_path):
    write_source(tmp_path, seasons=(2024, 2025), games=False)
    cfg = make_cfg(tmp_path, end=None, start=2024)
    result = ex.extract(cfg, datasets=["injuries"], today=date(2026, 11, 12))

    assert [d["season"] for d in result["downloaded"]] == [2024, 2025]
    assert [s["season"] for s in result["skipped"]] == [2026]
    assert result["failed"] == []


def test_explicit_end_season_missing_is_a_failure(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    cfg = make_cfg(tmp_path, end=2011)
    result = ex.extract(cfg, datasets=["injuries"], load_date="2026-11-12")

    assert [d["season"] for d in result["downloaded"]] == [2010]
    assert [f["season"] for f in result["failed"]] == [2011]
    assert result["skipped"] == []


def test_season_override(tmp_path):
    write_source(tmp_path, seasons=(2010, 2011, 2012), games=False)
    cfg = make_cfg(tmp_path, end=2012)
    result = ex.extract(cfg, datasets=["injuries"], seasons=[2012], load_date="2026-11-12")
    assert [d["season"] for d in result["downloaded"]] == [2012]


def test_html_response_is_rejected_and_removed(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    (tmp_path / "source" / "injuries" / "injuries_2010.csv").write_text("<!DOCTYPE html><html>nope</html>")
    cfg = make_cfg(tmp_path, end=2010)
    result = ex.extract(cfg, datasets=["injuries"], load_date="2026-11-12")

    assert len(result["failed"]) == 1 and "HTML" in result["failed"][0]["error"]
    assert not list(cfg.raw_files_dir.rglob("*.csv"))


def test_header_only_file_is_rejected(tmp_path):
    write_source(tmp_path, seasons=(2010,), games=False)
    (tmp_path / "source" / "injuries" / "injuries_2010.csv").write_text("season,team,week\n")
    cfg = make_cfg(tmp_path, end=2010)
    result = ex.extract(cfg, datasets=["injuries"], load_date="2026-11-12")
    assert "no data rows" in result["failed"][0]["error"]


def test_unknown_dataset(tmp_path):
    cfg = make_cfg(tmp_path, end=2010)
    with pytest.raises(ex.ExtractError, match="unknown datasets"):
        ex.extract(cfg, datasets=["nope"])


def test_download_404_is_not_retried(tmp_path):
    with pytest.raises(ex.SourceNotFound):
        ex.download((tmp_path / "missing.csv").as_uri(), tmp_path / "out.csv", timeout=1, retries=5, backoff=0)
