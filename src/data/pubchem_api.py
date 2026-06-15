"""
Cliente para la API PubChem PUG REST.

Se usa para construir el corpus de plaguicidas panameños (Fase V):
  1. Classification (HID 72): obtener CIDs de familias de plaguicidas
  2. Compound: descargar SMILES canónicos para cada CID
  3. BioAssay: descargar datos de los 12 ensayos Tox21 (trazabilidad)
  4. Hazard GHS: etiquetas de peligro para validación externa

IMPORTANTE: Este módulo NO se usa para entrenar el modelo.
El entrenamiento usa DeepChem (scripts/prepare_tox21_graphs.py).
Este módulo construye un corpus aparte de plaguicidas de Panamá
para evaluarlos con el modelo ya entrenado.
"""

from __future__ import annotations

import time
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
from rdkit import Chem

# URL base de la API PUG REST de PubChem
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Máximo de reintentos para llamadas HTTP que fallen
MAX_RETRIES = 3
RETRY_DELAY = 2.0


def _get_with_retry(url: str, timeout: int = 60) -> requests.Response:
    """Hace un GET con reintentos automáticos ante fallos de red."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.RequestException, requests.HTTPError) as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"  [RETRY] intento {attempt + 1}/{MAX_RETRIES} falló: {e}. "
                      f"Reintentando en {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise


def _atomic_save_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    """Guarda CSV de forma atómica: escribe a .tmp y renombra.
    Evita CSVs corruptos si el proceso se interrumpe a medio escribir."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(p)


# ── AIDs oficiales de los 12 ensayos Tox21 en PubChem BioAssay ───────────
# Cada AID corresponde a un ensayo biológico publicado por el NIH.
TOX21_AIDS: dict[str, int] = {
    "NR-AR": 720637,
    "NR-AR-LBD": 743035,
    "NR-AhR": 743122,
    "NR-Aromatase": 743139,
    "NR-ER": 743040,
    "NR-ER-LBD": 743042,
    "NR-PPAR-gamma": 743140,
    "SR-ARE": 743219,
    "SR-AtAD5": 743221,
    "SR-HSE": 743226,
    "SR-MMP": 743240,
    "SR-p53": 743241,
}

# ── Familias de plaguicidas en el árbol PubChem Classification ────────────
# HID = Hierarchy ID. El nodo raíz es HID 72 ("Pesticides").
FAMILY_HIDS: dict[str, int] = {
    "Organophosphates": 73,
    "Carbamates": 78,
    "Triazines": 126,
    "Azole_fungicides": 103,
    "Pyrethroids": 112,
    "Herbicides": 90,
}

# ── Códigos GHS de peligro (para validación externa) ─────────────────────
GHS_HAZARD_CODES: dict[str, str] = {
    "H300": "fatal_oral", "H301": "toxic_oral", "H302": "harmful_oral",
    "H310": "fatal_dermal", "H311": "toxic_dermal", "H312": "harmful_dermal",
    "H330": "fatal_inhalation", "H331": "toxic_inhalation",
    "H360": "reproductive_cat1", "H361": "reproductive_cat2",
    "H362": "lactation_hazard",
    "H340": "mutagenic_cat1", "H341": "mutagenic_cat2",
    "H350": "carcinogenic_cat1", "H351": "carcinogenic_cat2",
    "H400": "aquatic_acute_cat1", "H410": "aquatic_chronic_cat1",
    "H411": "aquatic_chronic_cat2", "H412": "aquatic_chronic_cat3",
}

# ── Ingredientes activos registrados en el MIDA (Panamá) ─────────────────
MIDA_ACTIVE_INGREDIENTS: list[str] = [
    "Chlorpyrifos", "Malathion", "Dimethoate", "Methyl parathion",
    "Carbaryl", "Methomyl", "Aldicarb",
    "Atrazine", "Simazine",
    "Tebuconazole", "Propiconazole", "Difenoconazole",
    "Cypermethrin", "Deltamethrin", "Lambda-cyhalothrin",
    "Glyphosate", "Paraquat", "2,4-D", "Mancozeb", "Chlorothalonil",
]


# ── PASO 1: PubChem BioAssay — datos Tox21 con trazabilidad ──────────────

def fetch_bioassay_data(aid: int, task_name: str) -> pd.DataFrame:
    """Descarga resultados de un ensayo PubChem BioAssay.

    Args:
        aid: ID del ensayo (ej: 720637 para NR-AR)
        task_name: nombre de la tarea (ej: "NR-AR")

    Returns:
        DataFrame con columnas: CID, task, AID, activity (1=Active, 0=Inactive)
    """
    url = f"{BASE}/bioassay/AID/{aid}/CSV"
    resp = _get_with_retry(url)
    df = pd.read_csv(StringIO(resp.text))
    df = df.rename(columns={
        "PUBCHEM_CID": "CID",
        "PUBCHEM_ACTIVITY_OUTCOME": "activity_raw",
    })
    df["activity"] = df["activity_raw"].map({"Active": 1, "Inactive": 0})
    df["task"] = task_name
    df["AID"] = aid
    time.sleep(0.35)
    return df[["CID", "task", "AID", "activity"]].dropna()


