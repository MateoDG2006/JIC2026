"""SQLAlchemy 2.0 Core — reflexión parcial de ChEMBLdb (7 tablas)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import MetaData, create_engine, func, literal, null, or_, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from src.analisis_proyecto.acquisition.schema import (
    ChemblSchemaResolver,
    ChemblTableKind,
)
from src.analisis_proyecto.core.constants import column_aliases, descriptor_columns

_ALIASES = column_aliases()


def _pick_col(table, cols_lower: set[str], *candidates: str) -> str:
    for c in candidates:
        if c.lower() in cols_lower:
            return c
    return candidates[-1]


@dataclass(frozen=True)
class ReflectedChemblSchema:
    """Esquema ChEMBL reflejado — tablas SQLAlchemy + metadatos de columnas."""

    tables: dict[ChemblTableKind, Any]
    molecule_chembl_col: str
    molecule_pref_col: str
    molecule_molregno_col: str
    structure_smiles_col: str
    synonym_col: str
    assay_chembl_col: str
    assay_type_col: str
    bao_col: str | None
    target_chembl_col: str
    target_pref_col: str
    target_type_col: str
    target_organism_col: str
    property_columns: frozenset[str]

    def table(self, kind: ChemblTableKind):
        return self.tables[kind]

    @classmethod
    def reflect(cls, engine: Engine) -> ReflectedChemblSchema:
        raw = engine.raw_connection()
        try:
            logical_names = ChemblSchemaResolver.resolve_tables(raw)
        finally:
            raw.close()
        physical = list(logical_names.values())

        metadata = MetaData()
        metadata.reflect(bind=engine, only=physical)

        by_logical = {kind: metadata.tables[name] for kind, name in logical_names.items()}
        md = by_logical[ChemblTableKind.MOLECULE_DICTIONARY]
        cs = by_logical[ChemblTableKind.COMPOUND_STRUCTURES]
        ms = by_logical[ChemblTableKind.MOLECULE_SYNONYMS]
        ass = by_logical[ChemblTableKind.ASSAYS]
        td = by_logical[ChemblTableKind.TARGET_DICTIONARY]
        cp = by_logical[ChemblTableKind.COMPOUND_PROPERTIES]

        md_cols = {c.name.lower() for c in md.columns}
        cs_cols = {c.name.lower() for c in cs.columns}
        ms_cols = {c.name.lower() for c in ms.columns}
        ass_cols = {c.name.lower() for c in ass.columns}
        td_cols = {c.name.lower() for c in td.columns}
        cp_cols = {c.name.lower() for c in cp.columns}

        return cls(
            tables=by_logical,
            molecule_chembl_col=_pick_col(md, md_cols, *_ALIASES["molecule_chembl"]),
            molecule_pref_col=_pick_col(md, md_cols, *_ALIASES["molecule_pref"]),
            molecule_molregno_col=_pick_col(md, md_cols, *_ALIASES["molecule_molregno"]),
            structure_smiles_col=_pick_col(cs, cs_cols, *_ALIASES["structure_smiles"]),
            synonym_col=_pick_col(ms, ms_cols, *_ALIASES["synonym"]),
            assay_chembl_col=_pick_col(ass, ass_cols, *_ALIASES["assay_chembl"]),
            assay_type_col=_pick_col(ass, ass_cols, *_ALIASES["assay_type"]),
            bao_col=next((c for c in _ALIASES["bao"] if c in ass_cols), None),
            target_chembl_col=_pick_col(td, td_cols, *_ALIASES["target_chembl"]),
            target_pref_col=_pick_col(td, td_cols, *_ALIASES["target_pref"]),
            target_type_col=_pick_col(td, td_cols, *_ALIASES["target_type"]),
            target_organism_col=_pick_col(td, td_cols, *_ALIASES["target_organism"]),
            property_columns=frozenset(cp_cols),
        )

    def build_activity_query(
        self,
        chembl_ids: list[str],
        *,
        standard_types: tuple[str, ...],
    ) -> Select:
        md = self.table(ChemblTableKind.MOLECULE_DICTIONARY)
        cs = self.table(ChemblTableKind.COMPOUND_STRUCTURES)
        cp = self.table(ChemblTableKind.COMPOUND_PROPERTIES)
        act = self.table(ChemblTableKind.ACTIVITIES)
        ass = self.table(ChemblTableKind.ASSAYS)
        td = self.table(ChemblTableKind.TARGET_DICTIONARY)

        md_chembl = md.c[self.molecule_chembl_col]
        md_molregno = md.c[self.molecule_molregno_col]

        bao_expr: ColumnElement[Any] = (
            ass.c[self.bao_col].label("bao_label")
            if self.bao_col
            else literal(None).label("bao_label")
        )

        prop_cols = []
        for col in descriptor_columns():
            if col in self.property_columns:
                prop_cols.append(cp.c[col].label(col))
            else:
                prop_cols.append(null().label(col))

        return (
            select(
                md_chembl.label("chembl_id"),
                cs.c[self.structure_smiles_col].label("smiles"),
                act.c.activity_id,
                ass.c[self.assay_chembl_col].label("assay_chembl_id"),
                td.c[self.target_chembl_col].label("target_chembl_id"),
                td.c[self.target_pref_col].label("target_name"),
                td.c[self.target_type_col].label("target_type"),
                td.c[self.target_organism_col].label("organism"),
                act.c.standard_type,
                act.c.standard_value,
                act.c.standard_units,
                act.c.standard_relation,
                act.c.pchembl_value,
                act.c.activity_comment,
                act.c.data_validity_comment,
                act.c.potential_duplicate,
                ass.c[self.assay_type_col].label("assay_type"),
                bao_expr,
                *prop_cols,
            )
            .select_from(act)
            .join(md, act.c.molregno == md_molregno)
            .outerjoin(cs, md_molregno == cs.c.molregno)
            .outerjoin(cp, md_molregno == cp.c.molregno)
            .join(ass, act.c.assay_id == ass.c.assay_id)
            .outerjoin(td, ass.c.tid == td.c.tid)
            .where(md_chembl.in_(chembl_ids))
            .where(act.c.standard_type.in_(standard_types))
            .where(
                or_(
                    act.c.standard_value.isnot(None),
                    act.c.pchembl_value.isnot(None),
                )
            )
        )

    def build_smiles_lookup(self, canonical_smiles: str) -> Select:
        md = self.table(ChemblTableKind.MOLECULE_DICTIONARY)
        cs = self.table(ChemblTableKind.COMPOUND_STRUCTURES)
        return (
            select(md.c[self.molecule_chembl_col], md.c[self.molecule_pref_col])
            .select_from(cs)
            .join(md, cs.c.molregno == md.c[self.molecule_molregno_col])
            .where(cs.c[self.structure_smiles_col] == canonical_smiles)
            .limit(2)
        )

    def build_pref_name_lookup(self, compound_name: str) -> Select:
        md = self.table(ChemblTableKind.MOLECULE_DICTIONARY)
        return (
            select(md.c[self.molecule_chembl_col], md.c[self.molecule_pref_col])
            .where(func.upper(md.c[self.molecule_pref_col]) == compound_name.upper())
            .limit(2)
        )

    def build_synonym_lookup(self, compound_name: str) -> Select:
        md = self.table(ChemblTableKind.MOLECULE_DICTIONARY)
        ms = self.table(ChemblTableKind.MOLECULE_SYNONYMS)
        return (
            select(md.c[self.molecule_chembl_col], md.c[self.molecule_pref_col])
            .select_from(ms)
            .join(md, ms.c.molregno == md.c[self.molecule_molregno_col])
            .where(func.upper(ms.c[self.synonym_col]) == compound_name.upper())
            .limit(2)
        )

    def build_pref_name_by_id(self, chembl_id: str) -> Select:
        md = self.table(ChemblTableKind.MOLECULE_DICTIONARY)
        return (
            select(md.c[self.molecule_pref_col])
            .where(md.c[self.molecule_chembl_col] == chembl_id)
            .limit(1)
        )


class ChemblSqlEngine:
    """Motor SQLAlchemy read-only sobre ChEMBLdb SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path).resolve()
        self.db_path = path
        self._engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        self._schema: ReflectedChemblSchema | None = None

    @property
    def engine(self) -> Engine:
        return self._engine

    def schema(self) -> ReflectedChemblSchema:
        if self._schema is None:
            self._schema = ReflectedChemblSchema.reflect(self._engine)
        return self._schema

    def read_df(self, stmt: Select) -> pd.DataFrame:
        with self._engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def fetch_all(self, stmt: Select) -> list[tuple[Any, ...]]:
        with self._engine.connect() as conn:
            return list(conn.execute(stmt).fetchall())

    def fetch_one(self, stmt: Select) -> tuple[Any, ...] | None:
        with self._engine.connect() as conn:
            return conn.execute(stmt).fetchone()

    def table_names(self) -> dict[str, str]:
        s = self.schema()
        return {kind.value: t.name for kind, t in s.tables.items()}

    def version_row(self) -> dict[str, Any] | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name LIKE 'version%' LIMIT 1"
                )
            ).fetchone()
            if not row:
                return None
            vtable = row[0]
            try:
                ver = conn.execute(text(f"SELECT * FROM {vtable} LIMIT 1")).mappings().first()
                return dict(ver) if ver else None
            except Exception:
                return None


@lru_cache(maxsize=4)
def get_chembl_engine(db_path: str) -> ChemblSqlEngine:
    """Cache de motores por ruta absoluta (evita re-reflexión en la misma sesión)."""
    return ChemblSqlEngine(db_path)
