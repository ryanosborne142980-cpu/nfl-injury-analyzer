"""Land the downloaded nflverse files in the Databricks volume, unchanged.

Run from the repo root after `python -m src.ingestion.extract`:
    python databricks/land_raw.py
    python databricks/land_raw.py --datasets injuries --profile nfl

The folder layout (raw_files/<dataset>/load_date=<date>/...) is kept, so bronze can read the
load_date from the path. Files are copied as they are; Auto Loader skips ones it already read.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_files"
VOLUME = "dbfs:/Volumes/workspace/nfl_injury/raw"
DATASETS = ["injuries", "rosters_weekly", "players", "games"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datasets", nargs="+", choices=DATASETS, default=DATASETS)
    parser.add_argument("--profile", default="nfl", help="Databricks CLI profile")
    args = parser.parse_args()

    cli = shutil.which("databricks")
    if not cli:
        print("databricks CLI not on PATH", file=sys.stderr)
        return 1

    failed = False
    for dataset in args.datasets:
        src = RAW / dataset
        if not src.is_dir():
            print(f"{dataset}: nothing in {src}; run the extract first", file=sys.stderr)
            failed = True
            continue
        result = subprocess.run(
            [cli, "fs", "cp", str(src), f"{VOLUME}/{dataset}", "--recursive", "--overwrite", "-p", args.profile]
        )
        if result.returncode:
            print(f"{dataset}: upload failed", file=sys.stderr)
            failed = True
        else:
            print(f"{dataset}: landed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
