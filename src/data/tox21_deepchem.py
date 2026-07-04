"""Carga Tox21 desde DeepChem con caché local y recuperación ante corrupción."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import deepchem as dc
    from deepchem.data import Dataset

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / "processed" / "deepchem_cache"


def _featurized_root(save_dir: Path) -> Path:
    return save_dir / "tox21-featurized" / "RawFeaturizer" / "ScaffoldSplitter"


def _cache_is_valid(save_dir: Path) -> bool:
    """True si existen los metadatos de train/val/test en disco."""
    root = _featurized_root(save_dir)
    if not root.exists():
        return False
    for sub in root.rglob("*_dir"):
        if sub.name not in {"train_dir", "valid_dir", "test_dir"}:
            continue
        meta = sub / "metadata.csv.gzip"
        legacy = sub / "metadata.joblib"
        if not meta.is_file() and not legacy.is_file():
            return False
    return any(root.rglob("train_dir"))


def _clear_featurized_cache(save_dir: Path) -> None:
    featurized = save_dir / "tox21-featurized"
    if featurized.exists():
        shutil.rmtree(featurized)


def load_tox21_raw_scaffold(
    *,
    reload: bool = True,
) -> tuple[list[str], tuple[Dataset, Dataset, Dataset], list]:
    """Descarga Tox21 (SMILES crudos, split scaffold) desde DeepChem.

    Usa ``data/raw`` para el CSV y ``data/processed/deepchem_cache`` para
    el caché featurizado. Si el caché está incompleto, lo elimina y reconstruye.
    """
    import deepchem as dc

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not _cache_is_valid(CACHE_DIR):
        _clear_featurized_cache(CACHE_DIR)

    kwargs = dict(
        featurizer=dc.feat.RawFeaturizer(),
        splitter="scaffold",
        data_dir=str(RAW_DIR),
        save_dir=str(CACHE_DIR),
    )

    try:
        tasks, splits, transformers = dc.molnet.load_tox21(
            reload=reload, **kwargs
        )
    except ValueError as exc:
        if "No Metadata found" not in str(exc):
            raise
        print("Caché DeepChem corrupto; reconstruyendo Tox21...")
        _clear_featurized_cache(CACHE_DIR)
        tasks, splits, transformers = dc.molnet.load_tox21(
            reload=False, **kwargs
        )

    return tasks, splits, transformers
