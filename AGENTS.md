# Project guidance for people and AI agents

This repository builds an NFL injury and player-availability warehouse from nflverse data. Keep changes scoped, preserve existing work, and do not confuse inferred data with source facts.

## Human and AI responsibilities

- The human owns the requested scope, data-model decisions, and approval of production or release actions.
- Inspect `git status --short --branch` and the relevant diffs before changing files. Never overwrite, discard, or silently stash user changes.
- Do not create commits, push, open or merge pull requests, tag releases, or delete branches unless the user explicitly asks for that action. A request to prepare a pull request is not permission to merge it.
- Never force-push to `main` or rewrite published history. Force-pushing an unmerged feature branch requires an explicit request and target verification.
- Do not run destructive DDL or write to a live/production database without explicit authorization. Use development/test databases for validation.
- Do not put credentials in source, configuration, logs, or responses. If a credential or private data is found in a diff, stop the affected publish action and report the file without repeating the value.

## Project conventions

- Python source is in `src/`; SQL is organized under `sql/raw`, `sql/staging`, `sql/dim`, and `sql/fact`.
- Raw downloads belong under `raw_files/` and must not be committed. Use sanitized fixtures under `tests/fixtures/` for tests.
- Keep secrets out of YAML configuration. Database credentials are read from `DB_USER` and `DB_PASSWORD` environment variables.
- Injury geography is inferred, not sourced. Preserve explicit inference metadata and update `docs/data_profile.md` when staging rules or data findings change.
- Follow the existing project style and prefer small, single-purpose changes.

## Validation

- Run focused tests during development and `python -m pytest` before committing or opening a pull request. Do not proceed with those actions when tests fail.
- If `sql/raw/*.sql` changes, run `python -m pytest tests/unit/test_raw_ddl.py`.
- Tests use fixtures and do not require a live SQL Server. State clearly whether a change was also validated against a live server.
- Review staged and untracked files separately; a clean `git diff` does not show untracked files.
- Secret searches are useful heuristics, not proof that a repository is secret-free.

## Repository settings to configure

These controls are not enforced by this file. In GitHub, protect `main`, require the CI checks to pass, disallow force-pushes, and enable secret scanning and push protection when available.
