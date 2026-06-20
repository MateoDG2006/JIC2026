"""
Extracción ChEMBL offline desde ChEMBLdb SQLite (Flujo A).

Consulta local en lugar de la API REST — segundos vs horas para los 20 MIDA.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from src.analisis_proyecto.chembl_api import (
    BIOACTIVITY_COLUMNS,
    KNOWN_MIDA_CHEMBL_IDS,
    PCHEMBL_ACTIVE_THRESHOLD,
    STANDARD_TYPES,
    _mapping_row_key,
    _match_result,
    canonicalize_smiles,
    derive_activity_class,
    load_mapping_table,
    resolve_molecule_props,
)

# Tablas lógicas → candidatos de nombre en ChEMBLdb
_TABLE_CANDIDATES: dict[str, list[str]] = {
    "molecule_dictionary": ["molecule_dictionary", "MOLECULE_DICTIONARY"],
    "compound_structures": ["compound_structures", "COMPOUND_STRUCTURES"],
    "compound_properties": ["compound_properties", "COMPOUND_PROPERTIES"],
    "activities": ["activities", "ACTIVITIES"],
    "assays": ["assays", "ASSAYS"],
    "target_dictionary": ["target_dictionary", "TARGET_DICTIONARY"],
    "molecule_synonyms": ["molecule_synonyms", "MOLECULE_SYNONYMS"],
}


class ChemblDatabaseError(FileNotFoundError):
    """La base SQLite de ChEMBL no está disponible."""


class ChemblSchemaError(RuntimeError):
    """El esquema SQLite no coincide con lo esperado."""


def default_db_path() -> Path:
    import os

    env = os.environ.get("CHEMBL_DB_PATH")
    if env:
        return Path(env)
    return Path("data/external/chembl/chembl_37.db")


def ensure_db_exists(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else default_db_path()
    if not path.is_file():
        raise ChemblDatabaseError(
            f"No se encontró ChEMBLdb en {path}. "
            "Ejecuta: docker compose -f docker/docker-compose.yml --profile setup run chembl-init"
        )
    return path


@contextmanager
def connect_readonly(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _table_map(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    by_lower = {r[0].lower(): r[0] for r in rows}
    resolved: dict[str, str] = {}
    for logical, candidates in _TABLE_CANDIDATES.items():
        for cand in candidates:
            if cand.lower() in by_lower:
                resolved[logical] = by_lower[cand.lower()]
                break
    missing = [k for k in _TABLE_CANDIDATES if k not in resolved]
    if missing:
        raise ChemblSchemaError(f"Tablas no encontradas en ChEMBLdb: {missing}")
    return resolved


def _column_set(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1].lower() for r in rows}


def _pick_column(cols: set[str], *candidates: str) -> str | None:
    for c in candidates:
        if c.lower() in cols:
            return c
    return None


def db_info(db_path: str | Path | None = None) -> dict[str, Any]:
    """Metadatos de la base local (versión, tablas, tamaño)."""
    path = ensure_db_exists(db_path)
    with connect_readonly(path) as conn:
        tables = _table_map(conn)
        version_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'version%'"
        ).fetchone()
        version = None
        if version_row:
            vtable = version_row[0]
            try:
                version = conn.execute(f"SELECT * FROM {vtable} LIMIT 1").fetchone()
            except sqlite3.Error:
                version = None
    manifest_path = path.parent / "manifest.json"
    manifest = None
    if manifest_path.is_file():
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "db_path": str(path),
        "db_size_bytes": path.stat().st_size,
        "tables": tables,
        "manifest": manifest,
        "version_row": dict(version) if version else None,
    }


def resolve_chembl_id_local(
    compound_name: str,
    pubchem_cid: int | str,
    smiles: str,
    conn: sqlite3.Connection,
    tables: dict[str, str] | None = None,
    *,
    use_known_registry: bool = True,
) -> dict[str, Any]:
    """Resuelve ChEMBL ID desde SQLite (sin red)."""
    if use_known_registry and compound_name in KNOWN_MIDA_CHEMBL_IDS:
        chembl_id = KNOWN_MIDA_CHEMBL_IDS[compound_name]
        pref = _fetch_pref_name(conn, chembl_id, tables)
        return _match_result(chembl_id, "known_registry", "ok", 1, pref)

    tables = tables or _table_map(conn)
    md = tables["molecule_dictionary"]
    cs = tables["compound_structures"]
    ms = tables["molecule_synonyms"]

    md_cols = _column_set(conn, md)
    cs_cols = _column_set(conn, cs)
    ms_cols = _column_set(conn, ms)

    chembl_col = _pick_column(md_cols, "chembl_id", "molecule_chembl_id") or "chembl_id"
    pref_col = _pick_column(md_cols, "pref_name") or "pref_name"
    molregno_col = _pick_column(md_cols, "molregno") or "molregno"
    smiles_col = _pick_column(cs_cols, "canonical_smiles") or "canonical_smiles"
    syn_col = _pick_column(ms_cols, "molsynonym", "synonyms", "molecule_synonym") or "molsynonym"

    # SMILES canónico — más fiable para el corpus PubChem (~235 compuestos)
    canon = canonicalize_smiles(smiles)
    if canon:
        row = conn.execute(
            f"""
            SELECT md.{chembl_col}, md.{pref_col}
            FROM {cs} cs
            JOIN {md} md ON cs.{molregno_col} = md.{molregno_col}
            WHERE cs.{smiles_col} = ?
            LIMIT 2
            """,
            (canon,),
        ).fetchall()
        if len(row) == 1:
            return _match_result(row[0][0], "sqlite_smiles", "ok", 1, row[0][1])
        if len(row) > 1:
            return _match_result(row[0][0], "sqlite_smiles", "ambiguous", len(row), row[0][1])

    # pref_name exacto (case-insensitive)
    row = conn.execute(
        f"SELECT {chembl_col}, {pref_col} FROM {md} "
        f"WHERE UPPER({pref_col}) = UPPER(?) LIMIT 2",
        (compound_name,),
    ).fetchall()
    if len(row) == 1:
        return _match_result(row[0][0], "sqlite_pref_name", "ok", 1, row[0][1])
    if len(row) > 1:
        return _match_result(row[0][0], "sqlite_pref_name", "ambiguous", len(row), row[0][1])

    # sinónimo
    row = conn.execute(
        f"""
        SELECT md.{chembl_col}, md.{pref_col}
        FROM {ms} syn
        JOIN {md} md ON syn.{molregno_col} = md.{molregno_col}
        WHERE UPPER(syn.{syn_col}) = UPPER(?)
        LIMIT 2
        """,
        (compound_name,),
    ).fetchall()
    if len(row) == 1:
        return _match_result(row[0][0], "sqlite_synonym", "ok", 1, row[0][1])
    if len(row) > 1:
        return _match_result(row[0][0], "sqlite_synonym", "ambiguous", len(row), row[0][1])

    return {
        "chembl_id": None,
        "match_method": None,
        "match_status": "not_found",
        "n_candidates": 0,
        "chembl_pref_name": None,
    }


def _fetch_pref_name(
    conn: sqlite3.Connection,
    chembl_id: str,
    tables: dict[str, str] | None = None,
) -> str | None:
    tables = tables or _table_map(conn)
    md = tables["molecule_dictionary"]
    md_cols = _column_set(conn, md)
    chembl_col = _pick_column(md_cols, "chembl_id", "molecule_chembl_id") or "chembl_id"
    pref_col = _pick_column(md_cols, "pref_name") or "pref_name"
    row = conn.execute(
        f"SELECT {pref_col} FROM {md} WHERE {chembl_col} = ? LIMIT 1",
        (chembl_id,),
    ).fetchone()
    return row[0] if row else None


def build_mapping_table_local(
    compounds_df: pd.DataFrame,
    db_path: str | Path | None = None,
    *,
    verbose: bool = True,
    existing_mapping_path: str | Path | None = None,
    skip_resolved: bool = True,
) -> pd.DataFrame:
    """Mapeo PubChem/MIDA → ChEMBL desde SQLite."""
    path = ensure_db_exists(db_path)
    existing: dict[str, dict[str, Any]] = {}
    if existing_mapping_path is not None:
        prev = load_mapping_table(existing_mapping_path)
        if prev is not None:
            for _, row in prev.iterrows():
                cid = row.get("chembl_id")
                if pd.notna(cid) and str(cid).strip():
                    key = _mapping_row_key(row)
                    existing[key] = row.to_dict()

    records: list[dict[str, Any]] = []
    with connect_readonly(path) as conn:
        tables = _table_map(conn)
        for _, row in compounds_df.iterrows():
            key = _mapping_row_key(row)
            name = row["compound_name"]
            if skip_resolved and key in existing:
                if verbose:
                    print(f"  {name}: reutilizado ({existing[key].get('chembl_id')})")
                records.append(existing[key])
                continue

            if verbose:
                print(f"  Mapeando (SQLite): {name}")
            match = resolve_chembl_id_local(
                name,
                row["pubchem_cid"],
                row["smiles"],
                conn,
                tables,
            )
            records.append(
                {
                    "compound_name": name,
                    "pubchem_cid": row["pubchem_cid"],
                    "smiles": row["smiles"],
                    "family": row["family"],
                    "chembl_id": match["chembl_id"],
                    "match_method": match["match_method"],
                    "match_status": match["match_status"],
                    "n_candidates": match["n_candidates"],
                    "chembl_pref_name": match["chembl_pref_name"],
                }
            )
    return pd.DataFrame(records)


def _bioactivity_sql(
    tables: dict[str, str],
    conn: sqlite3.Connection,
    *,
    standard_types: tuple[str, ...] | None = None,
) -> str:
    md, cs, cp, act, ass, td = (
        tables["molecule_dictionary"],
        tables["compound_structures"],
        tables["compound_properties"],
        tables["activities"],
        tables["assays"],
        tables["target_dictionary"],
    )

    md_cols = _column_set(conn, md)
    act_cols = _column_set(conn, act)
    ass_cols = _column_set(conn, ass)
    td_cols = _column_set(conn, td)
    cp_cols = _column_set(conn, cp)

    md_chembl = _pick_column(md_cols, "chembl_id", "molecule_chembl_id") or "chembl_id"
    md_molregno = _pick_column(md_cols, "molregno") or "molregno"

    ass_chembl = _pick_column(ass_cols, "assay_chembl_id", "chembl_id") or "chembl_id"
    bao_col = _pick_column(ass_cols, "bao_label", "bao_format")
    bao_sql = f"ass.{bao_col} AS bao_label" if bao_col else "NULL AS bao_label"

    td_chembl = _pick_column(td_cols, "chembl_id", "target_chembl_id") or "chembl_id"
    td_pref = _pick_column(td_cols, "pref_name") or "pref_name"
    td_type = _pick_column(td_cols, "target_type") or "target_type"
    td_org = _pick_column(td_cols, "organism") or "organism"
    ass_type = _pick_column(ass_cols, "assay_type") or "assay_type"

    prop_select = []
    for col in (
        "mw_freebase",
        "alogp",
        "psa",
        "hba",
        "hbd",
        "num_ro5_violations",
        "aromatic_rings",
        "heavy_atoms",
        "rtb",
        "molecular_species",
        "cx_logp",
        "cx_logd",
    ):
        if col in cp_cols:
            prop_select.append(f"cp.{col} AS {col}")
        else:
            prop_select.append(f"NULL AS {col}")
    prop_sql = ",\n        ".join(prop_select)

    stype_filter = ", ".join(f"'{s}'" for s in (standard_types or STANDARD_TYPES))

    return f"""
    SELECT
        md.{md_chembl} AS chembl_id,
        cs.canonical_smiles AS smiles,
        act.activity_id AS activity_id,
        ass.{ass_chembl} AS assay_chembl_id,
        td.{td_chembl} AS target_chembl_id,
        td.{td_pref} AS target_name,
        td.{td_type} AS target_type,
        td.{td_org} AS organism,
        act.standard_type AS standard_type,
        act.standard_value AS standard_value,
        act.standard_units AS standard_units,
        act.standard_relation AS standard_relation,
        act.pchembl_value AS pchembl_value,
        act.activity_comment AS activity_comment,
        act.data_validity_comment AS data_validity_comment,
        act.potential_duplicate AS potential_duplicate,
        ass.{ass_type} AS assay_type,
        {bao_sql},
        {prop_sql}
    FROM {act} act
    INNER JOIN {md} md ON act.molregno = md.{md_molregno}
    LEFT JOIN {cs} cs ON md.{md_molregno} = cs.molregno
    LEFT JOIN {cp} cp ON md.{md_molregno} = cp.molregno
    INNER JOIN {ass} ass ON act.assay_id = ass.assay_id
    LEFT JOIN {td} td ON ass.tid = td.tid
    WHERE md.{md_chembl} IN ({{placeholders}})
      AND act.standard_type IN ({stype_filter})
      AND (act.standard_value IS NOT NULL OR act.pchembl_value IS NOT NULL)
    """


def fetch_activities_local(
    chembl_ids: list[str],
    db_path: str | Path | None = None,
    *,
    standard_types: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Actividades para una lista de ChEMBL IDs."""
    if not chembl_ids:
        return pd.DataFrame()
    path = ensure_db_exists(db_path)
    placeholders = ", ".join("?" for _ in chembl_ids)
    with connect_readonly(path) as conn:
        tables = _table_map(conn)
        sql = _bioactivity_sql(tables, conn, standard_types=standard_types).format(
            placeholders=placeholders
        )
        return pd.read_sql_query(sql, conn, params=chembl_ids)


