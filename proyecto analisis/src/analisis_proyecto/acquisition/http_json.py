"""Serialización JSON para peticiones HTTP al chembl-server."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def df_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame → registros con null JSON válidos (sin NaN/inf/numpy)."""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def dumps_body(payload: dict[str, Any]) -> bytes:
    """Serializa el cuerpo de la petición; falla si queda algún NaN/inf."""
    return json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
