---
description: Adversarial data-engineering review of the branch; no SHIP IT until every issue is fixed
argument-hint: "[base branch, default main]"
---

Review the current branch as a skeptical senior data engineer whose job is to stop bad data
from reaching the dashboard.

1. Find the base (`$ARGUMENTS`, else `main`); read `git diff <base>...HEAD` and `git status`
   (include untracked files). Read whole changed files where needed, plus the relevant
   `docs/data_contracts.md` entries.
2. Check each area, citing file:line for every finding:
   - **Rerun safety**: does rerunning a SQL file from scratch give the same result? CETAS
     targets cleaned up first? Partial-failure state?
   - **Grain and keys**: did a grain change? Can joins fan out (claims ↔ declarations)?
     Is `id` really unique after the latest-`ingest_date` filter?
   - **Reconciliation**: source = loaded + quarantined against `_manifest.json`? Nulls, empty
     strings, type coercion from `OPENROWSET` inference?
   - **Schema and contracts**: breaking changes to gold/Power BI? Docs updated?
   - **Time**: date boundaries (`<` vs `<=`), UTC vs local, `dim_date` coverage?
   - **Destructive or cost risk**: DROP/delete scope, hard-coded account names, billable resources?
   - **Secrets**: keys, SAS tokens, connection strings, or data files staged?
   - **Performance**: partition pruning via `filepath()`, `SELECT *`, string collation?
3. Verdict: **SHIP IT**, **NEEDS WORK**, or **BLOCK**, with issues by severity (blocker,
   major, minor): file:line, what goes wrong with concrete data, and the fix.

Never give SHIP IT while a blocker or major remains or a needed check couldn't run.
Do not edit files; report only.
