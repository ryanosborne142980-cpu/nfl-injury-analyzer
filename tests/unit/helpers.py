"""Shared test helpers: build a throwaway config that points at temp folders."""
from __future__ import annotations

from pathlib import Path

import yaml

from src.utilities.config import Config, load_config


def make_cfg(tmp_path: Path, end: int | None = None, start: int = 2010) -> Config:
    data = {
        "env": "test",
        "project": {"name": "t"},
        "source": {
            "base_url": (tmp_path / "source").as_uri(),
            "seasons": {"start": start, "end": end},
            "http": {"timeout_seconds": 5, "retries": 2, "backoff_seconds": 0},
            "datasets": {
                "injuries": {"path": "injuries/injuries_{season}.csv", "per_season": True, "table": "injuries"},
                "games": {"path": "schedules/games.csv", "per_season": False, "table": "games"},
            },
        },
        "paths": {"raw_files": str(tmp_path / "raw"), "sql": "sql"},
        "database": {
            "driver": "ODBC Driver 18 for SQL Server",
            "server": "localhost",
            "name": "nfl_test",
            "trusted_connection": True,
            "schemas": {"raw": "raw"},
        },
    }
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "test.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_config("test", config_dir=cfg_dir)


def write_source(tmp_path: Path, seasons=(2010, 2011), games: bool = True) -> None:
    src = tmp_path / "source"
    for s in seasons:
        f = src / "injuries" / f"injuries_{s}.csv"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"season,team,week\n{s},ARI,1\n{s},ATL,1\n", encoding="utf-8")
    if games:
        g = src / "schedules" / "games.csv"
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_text("game_id,season\n2010_01_A_B,2010\n", encoding="utf-8")
