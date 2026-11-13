"""Silver: typed, de-duplicated tables built from bronze.

Bronze keeps every version of a row, so each table here picks the latest landed one. Rules come
from docs/data_profile.md; the finding number is noted next to each. Two rules are NOT applied
yet because they are data-model decisions that belong to the project owner (see
docs/decisions/0001-databricks-lakehouse-layer.md): collapsing duplicate weekly-roster keys, and
mapping roof and surface values to a controlled vocabulary.
"""
import dlt
from pyspark.sql import Window
from pyspark.sql import functions as F

# Finding 3: 2010 to 2015 rosters use these codes; games and injuries use the values.
# Relocations (OAK to LV, SD to LAC, STL to LA) are left alone: dim_team handles them as SCD2.
TEAM_CODE_MAP = {"ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU", "SL": "STL"}


def _latest(df, keys, order=("load_date", "source_modified_at")):
    window = Window.partitionBy(*keys).orderBy(*[F.col(c).desc() for c in order])
    return df.withColumn("_rn", F.row_number().over(window)).filter("_rn = 1").drop("_rn")


def _col(df, name):
    """A column that may be absent from bronze until a file that carries it has landed."""
    return F.col(name) if name in df.columns else F.lit(None).cast("string")


def _clean_text(name):
    trimmed = F.lower(F.trim(F.col(name)))
    return F.when(trimmed != "", trimmed)


@dlt.table(
    name="silver_injuries",
    comment="Weekly injury reports, typed, one row per season, game type, week, team and player.",
)
@dlt.expect_or_drop("has_gsis_id", "gsis_id IS NOT NULL")
@dlt.expect_or_drop("has_season_and_week", "season IS NOT NULL AND week IS NOT NULL")
@dlt.expect("has_team", "team IS NOT NULL")
def silver_injuries():
    bronze = spark.read.table("bronze_injuries")  # noqa: F821 (provided by the pipeline runtime)
    typed = (
        bronze.withColumn("season", F.col("season").cast("int"))
        .withColumn("week", F.col("week").cast("int"))
        .withColumn("season_type", _col(bronze, "season_type"))
        .withColumn("date_modified", F.to_timestamp(_col(bronze, "date_modified")))
    )
    # Finding 6: deduplicate on the full key.
    latest = _latest(typed, ["season", "game_type", "week", "team", "gsis_id"])
    return latest.select(
        "season",
        "season_type",
        "game_type",
        "week",
        "team",
        "gsis_id",
        "position",
        "full_name",
        "report_primary_injury",
        "report_secondary_injury",
        "report_status",
        "practice_primary_injury",
        "practice_secondary_injury",
        "practice_status",
        "date_modified",
        "source_file",
        "load_date",
    )


@dlt.table(
    name="silver_rosters_weekly",
    comment="Weekly rosters, typed, with team codes aligned to games and injuries. "
    "Duplicate player-team-week keys in 2010 to 2015 are NOT collapsed yet.",
)
@dlt.expect_or_drop("has_gsis_id", "gsis_id IS NOT NULL")
@dlt.expect_or_drop("has_season_and_week", "season IS NOT NULL AND week IS NOT NULL")
@dlt.expect("has_team", "team IS NOT NULL")
def silver_rosters_weekly():
    mapping = F.create_map([F.lit(x) for pair in TEAM_CODE_MAP.items() for x in pair])
    bronze = spark.read.table("bronze_rosters_weekly")  # noqa: F821
    typed = (
        bronze.withColumn("season", F.col("season").cast("int"))
        .withColumn("week", F.col("week").cast("int"))
        .withColumn("roster_team_code", F.col("team"))
        .withColumn("team", F.coalesce(mapping[F.col("team")], F.col("team")))
        .withColumn("birth_date", F.to_date("birth_date"))
    )
    # Same file landed twice under two load_dates is the same rows; keep the later copy.
    # Different rows sharing a key (finding 2) differ in status and all survive.
    latest = typed.withColumn("_rank", F.dense_rank().over(
        Window.partitionBy("season").orderBy(F.col("load_date").desc())
    )).filter("_rank = 1").drop("_rank")
    return latest.select(
        "season",
        "week",
        "game_type",
        "team",
        "roster_team_code",
        "gsis_id",
        "full_name",
        "position",
        "depth_chart_position",
        "status",
        "status_description_abbr",
        "birth_date",
        "source_file",
        "load_date",
    )


@dlt.table(name="silver_players", comment="One row per player, from the latest players file.")
@dlt.expect_or_drop("has_gsis_id", "gsis_id IS NOT NULL")
def silver_players():
    typed = (
        spark.read.table("bronze_players")  # noqa: F821
        .withColumn("birth_date", F.to_date("birth_date"))
        .withColumn("rookie_season", F.col("rookie_season").cast("int"))
        .withColumn("last_season", F.col("last_season").cast("int"))
        .withColumn("height", F.col("height").cast("int"))
        .withColumn("weight", F.col("weight").cast("int"))
        .withColumn("draft_year", F.col("draft_year").cast("int"))
        .withColumn("draft_round", F.col("draft_round").cast("int"))
        .withColumn("draft_pick", F.col("draft_pick").cast("int"))
    )
    return _latest(typed, ["gsis_id"]).select(
        "gsis_id",
        "display_name",
        "first_name",
        "last_name",
        "position_group",
        "position",
        "birth_date",
        "height",
        "weight",
        "college_name",
        "rookie_season",
        "last_season",
        "latest_team",
        "status",
        "draft_year",
        "draft_round",
        "draft_pick",
        "source_file",
        "load_date",
    )


@dlt.table(name="silver_games", comment="One row per game, from the latest games file, 2010 onward.")
@dlt.expect_or_drop("has_game_id", "game_id IS NOT NULL")
@dlt.expect_or_drop("has_gameday", "gameday IS NOT NULL")
@dlt.expect("has_stadium_id", "stadium_id IS NOT NULL")
def silver_games():
    typed = (
        spark.read.table("bronze_games")  # noqa: F821
        .withColumn("season", F.col("season").cast("int"))
        .withColumn("week", F.col("week").cast("int"))
        .withColumn("gameday", F.to_date("gameday"))
        .withColumn("away_score", F.col("away_score").cast("int"))
        .withColumn("home_score", F.col("home_score").cast("int"))
        .withColumn("temp", F.col("temp").cast("int"))
        .withColumn("wind", F.col("wind").cast("int"))
        # Finding 8: trim and lowercase only. Mapping values such as a_turf is left to the owner.
        .withColumn("roof", _clean_text("roof"))
        .withColumn("surface", _clean_text("surface"))
    )
    # The file holds 1999 onward; the warehouse starts at 2010 (config source.seasons.start).
    latest = _latest(typed.filter("season >= 2010"), ["game_id"])
    return latest.select(
        "game_id",
        "season",
        "game_type",
        "week",
        "gameday",
        "away_team",
        "home_team",
        "away_score",
        "home_score",
        "location",
        "roof",
        "surface",
        "temp",
        "wind",
        "stadium_id",
        "stadium",
        "source_file",
        "load_date",
    )
