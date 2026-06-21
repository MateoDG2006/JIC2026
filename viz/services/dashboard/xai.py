"""Resolución de figuras XAI precomputadas.

Permite que el front-end pida ``/api/analytics/toxicity/xai?compound=...&method=...``
sin conocer el esquema de nombres exacto de los SVG en disco.

Estrategia de búsqueda (por orden de prioridad):
    1. ``xai_index.json`` (generado por ``prepare_dashboard.py``)
    2. Nombres canónicos: ``{slug}_{task}_{method}.svg``
    3. Variante con alias histórico (``NR-PPAR-gamma`` ↔ ``NR-PPAR-g``)
    4. Cualquier SVG con prefijo ``{slug}_`` y sufijo ``_{method}.svg``

``slugify("2,4-D")`` → ``"2_4_d"`` para normalizar nombres con comas/espacios.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from viz.config import BUNDLE_DIR, XAI_FIGURES_DIR, resolve_dir, use_bundle
from viz.services.dashboard.artifacts import load_xai_index


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _xai_dir() -> Path:
    return resolve_dir(XAI_FIGURES_DIR, "xai")


def resolve_xai_filename(compound: str, task: str, method: str) -> str | None:
    slug = slugify(compound)
    xai_index = load_xai_index()

    candidates: list[str] = []
    if slug in xai_index:
        for entry in xai_index[slug]:
            if entry["method"] == method:
                candidates.append(entry["file"])

    candidates.extend([
        f"{slug}_{task}_{method}.svg",
        f"{slug}_{task.replace('NR-PPAR-gamma', 'NR-PPAR-g')}_{method}.svg",
    ])

    seen: set[str] = set()
    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        if (_xai_dir() / name).is_file():
            return name

    for svg in sorted(_xai_dir().glob(f"{slug}_*_{method}.svg")):
        return svg.name
    return None


def xai_figures_dir() -> Path:
    if use_bundle() and (BUNDLE_DIR / "xai").is_dir():
        return BUNDLE_DIR / "xai"
    return XAI_FIGURES_DIR
