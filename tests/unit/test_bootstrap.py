from dataclasses import replace

import pytest

from src.utilities.bootstrap import BootstrapError, apply_migrations, ensure_database, tune_instance, verify
from tests.unit.helpers import make_cfg


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []

    def execute(self, sql, *params):
        self.conn.log.append((sql.strip(), params))
        text = sql.strip()
        if text.startswith("SELECT recovery_model_desc"):
            self.rows = [self.conn.db_row] if self.conn.db_row else []
        elif text.startswith("SELECT name, type_desc"):
            self.rows = [("nfl_test", "ROWS", 8), ("nfl_test_log", "LOG", 8)]
        elif text.startswith("SELECT file_path"):
            self.rows = list(self.conn.recorded.items())
        elif text.startswith("SELECT name FROM sys.schemas"):
            self.rows = [(s,) for s in self.conn.schemas]
        elif "FROM sys.tables" in text:
            self.rows = [(t,) for t in self.conn.tables]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, db_row=None, recorded=None, schemas=(), tables=()):
        self.log, self.db_row = [], db_row
        self.recorded, self.schemas, self.tables = recorded or {}, schemas, tables

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass

    def statements(self):
        return [s for s, _ in self.log]


def cfg_with(tmp_path, **bootstrap):
    cfg = make_cfg(tmp_path)
    cfg.data["database"]["bootstrap"] = bootstrap
    cfg.data["database"]["schemas"] = {"raw": "raw", "dim": "dim"}
    cfg.data["paths"]["sql"] = "sql"
    return replace(cfg, repo_root=tmp_path)


def write_sql(tmp_path, files):
    for rel, text in files.items():
        p = tmp_path / "sql" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def test_new_database_is_created_sized_and_configured(tmp_path):
    cfg = cfg_with(tmp_path, collation="Latin1_General_100_CI_AS_SC_UTF8", data_file_mb=1024, log_file_mb=512,
                   file_growth_mb=256)
    conn = FakeConn(db_row=None)
    assert ensure_database(conn, cfg) is True
    stmts = conn.statements()
    assert "CREATE DATABASE [nfl_test] COLLATE Latin1_General_100_CI_AS_SC_UTF8" in stmts
    assert any("MODIFY FILE (NAME = N'nfl_test', SIZE = 1024MB, FILEGROWTH = 256MB)" in s for s in stmts)
    assert any("MODIFY FILE (NAME = N'nfl_test_log', SIZE = 512MB" in s for s in stmts)
    assert "ALTER DATABASE [nfl_test] SET RECOVERY SIMPLE" in stmts
    assert any("READ_COMMITTED_SNAPSHOT ON" in s for s in stmts)


def test_existing_database_with_matching_options_is_left_alone(tmp_path):
    conn = FakeConn(db_row=("SIMPLE", 1))
    assert ensure_database(conn, cfg_with(tmp_path)) is False
    assert not any(s.startswith(("CREATE DATABASE", "ALTER DATABASE")) for s in conn.statements())


def test_unsafe_database_name_is_rejected(tmp_path):
    cfg = cfg_with(tmp_path)
    cfg.data["database"]["name"] = "x]; DROP DATABASE y;--"
    with pytest.raises(BootstrapError):
        ensure_database(FakeConn(), cfg)


def test_tune_instance_only_sets_configured_values(tmp_path):
    cfg = cfg_with(tmp_path, instance={"max_server_memory_mb": 6144, "max_degree_of_parallelism": None})
    conn = FakeConn()
    assert tune_instance(conn, cfg) == ["max server memory (MB)"]
    assert "EXEC sp_configure N'max server memory (MB)', 6144" in conn.statements()


def test_migrations_apply_new_files_and_skip_recorded_ones(tmp_path):
    cfg = cfg_with(tmp_path)
    write_sql(tmp_path, {"raw/000_a.sql": "SELECT 1", "raw/010_b.sql": "SELECT 2", "dim/010_c.sql": "SELECT 3"})
    first = FakeConn()
    assert apply_migrations(first, cfg) == ["raw/000_a.sql", "raw/010_b.sql", "dim/010_c.sql"]

    from src.utilities.bootstrap import _sha256

    recorded = {f"raw/{n}": _sha256(tmp_path / "sql" / "raw" / n) for n in ("000_a.sql", "010_b.sql")}
    second = FakeConn(recorded=recorded)
    assert apply_migrations(second, cfg) == ["dim/010_c.sql"]


def test_changed_file_stops_the_run_unless_accepted(tmp_path):
    cfg = cfg_with(tmp_path)
    write_sql(tmp_path, {"raw/000_a.sql": "SELECT 1"})
    conn = FakeConn(recorded={"raw/000_a.sql": "0" * 64})
    with pytest.raises(BootstrapError, match="raw/000_a.sql"):
        apply_migrations(conn, cfg)
    assert apply_migrations(FakeConn(recorded={"raw/000_a.sql": "0" * 64}), cfg, accept_changes=True) == [
        "raw/000_a.sql"
    ]


def test_verify_reports_missing_objects(tmp_path):
    cfg = cfg_with(tmp_path)
    ok = FakeConn(schemas=["raw", "dim"], tables=["raw.load_batch", "meta.schema_version", "raw.injuries", "raw.games"])
    verify(ok, cfg)
    bad = FakeConn(schemas=["raw"], tables=["raw.load_batch"])
    with pytest.raises(BootstrapError) as err:
        verify(bad, cfg)
    assert "schema dim" in str(err.value) and "table raw.injuries" in str(err.value)
