# Source data profile and staging rules

Profiled 2010 to 2026 (season 2026 in progress) from the nflverse release files. Every finding below was measured on the downloaded files, and each one drives a staging rule.

## Volumes

| Dataset | Files | Rows (2010+) | Grain |
|---|---|---|---|
| injuries | 17 (one per season) | 89,028 | season, game_type, week, team, gsis_id |
| rosters_weekly | 17 (one per season) | 681,490 | season, week, team, gsis_id (see duplicates below) |
| players | 1 | 24,869 | gsis_id |
| games | 1 (1999+) | 7,548 (4,635 since 2010) | game_id |

## Findings and rules

| # | Finding | Staging rule |
|---|---|---|
| 1 | **Schema drift in injuries.** 2025 and later files add `season_type` and drop `date_modified`. | Raw tables carry the union of columns, all nullable. The loader fails on any column the table doesn't have, and a test keeps the DDL in sync with real headers. |
| 2 | **Weekly rosters have duplicate keys in 2010 to 2015** (8,752 keys, 18,246 rows). Rows for the same player, team and week differ only in `status` (for example ACT plus TRC, TRD plus RES). | Collapse to one row per player, team and week with a documented status precedence. Record the rule in this log when implemented. |
| 3 | **Team codes differ by dataset and era.** 2010 to 2015 rosters use ARZ, BLT, CLV, HST and SL. Games and injuries use ARI, BAL, CLE, HOU and STL. | Map roster codes to the games and injuries codes before any join. 35 distinct codes appear since 2010 because of relocations (OAK to LV, SD to LAC, STL to LA), which `dim_team` handles as SCD2. |
| 4 | **Injury rows join cleanly to games on season, week and team.** 99.98% match (89,011 of 89,028 rows), and the only misses are 17 rows for BUF and CIN in 2022 week 17. That is consistent with the cancelled BUF vs CIN game, but the data doesn't say so directly. | The onset-venue inference can rely on this join. Treat the BUF/CIN week 17 rows as unmatched and keep them. |
| 5 | **Only 93.4% of injury rows appear on that week's roster** for the same team. | Key players by `gsis_id` against `players`, not against the weekly roster. |
| 6 | **Injury duplicates are rare.** 2 duplicate rows across 89,028 on the full key. | Deduplicate on the full key in staging and log the count. |
| 7 | **Stadium names change, stadium IDs don't.** 52 stadium IDs carry 79 distinct names (for example BUF00 has 3). | `dim_stadium` is keyed on `stadium_id` with the latest name. |
| 8 | **Dirty surface values.** `grass ` (trailing space), `a_turf` vs `astroturf`, 115 nulls. 23 null roofs. | Trim and map to a small controlled vocabulary. Keep nulls as unknown. |
| 9 | **Games has no city, state, latitude or longitude.** | A 52-row seed file (stadium_id to city, state, latitude, longitude) must be sourced and verified separately. |
| 10 | **Weekly rosters and injuries carry no played/did-not-play signal.** | `fact_player_week` uses `roster_status` and `on_report_flag` for now. A played flag needs a player-stats or snap-count source. |
