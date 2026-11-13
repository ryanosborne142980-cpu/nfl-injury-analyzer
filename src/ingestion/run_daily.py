"""Daily ingestion: extract the current season, check the files, then load them into SQL Server.

Meant to run once a day from Windows Task Scheduler (see scripts/register_daily_task.ps1), after nflverse's
07:00 UTC refresh. Single-file datasets (players, games) are always re-downloaded. Nothing is loaded if the
extract fails or a quality check fails while quality.fail_on_error is true. The exit code is 0 on success
and 1 on failure, so Task Scheduler's "Last Run Result" shows failed runs. Each run also logs to logs/.

Usage:
    python -m src.ingestion.run_daily
    python -m src.ingestion.run_daily --skip-load          # extract and check only, no database
    python -m src.ingestion.run_daily --seasons 2025 2026  # override the current season
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from src.ingestion.checks import check_downloads
from src.ingestion.extract import extract, latest_season
from src.utilities.config import Config, load_config

log = logging.getLogger("run_daily")


def run(cfg: Config, seasons: list[int] | None = None, skip_load: bool = False, today: date | None = None,
        connect_fn=None) -> int:
    """Run one daily cycle. Returns the process exit code."""
    current = latest_season(today)
    seasons = sorted(set(seasons)) if seasons else [current]
    log.info("daily run: seasons %s", seasons)

    result = extract(cfg, seasons=seasons, today=today)
    failed = []
    for item in result["failed"]:
        # Early in September the new season's files may not be published yet. That is expected, not a failure.
        if item["season"] == current and item["error"] == "not found":
            log.warning("%s %s not published yet, skipping", item["dataset"], current)
        else:
            failed.append(item)
    if failed:
        for item in failed:
            log.error("extract failed: %s %s: %s", item["dataset"], item["season"], item["error"])
        return 1

    findings = check_downloads(cfg, result["downloaded"])
    for f in findings:
        (log.error if f.level == "error" else log.warning)(str(f))
    errors = [f for f in findings if f.level == "error"]
    if errors and cfg.get("quality.fail_on_error", True):
        log.error("%d quality check(s) failed, nothing loaded", len(errors))
        return 1

    if skip_load:
        log.info("checks passed, --skip-load set, not loading")
        return 0

    from src.ingestion.load_raw import load_all

    if connect_fn is None:
        from src.utilities.db import connect as connect_fn
    datasets = sorted({m["dataset"] for m in result["downloaded"]})
    if not datasets:
        log.warning("nothing downloaded, nothing to load")
        return 0
    conn = connect_fn(cfg)
    try:
        summary = load_all(conn, cfg, datasets, seasons)
    finally:
        conn.close()
    log.info("loaded %d files, %d rows", len(summary), sum(s["rows"] for s in summary))
    return 0


def _setup_logging(cfg: Config) -> Path:
    log_dir = cfg.repo_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"daily_{datetime.now():%Y-%m-%d_%H%M%S}.log"
    logging.basicConfig(
        level=cfg.get("logging.level", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )
    return log_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily extract, check and load of the current NFL season")
    parser.add_argument("--env", default=None, help="config environment (default: NFL_ENV or dev)")
    parser.add_argument("--seasons", nargs="+", type=int, help="seasons to refresh (default: current season)")
    parser.add_argument("--skip-load", action="store_true", help="extract and check only")
    args = parser.parse_args(argv)

    cfg = load_config(args.env)
    log_file = _setup_logging(cfg)
    try:
        code = run(cfg, args.seasons, args.skip_load)
    except Exception:
        log.exception("daily run crashed")
        code = 1
    print(f"{'OK' if code == 0 else 'FAILED'}: log at {log_file}")
    return code


if __name__ == "__main__":
    sys.exit(main())
