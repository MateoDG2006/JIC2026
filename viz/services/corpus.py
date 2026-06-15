"""Servicio de corpus pre-computado: carga y sirve datos XAI pre-calculados."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from viz.config import CORPUS_DIR

_corpus_cache: dict[str, dict[str, Any]] | None = None


def _load_corpus() -> dict[str, dict[str, Any]]:
    """Carga todos los JSON pre-computados del directorio viz/data/."""
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache

    _corpus_cache = {}
    if not CORPUS_DIR.is_dir():
        return _corpus_cache

    for f in sorted(CORPUS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            compound_id = f.stem
            data["id"] = compound_id
            _corpus_cache[compound_id] = data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[corpus] Error cargando {f.name}: {e}")

    return _corpus_cache


def list_compounds() -> list[dict[str, Any]]:
    """Lista resumen de todos los compuestos pre-computados."""
    corpus = _load_corpus()
    result = []
    for cid, data in corpus.items():
        preds = data.get("predictions", {})
        max_task = max(preds, key=preds.get) if preds else ""
        max_prob = max(preds.values()) if preds else 0.0

        if max_prob > 0.7:
            risk = "ALTO"
        elif max_prob > 0.4:
            risk = "MODERADO"
        else:
            risk = "BAJO"

        result.append({
            "id": cid,
            "name": data.get("name", cid),
            "smiles": data.get("smiles", ""),
            "top_task": max_task,
            "top_prob": round(max_prob, 3),
            "risk": risk,
            "family": data.get("family", ""),
            "demo": bool(data.get("demo", False)),
        })
    return result


def get_compound(compound_id: str) -> dict[str, Any] | None:
    """Retorna datos completos de un compuesto pre-computado."""
    corpus = _load_corpus()
    return corpus.get(compound_id)


def reload_corpus() -> int:
    """Fuerza recarga del corpus. Retorna cantidad de compuestos cargados."""
    global _corpus_cache
    _corpus_cache = None
    return len(_load_corpus())
