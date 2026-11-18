# nfl-injury-analyzer-lakehouse

NFL player availability and injury data, 2010 to present, from [nflverse](https://github.com/nflverse/nflverse-data), built as an Azure lakehouse (ADLS Gen2 + Synapse serverless).

**Status:** the extract step is built and unit-tested. Nothing has been landed in Azure yet.

## Pipeline

1. **Extract** (`src/ingestion/extract.py`), built: downloads injuries, weekly rosters, players and games into `raw_files/`, with retries, atomic writes, CSV validation and a manifest (url, bytes, sha256, rows) beside each file.
2. **Land**, next: upload `raw_files/` to an ADLS Gen2 container unchanged, keeping the `load_date=` folders so any run can be replayed.
3. **Query**, later: Synapse serverless external tables over the landed files.

Layers beyond this are deliberately not built until data has landed and been looked at.

## Design decisions carried forward

- **Raw files are kept as downloaded** under `raw_files/<dataset>/load_date=<date>/[season=<year>/]`, each with a manifest.
- **Source findings drive later rules.** See [docs/data_profile.md](docs/data_profile.md): injuries schema drift in 2025+, duplicate roster keys in 2010 to 2015, team codes that differ by dataset and era.
- **Injury geography is inferred, not sourced.** nflverse injury reports have no field for where an injury happened, so any onset venue must be recorded with its inference method.

## Run

Prerequisites: Python 3.10+.

```
pip install -r requirements.txt
python -m src.ingestion.extract                                  # all configured seasons
python -m src.ingestion.extract --datasets injuries --seasons 2025
python -m pytest
```

## Layout

```
config/          environment settings (dev.yaml), no secrets
src/ingestion/   extract from nflverse
src/utilities/   config loader
tests/           unit tests and sanitized fixtures
docs/            source data profile
raw_files/       downloaded files (git-ignored)
```

## Configuration

Settings live in `config/<env>.yaml`, selected by `NFL_ENV` (default `dev`). Secrets never go in YAML; the loader rejects any config file with secret-like keys.

## Authors

- Ryan Osborne: concept, data model and design decisions
- Claude (Anthropic): implementation

## Data source

[nflverse](https://github.com/nflverse/nflverse-data) release files.
