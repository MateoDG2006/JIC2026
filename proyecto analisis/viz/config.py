"""Configuración del visor analytics ChEMBL."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

from src.paths import PROJECT_ROOT, setup_path

setup_path()

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "outputs" / "dashboard"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
COMPOUNDS_ALL_CSV = DATA_DIR / "compounds_all.csv"
CHEMBL_CSV = DATA_DIR / "compounds_features.csv"
ACTIVITIES_CSV = DATA_DIR / "activities_clean.csv"
RESULTS_DIR = PROJECT_ROOT / "outputs" / "chembl" / "results"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DATA_DIR = STATIC_DIR / "data"

NUMERIC_COLS = [
    "pchembl_median_binding",
    "pchembl_std_binding",
    "pchembl_iqr_binding",
    "mw_freebase",
    "alogp",
    "psa",
    "hba",
    "hbd",
    "aromatic_rings",
    "rtb",
    "n_activities_total",
    "n_activities_binding",
]


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def use_bundle() -> bool:
    cfg = _load_yaml().get("viz", {})
    explicit = cfg.get("use_bundle")
    if explicit is True:
        return True
    if explicit is False:
        return False
    return not COMPOUNDS_ALL_CSV.is_file() and (BUNDLE_DIR / "compounds_all.csv").is_file()


def resolve_path(canonical: Path, bundle_name: str) -> Path:
    if use_bundle():
        bundle_path = BUNDLE_DIR / bundle_name
        if bundle_path.is_file():
            return bundle_path
    return canonical


def resolve_dir(canonical: Path, bundle_subdir: str) -> Path:
    if use_bundle():
        bundle_path = BUNDLE_DIR / bundle_subdir
        if bundle_path.is_dir():
            return bundle_path
    return canonical


def viz_host() -> str:
    return str(_load_yaml().get("viz", {}).get("host", "127.0.0.1"))


def viz_port() -> int:
    return int(_load_yaml().get("viz", {}).get("port", 8001))
