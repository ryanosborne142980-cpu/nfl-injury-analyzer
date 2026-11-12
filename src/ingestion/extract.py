"""Download nflverse files into raw_files/, with a manifest (url, bytes, sha256, rows) beside each file.

Layout: raw_files/<dataset>/load_date=<YYYY-MM-DD>/[season=<YYYY>/]<file>.csv

Usage:
    python -m src.ingestion.extract
    python -m src.ingestion.extract --datasets injuries --seasons 2024 2025
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.utilities.config import Config, load_config

log = logging.getLogger("extract")
USER_AGENT = "nfl-injury-analyzer/0.1"


class ExtractError(Exception):
    """A download or validation failure."""


class SourceNotFound(ExtractError):
    """The source file does not exist (HTTP 404)."""


def latest_season(today: date | None = None) -> int:
    """Latest NFL season likely to have published data: the new season counts from September."""
    today = today or date.today()
    return today.year if today.month >= 9 else today.year - 1


def build_url(cfg: Config, spec: dict, season: int | None) -> str:
    base = str(cfg.get("source.base_url")).rstrip("/")
    return f"{base}/{spec['path'].format(season=season)}"


def dest_path(cfg: Config, dataset: str, url: str, load_date: str, season: int | None) -> Path:
    parts = [cfg.raw_files_dir, dataset, f"load_date={load_date}"]
    if season is not None:
        parts.append(f"season={season}")
    return Path(*[str(p) for p in parts]) / Path(url).name


def download(url: str, dest: Path, timeout: int, retries: int, backoff: float) -> tuple[int, str]:
    """Download atomically (via a .part file). Returns (bytes, sha256). 404s are not retried."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            sha, size = hashlib.sha256(), 0
            with urllib.request.urlopen(req, timeout=timeout) as resp, part.open("wb") as out:
                while chunk := resp.read(1 << 20):
                    out.write(chunk)
                    sha.update(chunk)
                    size += len(chunk)
            os.replace(part, dest)
            return size, sha.hexdigest()
        except urllib.error.HTTPError as exc:
            part.unlink(missing_ok=True)
            if exc.code == 404:
                raise SourceNotFound(url) from exc
            last = exc
        except urllib.error.URLError as exc:
            part.unlink(missing_ok=True)
            if isinstance(exc.reason, FileNotFoundError):
                raise SourceNotFound(url) from exc
            last = exc
        except (TimeoutError, ConnectionError) as exc:
            part.unlink(missing_ok=True)
            last = exc
        if attempt < retries:
            log.warning("attempt %d/%d failed for %s: %s", attempt, retries, url, last)
            time.sleep(backoff * attempt)
    raise ExtractError(f"download failed after {retries} attempts: {url}: {last}")


def validate_csv(path: Path) -> int:
    """Confirm the file is a CSV with a header and at least one data row. Returns the data row count."""
    with path.open("rb") as fh:
        head = fh.read(512).lstrip().lower()
    if head.startswith((b"<!doctype", b"<html")):
        raise ExtractError(f"{path.name} is HTML, not CSV")
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if not header or len(header) < 2:
            raise ExtractError(f"{path.name} has no usable header")
        rows = sum(1 for _ in reader)
    if rows == 0:
        raise ExtractError(f"{path.name} has no data rows")
    return rows


def extract(
    cfg: Config,
    datasets: list[str] | None = None,
    seasons: list[int] | None = None,
    load_date: str | None = None,
    today: date | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Download the configured datasets. Returns manifests under 'downloaded', plus 'skipped' and 'failed'."""
    load_date = load_date or (today or date.today()).isoformat()
    registry: dict[str, dict] = cfg.get("source.datasets")
    names = datasets or list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise ExtractError(f"unknown datasets: {unknown}. Configured: {list(registry)}")

    open_ended = cfg.get("source.seasons.end") is None
    all_seasons = list(cfg.season_range(latest_season(today)))
    season_list = sorted(set(seasons)) if seasons else all_seasons
    last_open_season = all_seasons[-1] if (open_ended and not seasons) else None

    http = cfg.get("source.http", {}) or {}
    timeout = int(http.get("timeout_seconds", 120))
    retries = int(http.get("retries", 3))
    backoff = float(http.get("backoff_seconds", 2))

    result: dict[str, list[dict[str, Any]]] = {"downloaded": [], "skipped": [], "failed": []}

    for name in names:
        spec = registry[name]
        targets: list[int | None] = season_list if spec.get("per_season") else [None]
        for season in targets:
            url = build_url(cfg, spec, season)
            dest = dest_path(cfg, name, url, load_date, season)
            label = {"dataset": name, "season": season, "url": url}
            try:
                size, sha = download(url, dest, timeout, retries, backoff)
                rows = validate_csv(dest)
            except SourceNotFound:
                if season is not None and season == last_open_season:
                    log.warning("%s %s not published yet, skipping", name, season)
                    result["skipped"].append({**label, "reason": "not published yet"})
                else:
                    log.error("%s %s not found: %s", name, season, url)
                    result["failed"].append({**label, "error": "not found"})
                continue
            except ExtractError as exc:
                dest.unlink(missing_ok=True)
                log.error("%s %s failed: %s", name, season, exc)
                result["failed"].append({**label, "error": str(exc)})
                continue

            manifest = {
                **label,
                "file": str(dest.relative_to(cfg.raw_files_dir).as_posix()),
                "bytes": size,
                "sha256": sha,
                "rows": rows,
                "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            dest.with_name(dest.name + ".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            log.info("%s %s: %d rows, %d bytes", name, season or "all", rows, size)
            result["downloaded"].append(manifest)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download nflverse files into raw_files/")
    parser.add_argument("--env", default=None, help="config environment (default: NFL_ENV or dev)")
    parser.add_argument("--datasets", nargs="+", help="subset of configured datasets")
    parser.add_argument("--seasons", nargs="+", type=int, help="explicit seasons for per-season datasets")
    parser.add_argument("--load-date", help="partition date, default today (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    cfg = load_config(args.env)
    logging.basicConfig(level=cfg.get("logging.level", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    result = extract(cfg, args.datasets, args.seasons, args.load_date)

    print(f"downloaded={len(result['downloaded'])} skipped={len(result['skipped'])} failed={len(result['failed'])}")
    for item in result["failed"]:
        print(f"FAILED {item['dataset']} {item['season']}: {item['error']}")
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
