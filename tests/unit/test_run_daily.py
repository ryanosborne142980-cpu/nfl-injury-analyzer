from datetime import date

import pytest

from src.ingestion import load_raw, run_daily
from tests.unit.helpers import make_cfg, write_source

TODAY = date(2011, 11, 12)  # current season 2011


class FakeConn:
    closed = False

    def close(self):
        self.closed = True


@pytest.fixture
def loads(monkeypatch):
    calls = []
    monkeypatch.setattr(load_raw, "load_all", lambda conn, cfg, datasets, seasons: calls.append((datasets, seasons)) or [])
    return calls


def test_skip_load_extracts_only_current_season(tmp_path, loads):
    write_source(tmp_path, seasons=(2010, 2011))
    cfg = make_cfg(tmp_path, end=None)

    assert run_daily.run(cfg, skip_load=True, today=TODAY) == 0
    assert not (cfg.raw_files_dir / "injuries" / "load_date=2011-11-12" / "season=2010").exists()
    assert (cfg.raw_files_dir / "injuries" / "load_date=2011-11-12" / "season=2011").is_dir()
    assert loads == []


def test_loads_downloaded_datasets_for_current_season(tmp_path, loads):
    write_source(tmp_path, seasons=(2011,))
    cfg = make_cfg(tmp_path, end=None)
    conn = FakeConn()

    assert run_daily.run(cfg, today=TODAY, connect_fn=lambda c: conn) == 0
    assert loads == [(["games", "injuries"], [2011])]
    assert conn.closed


def test_quality_error_blocks_load(tmp_path, loads):
    write_source(tmp_path, seasons=(2011,))
    (tmp_path / "source" / "injuries" / "injuries_2011.csv").write_text("season,team,week,surprise\n2011,ARI,1,x\n")
    cfg = make_cfg(tmp_path, end=None)

    def no_connect(c):
        raise AssertionError("must not connect when checks fail")

    assert run_daily.run(cfg, today=TODAY, connect_fn=no_connect) == 1
    assert loads == []


def test_current_season_not_published_is_not_a_failure(tmp_path, loads):
    write_source(tmp_path, seasons=(2010,))  # no 2011 file yet
    cfg = make_cfg(tmp_path, end=None)

    assert run_daily.run(cfg, today=TODAY, connect_fn=lambda c: FakeConn()) == 0
    assert loads == [(["games"], [2011])]


def test_past_season_missing_is_a_failure(tmp_path, loads):
    write_source(tmp_path, seasons=(2011,))
    cfg = make_cfg(tmp_path, end=None)

    assert run_daily.run(cfg, seasons=[2010], today=TODAY, connect_fn=lambda c: FakeConn()) == 1
    assert loads == []
