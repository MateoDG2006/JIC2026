"""Cliente PubChem PUG REST — docs/01_pipeline_datos.md, AGENTS.md (rate limit)."""

from __future__ import annotations

import time
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
from rdkit import Chem

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def _atomic_save_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    """Escritura atómica (WARN-2): evita CSV corrupto si el proceso se interrumpe."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(p)

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

FAMILY_HIDS: dict[str, int] = {
    "Organophosphates": 73,
    "Carbamates": 78,
    "Triazines": 126,
    "Azole_fungicides": 103,
    "Pyrethroids": 112,
    "Herbicides": 90,
}

GHS_HAZARD_CODES: dict[str, str] = {
    "H300": "fatal_oral",
    "H301": "toxic_oral",
    "H302": "harmful_oral",
    "H310": "fatal_dermal",
    "H311": "toxic_dermal",
    "H312": "harmful_dermal",
    "H330": "fatal_inhalation",
    "H331": "toxic_inhalation",
    "H360": "reproductive_cat1",
    "H361": "reproductive_cat2",
    "H362": "lactation_hazard",
    "H340": "mutagenic_cat1",
    "H341": "mutagenic_cat2",
    "H350": "carcinogenic_cat1",
    "H351": "carcinogenic_cat2",
    "H400": "aquatic_acute_cat1",
    "H410": "aquatic_chronic_cat1",
    "H411": "aquatic_chronic_cat2",
    "H412": "aquatic_chronic_cat3",
}

MIDA_ACTIVE_INGREDIENTS: list[str] = [
    "Chlorpyrifos",
    "Malathion",
    "Dimethoate",
    "Methyl parathion",
    "Carbaryl",
    "Methomyl",
    "Aldicarb",
    "Atrazine",
    "Simazine",
    "Tebuconazole",
    "Propiconazole",
    "Difenoconazole",
    "Cypermethrin",
    "Deltamethrin",
    "Lambda-cyhalothrin",
    "Glyphosate",
    "Paraquat",
    "2,4-D",
    "Mancozeb",
    "Chlorothalonil",
]


def fetch_bioassay_data(aid: int, task_name: str) -> pd.DataFrame:
    url = f"{BASE}/bioassay/AID/{aid}/CSV"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    df = df.rename(
        columns={
            "PUBCHEM_CID": "CID",
            "PUBCHEM_ACTIVITY_OUTCOME": "activity_raw",
        }
    )
    df["activity"] = df["activity_raw"].map({"Active": 1, "Inactive": 0})
    df["task"] = task_name
    df["AID"] = aid
    time.sleep(0.35)
    return df[["CID", "task", "AID", "activity"]].dropna()


def build_tox21_from_pubchem(output_path: str = "data/raw/pubchem_tox21_aids.csv") -> pd.DataFrame:
    all_dfs: list[pd.DataFrame] = []
    for task, aid in TOX21_AIDS.items():
        df = fetch_bioassay_data(aid, task)
        all_dfs.append(df)
    result = pd.concat(all_dfs, ignore_index=True)
    _atomic_save_dataframe(result, output_path)
    return result


def fetch_classification_cids(hid: int) -> list[int]:
    url = f"{BASE}/classification/hid/{hid}/cids/JSON"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    time.sleep(0.5)
    return data.get("IdentifierList", {}).get("CID", [])


def fetch_smiles_batch(cids: list[int], batch_size: int = 100) -> dict[int, str]:
    smiles_map: dict[int, str] = {}
    for i in range(0, len(cids), batch_size):
        batch = cids[i : i + batch_size]
        cid_str = ",".join(map(str, batch))
        url = f"{BASE}/compound/cid/{cid_str}/property/CanonicalSMILES/JSON"
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            for prop in resp.json()["PropertyTable"]["Properties"]:
                smiles_map[prop["CID"]] = prop["CanonicalSMILES"]
        except Exception as e:
            print(f"[WARN] fetch_smiles_batch lote {i // batch_size} ({len(batch)} CIDs): {e}")
        time.sleep(0.4)
    return smiles_map


def build_panama_cid_list(output_path: str = "data/raw/pubchem_panama_cids.csv") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in MIDA_ACTIVE_INGREDIENTS:
        url = (
            f"{BASE}/compound/name/{quote(name, safe='')}/property/"
            "CanonicalSMILES,IUPACName,MolecularFormula/JSON"
        )
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                props = resp.json()["PropertyTable"]["Properties"][0]
                rows.append(
                    {
                        "name": name,
                        "CID": props["CID"],
                        "SMILES": props["CanonicalSMILES"],
                        "formula": props.get("MolecularFormula", ""),
                        "source": "MIDA_name_search",
                        "family": "mixed",
                    }
                )
        except Exception as e:
            print(f"[WARN] PubChem compound/name '{name}': {e}")
        time.sleep(0.35)

    for family, hid in FAMILY_HIDS.items():
        try:
            cids = fetch_classification_cids(hid)[:50]
            for cid in cids:
                rows.append(
                    {
                        "name": "",
                        "CID": cid,
                        "SMILES": "",
                        "formula": "",
                        "source": f"classification_hid_{hid}",
                        "family": family,
                    }
                )
        except Exception as e:
            print(f"[WARN] PubChem classification hid={hid}: {e}")

    df = pd.DataFrame(rows).drop_duplicates(subset=["CID"])
    _atomic_save_dataframe(df, output_path)
    return df


def enrich_corpus_with_smiles(corpus_path: str) -> pd.DataFrame:
    df = pd.read_csv(corpus_path)
    missing = df[df["SMILES"].fillna("") == ""]["CID"].tolist()
    if missing:
        smap = fetch_smiles_batch([int(x) for x in missing])
        df.loc[df["SMILES"].fillna("") == "", "SMILES"] = df["CID"].map(smap)

    def validate_smiles(smi: object) -> str | None:
        if not isinstance(smi, str) or not smi:
            return None
        mol = Chem.MolFromSmiles(smi)
        return Chem.MolToSmiles(mol) if mol else None

    df["SMILES_canonical"] = df["SMILES"].apply(validate_smiles)
    df = df.dropna(subset=["SMILES_canonical"])
    _atomic_save_dataframe(df, corpus_path)
    return df


def fetch_ghs_labels(cids: list[int], output_path: str = "data/raw/pubchem_ghs_labels.csv") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cid in cids:
        url = f"{BASE}/compound/cid/{cid}/JSON"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            ghs_codes: list[str] = []
            sections = data.get("Record", {}).get("Section", [])
            for sec in sections:
                if sec.get("TOCHeading") == "Safety and Hazards":
                    for subsec in sec.get("Section", []):
                        if "GHS" in subsec.get("TOCHeading", ""):
                            for info in subsec.get("Information", []):
                                for val in info.get("Value", {}).get("StringWithMarkup", []):
                                    text = val.get("String", "")
                                    for code in GHS_HAZARD_CODES:
                                        if code in text:
                                            ghs_codes.append(code)
            rows.append(
                {
                    "CID": cid,
                    "ghs_codes": "|".join(sorted(set(ghs_codes))),
                    "toxic_oral": int(any(c in ghs_codes for c in ["H300", "H301", "H302"])),
                    "endocrine_risk": int(any(c in ghs_codes for c in ["H360", "H361"])),
                    "genotoxic": int(any(c in ghs_codes for c in ["H340", "H341", "H350", "H351"])),
                    "aquatic_tox": int(
                        any(c in ghs_codes for c in ["H400", "H410", "H411", "H412"])
                    ),
                }
            )
        except Exception as e:
            print(f"[WARN] PubChem GHS CID {cid}: {e}")
            rows.append(
                {
                    "CID": cid,
                    "ghs_codes": "",
                    "toxic_oral": 0,
                    "endocrine_risk": 0,
                    "genotoxic": 0,
                    "aquatic_tox": 0,
                }
            )
        time.sleep(0.35)

    out = pd.DataFrame(rows)
    _atomic_save_dataframe(out, output_path)
    return out


def build_full_panama_corpus() -> pd.DataFrame:
    df = build_panama_cid_list()
    df = enrich_corpus_with_smiles("data/raw/pubchem_panama_cids.csv")
    cids = df["CID"].tolist()
    fetch_ghs_labels(cids)
    return df
