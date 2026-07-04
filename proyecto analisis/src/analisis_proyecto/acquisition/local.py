"""Consultas ChEMBL sobre SQLite — solo dentro de chembl-server (contenedor Docker)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.analisis_proyecto.acquisition.common import (
    ActivityClassAssigner,
    MappingTableStore,
    MolecularPropertyCalculator,
    SmilesCanonicalizer,
)
from src.analisis_proyecto.acquisition.sqlalchemy import (
    ChemblSqlEngine,
    ReflectedChemblSchema,
    get_chembl_engine,
)
from src.analisis_proyecto.core.models import (
    BioactivitySchema,
    ChemblMatch,
    CorpusCompound,
    MappingRecord,
    MidaRegistry,
    StandardActivityTypes,
)


class ChemblDatabaseError(FileNotFoundError):
    """La base SQLite de ChEMBL no está disponible."""


@dataclass
class ChemblDatabaseInfo:
    db_path: Path
    db_size_bytes: int
    tables: dict[str, str]
    manifest: dict[str, Any] | None
    version_row: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_size_bytes,
            "tables": self.tables,
            "manifest": self.manifest,
            "version_row": self.version_row,
        }


class ChemblIdResolver:
    """Resuelve PubChem/MIDA → ChEMBL ID vía SQLAlchemy Core."""

    def __init__(self, registry: MidaRegistry | None = None) -> None:
        self.registry = registry or MidaRegistry()

    def resolve(
        self,
        compound: CorpusCompound,
        sql: ChemblSqlEngine,
        schema: ReflectedChemblSchema,
        *,
        use_known_registry: bool = True,
    ) -> ChemblMatch:
        if use_known_registry:
            chembl_id = self.registry.chembl_id(compound.compound_name)
            if chembl_id:
                pref = self._fetch_pref_name(sql, schema, chembl_id)
                return ChemblMatch.found(chembl_id, "known_registry", pref_name=pref)

        canon = SmilesCanonicalizer.canonicalize(compound.smiles)
        if canon:
            rows = sql.fetch_all(schema.build_smiles_lookup(canon))
            if len(rows) == 1:
                return ChemblMatch.found(rows[0][0], "sqlite_smiles", pref_name=rows[0][1])
            if len(rows) > 1:
                return ChemblMatch.found(
                    rows[0][0], "sqlite_smiles", ambiguous=True, n_candidates=len(rows), pref_name=rows[0][1]
                )

        rows = sql.fetch_all(schema.build_pref_name_lookup(compound.compound_name))
        if len(rows) == 1:
            return ChemblMatch.found(rows[0][0], "sqlite_pref_name", pref_name=rows[0][1])
        if len(rows) > 1:
            return ChemblMatch.found(
                rows[0][0], "sqlite_pref_name", ambiguous=True, n_candidates=len(rows), pref_name=rows[0][1]
            )

        rows = sql.fetch_all(schema.build_synonym_lookup(compound.compound_name))
        if len(rows) == 1:
            return ChemblMatch.found(rows[0][0], "sqlite_synonym", pref_name=rows[0][1])
        if len(rows) > 1:
            return ChemblMatch.found(
                rows[0][0], "sqlite_synonym", ambiguous=True, n_candidates=len(rows), pref_name=rows[0][1]
            )

        return ChemblMatch.not_found()

    @staticmethod
    def _fetch_pref_name(sql: ChemblSqlEngine, schema: ReflectedChemblSchema, chembl_id: str) -> str | None:
        row = sql.fetch_one(schema.build_pref_name_by_id(chembl_id))
        return row[0] if row else None


class ChemblDatabase:
    """Acceso tipado a ChEMBLdb SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = self.ensure_exists(db_path)
        self._sql = get_chembl_engine(str(self.db_path.resolve()))
        self._resolver = ChemblIdResolver()

    @property
    def sql_engine(self) -> ChemblSqlEngine:
        return self._sql

    @staticmethod
    def ensure_exists(db_path: str | Path) -> Path:
        path = Path(db_path)
        if not path.is_file():
            raise ChemblDatabaseError(f"No se encontró ChEMBLdb en {path}.")
        return path

    def info(self) -> ChemblDatabaseInfo:
        manifest_path = self.db_path.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
        return ChemblDatabaseInfo(
            db_path=self.db_path,
            db_size_bytes=self.db_path.stat().st_size,
            tables=self._sql.table_names(),
            manifest=manifest,
            version_row=self._sql.version_row(),
        )

    def fetch_activities(
        self,
        chembl_ids: list[str],
        *,
        standard_types: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        if not chembl_ids:
            return pd.DataFrame()
        types = standard_types or StandardActivityTypes.DEFAULT
        schema = self._sql.schema()
        stmt = schema.build_activity_query(chembl_ids, standard_types=types)
        return self._sql.read_df(stmt)

    def build_mapping_table(
        self,
        compounds_df: pd.DataFrame,
        *,
        verbose: bool = True,
        existing_mapping_path: str | Path | None = None,
        existing_resolved: dict[str, dict[str, Any]] | None = None,
        skip_resolved: bool = True,
    ) -> pd.DataFrame:
        if existing_resolved is not None:
            existing = existing_resolved
        elif existing_mapping_path and (prev := MappingTableStore.load(existing_mapping_path)) is not None:
            existing = MappingTableStore.index_resolved(prev)
        else:
            existing = {}
        schema = self._sql.schema()
        records: list[dict[str, Any]] = []
        for _, row in compounds_df.iterrows():
            compound = CorpusCompound.from_row(row)
            if skip_resolved and compound.mapping_key in existing:
                if verbose:
                    print(f"  {compound.compound_name}: reutilizado ({existing[compound.mapping_key].get('chembl_id')})")
                records.append(existing[compound.mapping_key])
                continue
            if verbose:
                print(f"  Mapeando (SQLite): {compound.compound_name}")
            match = self._resolver.resolve(compound, self._sql, schema)
            records.append(MappingRecord(compound, match).to_dict())
        return pd.DataFrame(records)

    def build_bioactivity_table(
        self,
        mapping_df: pd.DataFrame,
        *,
        verbose: bool = True,
        standard_types: tuple[str, ...] | None = None,
        pchembl_threshold: float = 6.0,
    ) -> pd.DataFrame:
        resolved = mapping_df[mapping_df["chembl_id"].notna() & (mapping_df["chembl_id"] != "")]
        if resolved.empty:
            return BioactivitySchema.empty_frame()

        chembl_ids = resolved["chembl_id"].astype(str).unique().tolist()
        types = standard_types or StandardActivityTypes.DEFAULT
        if verbose:
            print(f"  Consultando SQLite: {len(chembl_ids)} moléculas, {len(types)} tipos de actividad...")

        act_df = self.fetch_activities(chembl_ids, standard_types=types)
        if act_df.empty:
            return BioactivitySchema.empty_frame()
        if verbose:
            print(f"  -> {len(act_df):,} registros raw desde ChEMBLdb")

        meta = resolved.set_index("chembl_id", drop=False)
        props_cache: dict[str, dict[str, Any]] = {}
        rows: list[dict[str, Any]] = []
        for _, act in act_df.iterrows():
            cid = act["chembl_id"]
            if cid not in meta.index:
                continue
            m = meta.loc[cid]
            if isinstance(m, pd.DataFrame):
                m = m.iloc[0]
            compound = CorpusCompound.from_row(m)
            smiles = compound.smiles or act.get("smiles")
            if cid not in props_cache:
                props_cache[cid] = MolecularPropertyCalculator.from_smiles(
                    str(smiles) if smiles else ""
                ).to_dict()
            props = props_cache[cid]
            merged_props = {
                key: act.get(key) if pd.notna(act.get(key)) else props.get(key)
                for key in props
            }
            rows.append({
                "compound_name": compound.compound_name,
                "pubchem_cid": compound.pubchem_cid,
                "chembl_id": cid,
                "smiles": smiles,
                "family": compound.family,
                "match_method": m["match_method"],
                "activity_id": act.get("activity_id"),
                "assay_chembl_id": act.get("assay_chembl_id"),
                "target_chembl_id": act.get("target_chembl_id"),
                "target_name": act.get("target_name"),
                "target_type": act.get("target_type"),
                "organism": act.get("organism"),
                "standard_type": act.get("standard_type"),
                "standard_value": act.get("standard_value"),
                "standard_units": act.get("standard_units"),
                "standard_relation": act.get("standard_relation"),
                "pchembl_value": act.get("pchembl_value"),
                "pchembl_imputed": False,
                "activity_comment": act.get("activity_comment"),
                "data_validity_comment": act.get("data_validity_comment"),
                "potential_duplicate": act.get("potential_duplicate"),
                "assay_type": act.get("assay_type"),
                "bao_label": act.get("bao_label"),
                **merged_props,
            })

        df = pd.DataFrame(rows)
        df = ActivityClassAssigner.assign(df, threshold=pchembl_threshold)
        return df.reindex(columns=list(BioactivitySchema.COLUMNS))
