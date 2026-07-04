"""Resolución de nombres físicos de tablas en ChEMBLdb SQLite."""

from __future__ import annotations

import sqlite3
from enum import Enum

from src.analisis_proyecto.core.constants import table_candidates


class ChemblSchemaError(RuntimeError):
    """El esquema SQLite no coincide con lo esperado."""


class ChemblTableKind(str, Enum):
    MOLECULE_DICTIONARY = "molecule_dictionary"
    COMPOUND_STRUCTURES = "compound_structures"
    COMPOUND_PROPERTIES = "compound_properties"
    ACTIVITIES = "activities"
    ASSAYS = "assays"
    TARGET_DICTIONARY = "target_dictionary"
    MOLECULE_SYNONYMS = "molecule_synonyms"

    @property
    def candidates(self) -> tuple[str, ...]:
        return table_candidates()[self.value]


class ChemblSchemaResolver:
    """Resuelve nombres físicos de tablas (variantes mayúsculas entre versiones ChEMBL)."""

    @classmethod
    def resolve_tables(cls, conn: sqlite3.Connection) -> dict[ChemblTableKind, str]:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        by_lower = {r[0].lower(): r[0] for r in rows}
        resolved: dict[ChemblTableKind, str] = {}
        for kind in ChemblTableKind:
            for cand in kind.candidates:
                if cand.lower() in by_lower:
                    resolved[kind] = by_lower[cand.lower()]
                    break
        missing = [k.value for k in ChemblTableKind if k not in resolved]
        if missing:
            raise ChemblSchemaError(f"Tablas no encontradas en ChEMBLdb: {missing}")
        return resolved
