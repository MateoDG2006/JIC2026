"""Cache con invalidación por checksum de archivos (AUDIT P3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

_csv_cache: dict[str, tuple[str, pd.DataFrame]] = {}
_json_cache: dict[str, tuple[str, dict]] = {}
_checksum_registry: dict[str, str] = {}


def _checksum(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_csv_cached(path: Path) -> pd.DataFrame:
    key = str(path.resolve())
    chk = _checksum(path)
    if key in _csv_cache and _csv_cache[key][0] == chk:
        return _csv_cache[key][1].copy()
    df = pd.read_csv(path)
    _csv_cache[key] = (chk, df)
    _checksum_registry[key] = chk
    return df.copy()


def load_json_cached(path: Path) -> dict | list:
    key = str(path.resolve())
    chk = _checksum(path)
    if key in _json_cache and _json_cache[key][0] == chk:
        cached = _json_cache[key][1]
        return dict(cached) if isinstance(cached, dict) else list(cached)
    payload = json.loads(path.read_text(encoding="utf-8"))
    _json_cache[key] = (chk, payload)
    _checksum_registry[key] = chk
    return dict(payload) if isinstance(payload, dict) else list(payload)


def invalidate_all() -> None:
    """Fuerza recarga en la próxima petición."""
    _csv_cache.clear()
    _json_cache.clear()
    _checksum_registry.clear()
