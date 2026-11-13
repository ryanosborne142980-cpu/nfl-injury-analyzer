"""Checks on the Databricks layer that need neither Databricks nor pyspark.

The pipeline files import dlt and pyspark, which only exist on Databricks, so these tests read
them as source: they must parse, agree with config/dev.yaml, and keep the team-code map intact.
"""
import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DBX = ROOT / "databricks"


def module_constant(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path.name}")


def test_all_databricks_python_files_parse():
    for path in DBX.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_bronze_datasets_match_config():
    cfg = yaml.safe_load((ROOT / "config" / "dev.yaml").read_text(encoding="utf-8"))
    configured = set(cfg["source"]["datasets"])
    assert set(module_constant(DBX / "pipelines" / "bronze.py", "DATASETS")) == configured
    assert set(module_constant(DBX / "land_raw.py", "DATASETS")) == configured


def test_bundle_pipeline_libraries_exist():
    bundle = yaml.safe_load((DBX / "databricks.yml").read_text(encoding="utf-8"))
    libraries = bundle["resources"]["pipelines"]["lakehouse"]["libraries"]
    assert libraries
    for lib in libraries:
        assert (DBX / lib["file"]["path"]).is_file()


def test_bundle_has_no_workspace_url_or_secret():
    text = (DBX / "databricks.yml").read_text(encoding="utf-8").lower()
    for banned in ("host:", "token", "password", "secret", "azuredatabricks", "cloud.databricks"):
        assert banned not in text


def test_team_code_map_aligns_roster_codes_without_touching_relocations():
    mapping = module_constant(DBX / "pipelines" / "silver.py", "TEAM_CODE_MAP")
    assert mapping == {"ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU", "SL": "STL"}
    # Relocations are dim_team's job (SCD2), so no franchise move may be mapped here.
    assert not {"OAK", "SD", "LV", "LAC", "LA"} & set(mapping)
    # A mapped code must not itself be remapped.
    assert not set(mapping.values()) & set(mapping)
