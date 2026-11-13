# 0001. Add a Databricks bronze and silver layer beside SQL Server

Status: proposed. Built and unit-tested; not yet run on a Databricks workspace.

## Decision

Land the raw nflverse files in a Databricks volume, read them into Delta bronze tables with Auto Loader, and build typed silver tables from bronze. SQL Server stays the home of the dimensional model (`dim_*`, `fact_*`, SCD2 teams, injury-episode inference). The two are meant to be reconciled, as in `columbus_housing`.

## Why

- Bronze is append-only and keeps every file version, so a staging bug is fixed by replaying, not re-downloading.
- Auto Loader tracks which files it has read, so re-running never loads a file twice, and it handles the 2025 injuries schema drift (`season_type` added, `date_modified` dropped) by evolving the schema once.
- The same files feed both engines, so row counts can be compared between them.

## What exists

| Layer | Tables | Notes |
|---|---|---|
| Volume | `raw` | Files exactly as downloaded, `load_date=` folders kept. |
| Bronze | `bronze_injuries`, `bronze_rosters_weekly`, `bronze_players`, `bronze_games` | All strings, plus `source_file`, `source_modified_at`, `load_date`, `loaded_at`. |
| Silver | `silver_injuries`, `silver_rosters_weekly`, `silver_players`, `silver_games` | Typed, latest landed version per key, with expectations that drop rows missing keys. |

Rules applied from `docs/data_profile.md`: finding 3 (roster team codes aligned to games and injuries, relocations left to SCD2) and finding 6 (injuries de-duplicated on the full key). Games are limited to 2010 onward.

## Left for the project owner to decide

These are data-model choices, so silver does not guess them:

1. **Duplicate weekly-roster keys (finding 2).** Silver keeps all rows. A status precedence must be chosen before collapsing to one row per player, team and week.
2. **Roof and surface vocabulary (finding 8).** Silver only trims and lowercases. Whether `a_turf` and `astroturf` are the same value is not settled.
3. **Gold.** No gold layer yet. The star schema is still being built in T-SQL; gold on Databricks, or reconciliation only, is open.
4. **Reconciliation.** A check comparing bronze and silver counts with `raw.load_batch` is not written, because the raw load has not run against a live SQL Server.

## Not validated

Nothing here has run on Databricks. Unit tests parse the files, keep bronze dataset names in step with `config/dev.yaml`, and guard the team-code map. Run `databricks bundle validate -p nfl` before the first deploy.
