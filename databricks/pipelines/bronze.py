"""Bronze: land nflverse files raw and append-only with Auto Loader.

Every value stays a string (no type inference), so bronze keeps what the file said. Each row
records which file it came from, which load_date folder it was downloaded under, and when it was
loaded, so it can be traced and replayed. Auto Loader tracks processed files, so re-running the
pipeline doesn't load a file twice.

The injuries files really do drift: 2025 and later add season_type and drop date_modified. In the
default addNewColumns mode the stream stops once on a new column, adds it, and continues on
restart. Rows from files without a column carry NULL for it.
"""
import dlt
from pyspark.sql import functions as F

# Same names as source.datasets in config/dev.yaml; a test keeps the two in sync.
DATASETS = ["injuries", "rosters_weekly", "players", "games"]

COMMENTS = {
    "injuries": "Weekly injury reports, raw. One row per player, team and week.",
    "rosters_weekly": "Weekly rosters, raw. 2010 to 2015 files hold duplicate keys; silver does not collapse them yet.",
    "players": "Player master file, raw. A re-download arrives again; silver picks the latest.",
    "games": "Schedules and results, raw. A re-download arrives again; silver picks the latest.",
}


def _auto_loader(dataset: str):
    return (
        spark.readStream.format("cloudFiles")  # noqa: F821 (provided by the pipeline runtime)
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "false")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        # load_date= and season= folders must not become columns: season is also a file column.
        .option("cloudFiles.partitionColumns", "")
        .option("header", "true")
        .load(f"{spark.conf.get('nfl.volume')}/{dataset}/")  # noqa: F821
        .withColumn("source_file", F.col("_metadata.file_path"))
        .withColumn("source_modified_at", F.col("_metadata.file_modification_time"))
        .withColumn("load_date", F.regexp_extract("source_file", r"load_date=(\d{4}-\d{2}-\d{2})", 1))
        .withColumn("loaded_at", F.current_timestamp())
    )


def _bronze(dataset: str):
    @dlt.table(name=f"bronze_{dataset}", comment=COMMENTS[dataset])
    def _table():
        return _auto_loader(dataset)

    return _table


for _dataset in DATASETS:
    _bronze(_dataset)
