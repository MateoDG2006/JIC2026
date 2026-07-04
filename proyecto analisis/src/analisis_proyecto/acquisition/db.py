"""Cliente ChEMBL — solo vía chembl-server (HTTP)."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from src.analisis_proyecto.acquisition.local import ChemblDatabaseInfo
from src.analisis_proyecto.core.models import ChemblConfig


class ChemblBackend(Protocol):
    def info(self) -> ChemblDatabaseInfo: ...

    def fetch_activities(
        self,
        chembl_ids: list[str],
        *,
        standard_types: tuple[str, ...] | None = None,
    ) -> pd.DataFrame: ...

    def build_mapping_table(
        self,
        compounds_df: pd.DataFrame,
        *,
        verbose: bool = True,
        existing_mapping_path: str | None = None,
        skip_resolved: bool = True,
    ) -> pd.DataFrame: ...

    def build_bioactivity_table(
        self,
        mapping_df: pd.DataFrame,
        *,
        verbose: bool = True,
        standard_types: tuple[str, ...] | None = None,
        pchembl_threshold: float = 6.0,
    ) -> pd.DataFrame: ...


def connect_chembl(config: ChemblConfig) -> ChemblBackend:
    from src.analisis_proyecto.acquisition.remote import ChemblRemoteDatabase
    return ChemblRemoteDatabase(config.require_server_url())
