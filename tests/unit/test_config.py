import pytest
import yaml

from src.utilities.config import ConfigError, load_config

VALID = {
    "env": "test",
    "source": {"seasons": {"start": 2010, "end": None}, "datasets": ["players"]},
    "paths": {"raw_files": "raw_files", "sql": "sql"},
    "database": {
        "driver": "ODBC Driver 18 for SQL Server",
        "server": "localhost",
        "port": 1433,
        "name": "nfl_test",
        "trusted_connection": True,
        "schemas": {"raw": "raw"},
    },
}


def write_cfg(tmp_path, data, name="test.yaml"):
    (tmp_path / name).write_text(yaml.safe_dump(data), encoding="utf-8")
    return tmp_path


def test_real_dev_config_loads():
    cfg = load_config("dev")
    assert cfg.env == "dev"
    assert cfg.get("database.schemas.fact") == "fact"
    assert cfg.raw_files_dir.is_absolute()


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config("nope", config_dir=tmp_path)


@pytest.mark.parametrize("key", ["password", "user", "token", "secret"])
def test_rejects_secret_keys(tmp_path, key):
    data = {**VALID, "database": {**VALID["database"], key: "x"}}
    with pytest.raises(ConfigError, match="Secret-like keys"):
        load_config("test", config_dir=write_cfg(tmp_path, data))


def test_rejects_missing_required_key(tmp_path):
    data = {**VALID, "paths": {"raw_files": "raw_files"}}
    with pytest.raises(ConfigError, match="paths.sql"):
        load_config("test", config_dir=write_cfg(tmp_path, data))


def test_rejects_env_mismatch(tmp_path):
    data = {**VALID, "env": "prod"}
    with pytest.raises(ConfigError, match="declares env"):
        load_config("test", config_dir=write_cfg(tmp_path, data))


def test_season_range_open_ended(tmp_path):
    cfg = load_config("test", config_dir=write_cfg(tmp_path, VALID))
    assert list(cfg.season_range(2012)) == [2010, 2011, 2012]


def test_season_range_end_before_start(tmp_path):
    data = {**VALID, "source": {**VALID["source"], "seasons": {"start": 2015, "end": 2012}}}
    cfg = load_config("test", config_dir=write_cfg(tmp_path, data))
    with pytest.raises(ConfigError, match="before start"):
        cfg.season_range(2020)


def test_connection_string_trusted(tmp_path):
    cfg = load_config("test", config_dir=write_cfg(tmp_path, VALID))
    conn = cfg.connection_string()
    assert "Trusted_Connection=yes" in conn
    assert "SERVER=localhost,1433" in conn
    assert "PWD" not in conn


def test_connection_string_sql_auth_requires_env(tmp_path, monkeypatch):
    data = {**VALID, "database": {**VALID["database"], "trusted_connection": False}}
    cfg = load_config("test", config_dir=write_cfg(tmp_path, data))
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    with pytest.raises(ConfigError, match="DB_USER"):
        cfg.connection_string()
    monkeypatch.setenv("DB_USER", "svc")
    monkeypatch.setenv("DB_PASSWORD", "pw")
    assert "UID=svc;PWD=pw" in cfg.connection_string()
