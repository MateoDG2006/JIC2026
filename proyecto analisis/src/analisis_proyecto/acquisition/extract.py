"""Orquestador de extracción ChEMBL vía chembl-server (HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.analisis_proyecto.acquisition.common import (
    CorpusLoader,
    ExtractionSummarizer,
    QualityFilterPipeline,
)
from src.analisis_proyecto.acquisition.db import connect_chembl
from src.analisis_proyecto.core.models import ChemblConfig


class ChemblConfigLoader:
    @staticmethod
    def project_root() -> Path:
        from src.paths import PROJECT_ROOT
        return PROJECT_ROOT

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> ChemblConfig:
        cfg_file = Path(config_path) if config_path else cls.project_root() / "config" / "config.yaml"
        section: dict[str, Any] | None = None
        if cfg_file.is_file():
            with cfg_file.open(encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            section = raw.get("chembl") or {}
        return ChemblConfig.from_yaml_section(section)


@dataclass
class ChemblExtractionResult:
    compounds: pd.DataFrame
    mapping: pd.DataFrame
    raw: pd.DataFrame
    clean: pd.DataFrame
    filter_stats: pd.DataFrame
    summary: pd.DataFrame


class ChemblExtractor:
    """Pipeline completo: corpus PubChem → mapping → bioactividad → filtros."""

    def __init__(self, config: ChemblConfig | None = None) -> None:
        self.config = config or ChemblConfigLoader.load()
        self.database = connect_chembl(self.config)
        self.corpus_loader = CorpusLoader()

    @classmethod
    def from_config_file(cls, config_path: str | Path) -> ChemblExtractor:
        return cls(ChemblConfigLoader.load(config_path))

    def standard_types(self) -> tuple[str, ...]:
        return self.config.standard_types_tuple()

    def load_compounds(self, corpus_path: str | Path) -> pd.DataFrame:
        return self.corpus_loader.load(corpus_path)

    def build_mapping(
        self,
        compounds_df: pd.DataFrame,
        *,
        existing_mapping_path: str | Path | None = None,
        skip_resolved: bool = True,
        verbose: bool = True,
    ) -> pd.DataFrame:
        return self.database.build_mapping_table(
            compounds_df,
            existing_mapping_path=existing_mapping_path,
            skip_resolved=skip_resolved,
            verbose=verbose,
        )

    def build_bioactivity(
        self,
        mapping_df: pd.DataFrame,
        *,
        verbose: bool = True,
    ) -> pd.DataFrame:
        return self.database.build_bioactivity_table(
            mapping_df,
            standard_types=self.standard_types(),
            pchembl_threshold=self.config.pchembl_active_threshold,
            verbose=verbose,
        )

    def apply_filters(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        return QualityFilterPipeline(self.config.quality_filters).apply(raw_df)

    def run(
        self,
        corpus_path: str | Path,
        *,
        existing_mapping_path: str | Path | None = None,
        skip_resolved: bool = True,
        verbose: bool = True,
    ) -> ChemblExtractionResult:
        compounds = self.load_compounds(corpus_path)
        mapping = self.build_mapping(
            compounds,
            existing_mapping_path=existing_mapping_path,
            skip_resolved=skip_resolved,
            verbose=verbose,
        )
        raw = self.build_bioactivity(mapping, verbose=verbose)
        clean, stats = self.apply_filters(raw)
        summary = ExtractionSummarizer.summarize(compounds, mapping, raw, clean)
        return ChemblExtractionResult(compounds, mapping, raw, clean, stats, summary)
