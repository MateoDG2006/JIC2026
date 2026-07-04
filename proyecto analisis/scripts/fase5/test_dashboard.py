#!/usr/bin/env python
"""Smoke test del visor analytics (proyecto analisis)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.paths import setup_path  # noqa: E402

setup_path()

from viz.config import CHEMBL_CSV, ARTIFACTS_DIR  # noqa: E402


def main() -> int:
    assert CHEMBL_CSV.is_file(), f"Falta {CHEMBL_CSV}"
    assert ARTIFACTS_DIR.is_dir(), f"Falta {ARTIFACTS_DIR}"
    from viz.app import app  # noqa: F401

    print("=== test_dashboard OK (proyecto analisis) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
