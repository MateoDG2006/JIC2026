"""Cliente HTTP para chembl-server (SQLite en contenedor Docker)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.analisis_proyecto.acquisition.common import MappingTableStore
from src.analisis_proyecto.acquisition.http_json import df_records, dumps_body
from src.analisis_proyecto.acquisition.local import ChemblDatabaseError, ChemblDatabaseInfo


class ChemblRemoteDatabase:
    def __init__(self, base_url: str, *, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._check_health()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}{path}",
            data=dumps_body(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> dict[str, Any]:
        resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _check_health(self) -> None:
        try:
            data = self._get("/health")
        except requests.RequestException as exc:
            raise ChemblDatabaseError(
                f"No se pudo conectar a chembl-server en {self.base_url}. "
                "Ejecuta: make chembl-server-up"
            ) from exc
        if not data.get("ok"):
            raise ChemblDatabaseError(f"chembl-server unhealthy: {self.base_url}")

    def info(self) -> ChemblDatabaseInfo:
        data = self._get("/info")
        return ChemblDatabaseInfo(
            db_path=Path(data["db_path"]),
            db_size_bytes=int(data["db_size_bytes"]),
            tables=data["tables"],
            manifest=data.get("manifest"),
            version_row=data.get("version_row"),
        )

    def fetch_activities(
        self,
        chembl_ids: list[str],
        *,
        standard_types: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        if not chembl_ids:
            return pd.DataFrame()
        data = self._post(
            "/fetch_activities",
            {"chembl_ids": chembl_ids, "standard_types": list(standard_types or ())},
        )
        rows = data.get("records") or []
        return pd.DataFrame(rows)

    def build_mapping_table(
        self,
        compounds_df: pd.DataFrame,
        *,
        verbose: bool = True,
        existing_mapping_path: str | Path | None = None,
        skip_resolved: bool = True,
    ) -> pd.DataFrame:
        existing = (
            MappingTableStore.index_resolved(prev)
            if existing_mapping_path and (prev := MappingTableStore.load(existing_mapping_path)) is not None
            else {}
        )
        data = self._post(
            "/build_mapping",
            {
                "compounds": df_records(compounds_df),
                "existing": existing,
                "skip_resolved": skip_resolved,
                "verbose": verbose,
            },
        )
        return pd.DataFrame(data.get("records") or [])

    def build_bioactivity_table(
        self,
        mapping_df: pd.DataFrame,
        *,
        verbose: bool = True,
        standard_types: tuple[str, ...] | None = None,
        pchembl_threshold: float = 6.0,
    ) -> pd.DataFrame:
        data = self._post(
            "/build_bioactivity",
            {
                "mapping": df_records(mapping_df),
                "standard_types": list(standard_types or ()),
                "pchembl_threshold": pchembl_threshold,
                "verbose": verbose,
            },
        )
        rows = data.get("records") or []
        return pd.DataFrame(rows)