def build_bioactivity_table_local(
    mapping_df: pd.DataFrame,
    db_path: str | Path | None = None,
    *,
    verbose: bool = True,
    standard_types: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Tabla de bioactividad raw desde SQLite — mismo schema que la API."""
    path = ensure_db_exists(db_path)
    resolved = mapping_df[mapping_df["chembl_id"].notna() & (mapping_df["chembl_id"] != "")]
    if resolved.empty:
        return pd.DataFrame(columns=BIOACTIVITY_COLUMNS)

    chembl_ids = resolved["chembl_id"].astype(str).unique().tolist()
    types = standard_types or STANDARD_TYPES
    if verbose:
        print(f"  Consultando SQLite: {len(chembl_ids)} moléculas, {len(types)} tipos de actividad...")

    act_df = fetch_activities_local(chembl_ids, path, standard_types=types)
    if act_df.empty:
        return pd.DataFrame(columns=BIOACTIVITY_COLUMNS)

    if verbose:
        print(f"  -> {len(act_df):,} registros raw desde ChEMBLdb")

    # Metadatos MIDA por chembl_id
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
        smiles = m["smiles"] if pd.notna(m.get("smiles")) else act.get("smiles")
        if cid not in props_cache:
            props_cache[cid] = resolve_molecule_props(
                str(smiles) if smiles else "",
                str(cid),
                fetch_from_chembl=False,
            )
        rdkit_props = props_cache[cid]

        def _prop(col: str) -> Any:
            val = act.get(col)
            if pd.notna(val):
                return val
            return rdkit_props.get(col)

        rows.append(
            {
                "compound_name": m["compound_name"],
                "pubchem_cid": m["pubchem_cid"],
                "chembl_id": cid,
                "smiles": smiles,
                "family": m["family"],
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
                "mw_freebase": _prop("mw_freebase"),
                "alogp": _prop("alogp"),
                "psa": _prop("psa"),
                "hba": _prop("hba"),
                "hbd": _prop("hbd"),
                "num_ro5_violations": _prop("num_ro5_violations"),
                "aromatic_rings": _prop("aromatic_rings"),
                "heavy_atoms": _prop("heavy_atoms"),
                "rtb": _prop("rtb"),
                "molecular_species": _prop("molecular_species"),
                "cx_logp": _prop("cx_logp"),
                "cx_logd": _prop("cx_logd"),
            }
        )

    df = pd.DataFrame(rows)
    df = derive_activity_class(df, threshold=PCHEMBL_ACTIVE_THRESHOLD)
    return df.reindex(columns=BIOACTIVITY_COLUMNS)