def build_tox21_from_pubchem(
    output_path: str = "data/raw/pubchem_tox21_aids.csv",
) -> pd.DataFrame:
    """Descarga y concatena los 12 ensayos Tox21 desde PubChem BioAssay."""
    all_dfs: list[pd.DataFrame] = []
    for task, aid in TOX21_AIDS.items():
        print(f"  Descargando {task} (AID {aid})...")
        df = fetch_bioassay_data(aid, task)
        all_dfs.append(df)
    result = pd.concat(all_dfs, ignore_index=True)
    _atomic_save_dataframe(result, output_path)
    print(f"Guardado: {output_path} ({len(result)} registros)")
    return result


# ── PASO 2: PubChem Classification — CIDs de familias de plaguicidas ─────

def fetch_classification_cids(hid: int) -> list[int]:
    """Obtiene todos los CIDs bajo un nodo del árbol de clasificación."""
    url = f"{BASE}/classification/hid/{hid}/cids/JSON"
    resp = _get_with_retry(url)
    data = resp.json()
    time.sleep(0.5)
    return data.get("IdentifierList", {}).get("CID", [])


# ── PASO 3: PubChem Compound — SMILES canónicos ──────────────────────────

def fetch_smiles_batch(cids: list[int], batch_size: int = 100) -> dict[int, str]:
    """Descarga SMILES canónicos para una lista de CIDs en lotes.

    PubChem acepta hasta ~100 CIDs por request en la URL.

    Returns:
        Diccionario {CID: SMILES_canónico}
    """
    smiles_map: dict[int, str] = {}
    for i in range(0, len(cids), batch_size):
        batch = cids[i : i + batch_size]
        cid_str = ",".join(map(str, batch))
        url = f"{BASE}/compound/cid/{cid_str}/property/CanonicalSMILES/JSON"
        try:
            resp = _get_with_retry(url)
            for prop in resp.json()["PropertyTable"]["Properties"]:
                smiles_map[prop["CID"]] = prop["CanonicalSMILES"]
        except Exception as e:
            print(f"[WARN] fetch_smiles_batch lote {i // batch_size} "
                  f"({len(batch)} CIDs): {e}")
        time.sleep(0.4)
    return smiles_map


# ── PASO 4: Construir corpus panameño ─────────────────────────────────────

def build_panama_cid_list(
    output_path: str = "data/raw/pubchem_panama_cids.csv",
) -> pd.DataFrame:
    """Construye la lista de CIDs de plaguicidas relevantes para Panamá.

    Dos fuentes:
      1. Búsqueda por nombre: ingredientes activos del MIDA
      2. Árbol de clasificación: familias de plaguicidas (HID 72)
    """
    rows: list[dict[str, Any]] = []

    # Fuente 1: buscar cada ingrediente activo por nombre
    for name in MIDA_ACTIVE_INGREDIENTS:
        url = (
            f"{BASE}/compound/name/{quote(name, safe='')}/property/"
            "CanonicalSMILES,IUPACName,MolecularFormula/JSON"
        )
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                props = resp.json()["PropertyTable"]["Properties"][0]
                rows.append({
                    "name": name,
                    "CID": props["CID"],
                    "SMILES": props["CanonicalSMILES"],
                    "formula": props.get("MolecularFormula", ""),
                    "source": "MIDA_name_search",
                    "family": "mixed",
                })
        except Exception as e:
            print(f"[WARN] PubChem compound/name '{name}': {e}")
        time.sleep(0.35)

    # Fuente 2: familias del árbol de clasificación
    for family, hid in FAMILY_HIDS.items():
        try:
            cids = fetch_classification_cids(hid)[:50]
            for cid in cids:
                rows.append({
                    "name": "",
                    "CID": cid,
                    "SMILES": "",
                    "formula": "",
                    "source": f"classification_hid_{hid}",
                    "family": family,
                })
        except Exception as e:
            print(f"[WARN] PubChem classification hid={hid}: {e}")

    df = pd.DataFrame(rows).drop_duplicates(subset=["CID"])
    _atomic_save_dataframe(df, output_path)
    print(f"Corpus inicial: {len(df)} compuestos en {output_path}")
    return df


