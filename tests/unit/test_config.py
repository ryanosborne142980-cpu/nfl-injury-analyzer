import pytest
import yaml

from src.utilities.config import ConfigError, load_config

VALID = {
    "env": "test",
    "source": {"seasons": {"start": 2010, "end": None}, "datasets": ["players"]},
    "paths": {"raw_files": "raw_files"},
}


def write_cfg(tmp_path, data, name="test.yaml"):
    (tmp_path / name).write_text(yaml.safe_dump(data), encoding="utf-8")
    return tmp_path


def test_real_dev_config_loads():
    cfg = load_config("dev")
    assert cfg.env == "dev"
    assert "injuries" in cfg.get("source.datasets")
    assert cfg.raw_files_dir.is_absolute()


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config("nope", config_dir=tmp_path)


@pytest.mark.parametrize("key", ["password", "user", "token", "secret"])
def test_rejects_secret_keys(tmp_path, key):
    data = {**VALID, "source": {**VALID["source"], "http": {key: "x"}}}
    with pytest.raises(ConfigError, match="Secret-like keys"):
        load_config("test", config_dir=write_cfg(tmp_path, data))


def test_rejects_missing_required_key(tmp_path):
    data = {**VALID, "paths": {}}
    with pytest.raises(ConfigError, match="paths.raw_files"):
        load_config("test", config_dir=write_cfg(tmp_path, data))


def test_rejects_env_mismatch(tmp_path):
    data = {**VALID, "env": "prod"}
    with pytest.raises(ConfigError, match="declares env"):
        load_config("test", config_dir=write_cfg(tmp_path, data))


def test_season_range_open_ended(tmp_path):
    cfg = load_config("test", config_dir=write_cfg(tmp_path, VALID))
    assert list(cfg.season_range(2012)) == [2010, 2011, 2012]


def test_season_range_end_before_start(tmp_path):
    data = {
        **VALID,
        "source": {**VALID["source"], "seasons": {"start": 2015, "end": 2012}},
    }
    cfg = load_config("test", config_dir=write_cfg(tmp_path, data))
    with pytest.raises(ConfigError, match="before start"):
        cfg.season_range(2020)
