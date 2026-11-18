---
name: rebuild
description: Safely rebuild the silver or gold layer in Synapse serverless (drop CETAS tables, delete their lake folders, re-run the layer SQL, verify counts). Use whenever a silver/gold SQL file changed and needs re-running, a CETAS fails with "location already exists", or the user says "rebuild silver/gold".
argument-hint: "<silver|gold> [--rerun-check]"
---

Layer: $ARGUMENTS (must be `silver` or `gold`; ask if missing or anything else. Bronze is
views only and never needs this; just re-run `sql/10_bronze.sql`.)

All the work is done by `scripts/rebuild_layer.py`. Don't hand-roll drops or `az storage`
deletes for layer rebuilds.

1. **Pre-flight.** Confirm the workspace is up (`az resource list -g rg-medallion-lab`) and
   `git status` shows the layer SQL you expect. If the SQL file has uncommitted changes,
   say so; that's fine, it's what gets rebuilt.
2. **Dry run.** `python scripts/rebuild_layer.py <layer>`. Show the user the plan: each
   table and the `lake/` folder that will be **deleted**.
3. **Confirm.** Ask the user to approve that exact list. Stop if a folder looks wrong.
4. **Apply.** `python scripts/rebuild_layer.py <layer> --apply`. Add `--rerun-check` when
   the layer's logic changed (proves idempotency). The guard hook will prompt; that's expected.
5. **Report.** Row counts per table, rerun-check result, `90_checks.sql` results, and any
   failure output verbatim. If silver was rebuilt, say gold is now stale and offer to rebuild it.
6. **Record.** If counts or grain changed, update `docs/data_contracts.md`; update
   **Where we left off** in `CLAUDE.md`.

If the script fails mid-way, every step is idempotent: fix the cause and re-run `--apply`.
If it refuses a LOCATION, fix the SQL (CETAS targets must be `<layer>/<subfolder>/`); never
work around the refusal.

SQL conventions this relies on (keep layer files compatible):
- One file per layer: `sql/20_silver.sql`, `sql/30_gold.sql`.
- CETAS form: `CREATE EXTERNAL TABLE silver.x WITH (LOCATION = 'silver/x/', DATA_SOURCE = ...,
  FILE_FORMAT = ...) AS SELECT ...`, one folder per table.
- The file may also contain `CREATE OR ALTER VIEW`s; those aren't touched.
