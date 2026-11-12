import pytest

from src.ingestion import load_raw as lr
from tests.unit.helpers import make_cfg

META = ["_batch_id", "_source_file", "_loaded_at"]


class FakeCursor:
    def __init__(self, columns):
        self.columns = columns
        self.executed = []
        self.many = []
        self.fast_executemany = False
        self._rows = []

    def execute(self, sql, *params):
        self.executed.append((sql, params))
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            self._rows = [(c,) for c in self.columns]
        elif "OUTPUT INSERTED.batch_id" in sql:
            self._rows = [(7,)]
        return self

    def executemany(self, sql, rows):
        self.many.append((sql, list(rows)))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0]


class FakeConn:
    def __init__(self, columns):
        self.cur = FakeCursor(columns)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def put_file(cfg, dataset, load_date, name, text, season=None):
    parts = [cfg.raw_files_dir, dataset, f"load_date={load_date}"]
    if season is not None:
        parts.append(f"season={season}")
    path = parts[0].joinpath(*[str(p) for p in parts[1:]]) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_discover_files_prefers_latest_load_date(tmp_path):
    cfg = make_cfg(tmp_path)
    put_file(cfg, "injuries", "2026-11-01", "injuries_2010.csv", "season\n2010\n", season=2010)
    new = put_file(cfg, "injuries", "2026-11-12", "injuries_2010.csv", "season\n2010\n", season=2010)
    other = put_file(cfg, "injuries", "2026-11-01", "injuries_2011.csv", "season\n2011\n", season=2011)
    found = lr.discover_files(cfg.raw_files_dir, "injuries")
    assert found == {2010: new, 2011: other}


def test_discover_files_single_file_dataset(tmp_path):
    cfg = make_cfg(tmp_path)
    path = put_file(cfg, "games", "2026-11-12", "games.csv", "game_id\nx\n")
    assert lr.discover_files(cfg.raw_files_dir, "games") == {None: path}
    assert lr.discover_files(cfg.raw_files_dir, "players") == {}


def test_read_rows_orders_columns_and_nulls_empties(tmp_path):
    path = tmp_path / "f.csv"
    path.write_text("week,season,team\n1,2010,\n2,2010,ARI\n", encoding="utf-8")
    rows = list(lr.read_rows(path, ["season", "team", "week", "extra_in_table"]))
    assert rows == [("2010", None, "1", None), ("2010", "ARI", "2", None)]


def test_read_rows_flags_schema_drift(tmp_path):
    path = tmp_path / "f.csv"
    path.write_text("season,brand_new_col\n2010,x\n", encoding="utf-8")
    with pytest.raises(lr.SchemaDriftError, match="brand_new_col"):
        list(lr.read_rows(path, ["season"]))


def test_load_file_success_replaces_season_and_logs_batch(tmp_path):
    cfg = make_cfg(tmp_path)
    path = put_file(
        cfg, "injuries", "2026-11-12", "injuries_2010.csv", "season,team,week\n2010,ARI,1\n2010,,2\n", season=2010
    )
    conn = FakeConn(META + ["season", "team", "week"])
    spec = cfg.get("source.datasets")["injuries"]

    loaded = lr.load_file(conn, cfg, "injuries", spec, path, 2010)

    assert loaded == 2
    src = "injuries/load_date=2026-11-12/season=2010/injuries_2010.csv"
    assert conn.cur.many[0][1] == [(7, src, "2010", "ARI", "1"), (7, src, "2010", None, "2")]
    assert "INSERT INTO raw.injuries ([_batch_id], [_source_file], [season], [team], [week])" in conn.cur.many[0][0]
    sqls = [s for s, _ in conn.cur.executed]
    assert any(s.startswith("DELETE FROM raw.injuries WHERE [season] = ?") for s in sqls)
    assert ("2010",) in [p for _, p in conn.cur.executed]
    last_sql, last_params = conn.cur.executed[-1]
    assert "status = 'succeeded'" in last_sql and last_params == (2, 7)
    assert conn.rollbacks == 0 and conn.commits >= 3


def test_load_file_single_file_dataset_deletes_whole_table(tmp_path):
    cfg = make_cfg(tmp_path)
    path = put_file(cfg, "games", "2026-11-12", "games.csv", "game_id,season\na,2010\n")
    conn = FakeConn(META + ["game_id", "season"])
    lr.load_file(conn, cfg, "games", cfg.get("source.datasets")["games"], path, None)
    assert any(s == "DELETE FROM raw.games" for s, _ in conn.cur.executed)


def test_load_file_failure_rolls_back_and_marks_batch_failed(tmp_path):
    cfg = make_cfg(tmp_path)
    path = put_file(cfg, "injuries", "2026-11-12", "injuries_2010.csv", "season,surprise\n2010,x\n", season=2010)
    conn = FakeConn(META + ["season"])

    with pytest.raises(lr.SchemaDriftError):
        lr.load_file(conn, cfg, "injuries", cfg.get("source.datasets")["injuries"], path, 2010)

    assert conn.rollbacks == 1
    last_sql, last_params = conn.cur.executed[-1]
    assert "status = 'failed'" in last_sql and last_params[1] == 7


def test_load_file_requires_table(tmp_path):
    cfg = make_cfg(tmp_path)
    path = put_file(cfg, "games", "2026-11-12", "games.csv", "game_id\na\n")
    with pytest.raises(lr.LoadError, match="--apply-ddl"):
        lr.load_file(FakeConn([]), cfg, "games", cfg.get("source.datasets")["games"], path, None)


def test_identifier_guard():
    assert lr._ident("raw") == "raw"
    with pytest.raises(ValueError):
        lr._ident("raw; DROP TABLE x")
    assert lr._q("a]b") == "[a]]b]"


def test_load_all_requires_extracted_files(tmp_path):
    cfg = make_cfg(tmp_path)
    with pytest.raises(lr.LoadError, match="Run the extract first"):
        lr.load_all(FakeConn(META), cfg, datasets=["games"])
