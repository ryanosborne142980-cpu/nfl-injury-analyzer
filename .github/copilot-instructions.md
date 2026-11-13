# Copilot instructions

Read and follow the repository-wide guidance in `AGENTS.md` before making changes.

- Keep changes focused and preserve unrelated user work.
- Do not create commits, push, open or merge pull requests, tag releases, delete branches, or run destructive/live database operations unless the user explicitly asks.
- Run relevant tests; run `python -m pytest` before a requested commit or pull request. Report what was and was not verified.
- Keep credentials and raw source data out of Git. Never repeat a discovered secret in a response.
- For SQL raw DDL changes, run `python -m pytest tests/unit/test_raw_ddl.py`. For staging-rule or data-finding changes, update `docs/data_profile.md`.