def enrich_corpus_with_smiles(corpus_path: str) -> pd.DataFrame:
    """Completa los SMILES vacíos descargándolos desde PubChem Compound."""
    df = pd.read_csv(corpus_path)
    missing_mask = df["SMILES"].fillna("") == ""
    missing_cids = df.loc[missing_mask, "CID"].tolist()

    if missing_cids:
        print(f"Descargando SMILES para {len(missing_cids)} CIDs...")
        smap = fetch_smiles_batch([int(x) for x in missing_cids])
        # Usar .loc para evitar SettingWithCopyWarning
        df.loc[missing_mask, "SMILES"] = df.loc[missing_mask, "CID"].map(smap)

    # Validar y canonicalizar con RDKit
    def validate_smiles(smi: object) -> str | None:
        if not isinstance(smi, str) or not smi:
            return None
        mol = Chem.MolFromSmiles(smi)
        return Chem.MolToSmiles(mol) if mol else None

    df["SMILES_canonical"] = df["SMILES"].apply(validate_smiles)
    df = df.dropna(subset=["SMILES_canonical"])
    _atomic_save_dataframe(df, corpus_path)
    print(f"Corpus enriquecido: {len(df)} moléculas válidas")
    return df


# ── PASO 5: PubChem Hazard (GHS) — etiquetas para validación ─────────────

def fetch_ghs_labels(
    cids: list[int],
    output_path: str = "data/raw/pubchem_ghs_labels.csv",
) -> pd.DataFrame:
    """Descarga etiquetas GHS (H-statements) para cada CID.

    Estas etiquetas son de VALIDACIÓN EXTERNA — NO se usan para entrenar.
    Sirven para verificar que las predicciones del modelo correlacionan
    con los peligros documentados por reguladores.

    Correlaciones esperadas:
      H300/H301/H302 (tóxico oral) → SR-ARE, SR-MMP
      H360/H361 (reproductivo) → NR-AR, NR-ER
      H340/H350 (mutagénico/carcinogénico) → SR-p53, SR-AtAD5
    """
    rows: list[dict[str, Any]] = []
    for cid in cids:
        url = f"{BASE}/compound/cid/{cid}/JSON"
        try:
            resp = _get_with_retry(url, timeout=30)
            data = resp.json()
            ghs_codes: list[str] = []

            # Navegar la estructura JSON anidada de PubChem
            sections = data.get("Record", {}).get("Section", [])
            for sec in sections:
                if sec.get("TOCHeading") == "Safety and Hazards":
                    for subsec in sec.get("Section", []):
                        if "GHS" in subsec.get("TOCHeading", ""):
                            for info in subsec.get("Information", []):
                                for val in info.get("Value", {}).get(
                                    "StringWithMarkup", []
                                ):
                                    text = val.get("String", "")
                                    for code in GHS_HAZARD_CODES:
                                        if code in text:
                                            ghs_codes.append(code)
            rows.append({
                "CID": cid,
                "ghs_codes": "|".join(sorted(set(ghs_codes))),
                "toxic_oral": int(
                    any(c in ghs_codes for c in ["H300", "H301", "H302"])
                ),
                "endocrine_risk": int(
                    any(c in ghs_codes for c in ["H360", "H361"])
                ),
                "genotoxic": int(
                    any(c in ghs_codes for c in ["H340", "H341", "H350", "H351"])
                ),
                "aquatic_tox": int(
                    any(c in ghs_codes for c in ["H400", "H410", "H411", "H412"])
                ),
            })
        except Exception as e:
            print(f"[WARN] PubChem GHS CID {cid}: {e}")
            rows.append({
                "CID": cid, "ghs_codes": "",
                "toxic_oral": 0, "endocrine_risk": 0,
                "genotoxic": 0, "aquatic_tox": 0,
            })
        time.sleep(0.35)

    out = pd.DataFrame(rows)
    _atomic_save_dataframe(out, output_path)
    print(f"Etiquetas GHS guardadas: {len(out)} compuestos en {output_path}")
    return out


# ── Pipeline completo ─────────────────────────────────────────────────────

def build_full_panama_corpus() -> pd.DataFrame:
    """Ejecuta los 3 pasos del pipeline de corpus panameño:
      1. Classification HID 72 → lista de CIDs por familia
      2. Compound API → SMILES canónicos verificados
      3. Hazard GHS → etiquetas de toxicidad regulatoria
    """
    print("=== Paso 1: PubChem Classification (HID 72) ===")
    df = build_panama_cid_list()

    print("\n=== Paso 2: PubChem Compound (SMILES canónicos) ===")
    df = enrich_corpus_with_smiles("data/raw/pubchem_panama_cids.csv")

    print("\n=== Paso 3: PubChem Hazard GHS ===")
    cids = df["CID"].tolist()
    fetch_ghs_labels(cids)

    print(f"\n=== Corpus panameño completo: {len(df)} compuestos ===")
    return df


if __name__ == "__main__":
    build_full_panama_corpus()
