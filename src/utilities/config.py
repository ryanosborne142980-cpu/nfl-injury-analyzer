"""Load and validate environment config from config/<env>.yaml.

Non-secret settings live in YAML. Secrets (DB_USER, DB_PASSWORD) come only from
environment variables, and the loader refuses YAML files that contain secret-like keys.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"

FORBIDDEN_KEYS = {"password", "pwd", "secret", "token", "api_key", "apikey", "user", "username", "uid"}

REQUIRED_KEYS = [
    "env",
    "source.seasons.start",
    "source.datasets",
    "paths.raw_files",
    "paths.sql",
    "database.driver",
    "database.server",
    "database.name",
    "database.schemas.raw",
]


class ConfigError(Exception):
    """Raised when config is missing, invalid, or contains secrets."""


def _walk_keys(node: Any, prefix: str = ""):
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield str(key), path
            yield from _walk_keys(value, path)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item, prefix)


def _is_secret_key(key: str) -> bool:
    """True if the key, or any _/- separated part of it, names a secret (e.g. db_password)."""
    k = key.lower()
    return k in FORBIDDEN_KEYS or any(part in FORBIDDEN_KEYS for part in re.split(r"[_\-]", k))


def _odbc_quote(value: Any) -> str:
    """Brace-quote an ODBC connection-string value so ';' and '}' inside it are literal."""
    return "{" + str(value).replace("}", "}}") + "}"


def _dig(data: dict, dotted: str) -> Any:
    node: Any = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


@dataclass(frozen=True)
class Config:
    data: dict
    env: str
    repo_root: Path = REPO_ROOT

    def get(self, dotted: str, default: Any = None) -> Any:
        try:
            return _dig(self.data, dotted)
        except KeyError:
            return default

    def path(self, dotted: str) -> Path:
        """Resolve a path setting (relative to repo root) to an absolute path."""
        return (self.repo_root / _dig(self.data, dotted)).resolve()

    @property
    def raw_files_dir(self) -> Path:
        return self.path("paths.raw_files")

    def season_range(self, current_season: int) -> range:
        """Seasons to load. An end of null in the YAML means the latest available season."""
        start = int(self.get("source.seasons.start"))
        end = self.get("source.seasons.end")
        end = current_season if end is None else int(end)
        if end < start:
            raise ConfigError(f"source.seasons.end ({end}) is before start ({start})")
        return range(start, end + 1)

    def connection_string(self, database: str | None = None) -> str:
        """Build an ODBC connection string. Credentials are read from the environment.

        database overrides database.name (the bootstrap connects to master before the database exists).
        """
        db = self.data["database"]
        parts = [
            f"DRIVER={_odbc_quote(db['driver'])}",
            f"SERVER={db['server']},{db.get('port', 1433)}",
            f"DATABASE={database or db['name']}",
            f"Encrypt={'yes' if db.get('encrypt', True) else 'no'}",
            f"TrustServerCertificate={'yes' if db.get('trust_server_certificate', False) else 'no'}",
        ]
        if db.get("trusted_connection", False):
            parts.append("Trusted_Connection=yes")
        else:
            user, password = os.getenv("DB_USER"), os.getenv("DB_PASSWORD")
            if not user or not password:
                raise ConfigError(
                    "database.trusted_connection is false: set DB_USER and DB_PASSWORD environment variables"
                )
            parts += [f"UID={_odbc_quote(user)}", f"PWD={_odbc_quote(password)}"]
        return ";".join(parts)


def load_config(env: str | None = None, config_dir: Path | None = None) -> Config:
    """Load config/<env>.yaml. The env defaults to the NFL_ENV variable, then 'dev'."""
    env = env or os.getenv("NFL_ENV", "dev")
    path = (config_dir or CONFIG_DIR) / f"{env}.yaml"
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name} must contain a YAML mapping")

    leaked = [p for key, p in _walk_keys(data) if _is_secret_key(key)]
    if leaked:
        raise ConfigError(
            f"Secret-like keys found in {path.name}: {', '.join(leaked)}. Use environment variables instead."
        )

    missing = []
    for dotted in REQUIRED_KEYS:
        try:
            _dig(data, dotted)
        except KeyError:
            missing.append(dotted)
    if missing:
        raise ConfigError(f"Missing required config keys in {path.name}: {', '.join(missing)}")

    if data["env"] != env:
        raise ConfigError(f"{path.name} declares env '{data['env']}' but '{env}' was requested")

    return Config(data=data, env=env)
