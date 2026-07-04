"""
Utilidades compartidas para extracción ChEMBL offline (SQLite).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski

from src.analisis_proyecto.core.constants import pchembl_active_threshold
from src.analisis_proyecto.core.models import (
    ConcentrationUnits,
    CorpusCompound,
    MidaRegistry,
    MolecularProperties,
    QualityFilterConfig,
)


class SmilesCanonicalizer:
    @staticmethod
    def canonicalize(smiles: str) -> str | None:
        if not isinstance(smiles, str) or not smiles.strip():
            return None
        mol = Chem.MolFromSmiles(smiles)
        return Chem.MolToSmiles(mol) if mol else None

    @classmethod
    def normalize_column(cls, df: pd.DataFrame) -> pd.Series:
        smiles_col = "SMILES_canonical" if "SMILES_canonical" in df.columns else "SMILES"
        raw = df[smiles_col].fillna(df.get("SMILES", ""))
        return raw.apply(lambda s: cls.canonicalize(s) or (s if isinstance(s, str) else ""))


class MolecularPropertyCalculator:
    @staticmethod
    def from_smiles(smiles: str) -> MolecularProperties:
        mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
        if mol is None:
            return MolecularProperties()
        violations = sum([
            Descriptors.MolWt(mol) > 500,
            Crippen.MolLogP(mol) > 5,
            Lipinski.NumHDonors(mol) > 5,
            Lipinski.NumHAcceptors(mol) > 10,
        ])
        return MolecularProperties(
            mw_freebase=Descriptors.MolWt(mol),
            alogp=Crippen.MolLogP(mol),
            psa=Descriptors.TPSA(mol),
            hba=Lipinski.NumHAcceptors(mol),
            hbd=Lipinski.NumHDonors(mol),
            num_ro5_violations=violations,
            aromatic_rings=Lipinski.NumAromaticRings(mol),
            heavy_atoms=Lipinski.HeavyAtomCount(mol),
            rtb=Lipinski.NumRotatableBonds(mol),
        )

    @classmethod
    def resolve(cls, smiles: str, chembl_id: str | None = None, **_) -> MolecularProperties:
        _ = chembl_id
        return cls.from_smiles(smiles)


class CorpusLoader:
    def __init__(self, registry: MidaRegistry | None = None) -> None:
        self.registry = registry or MidaRegistry()

    def load(self, corpus_path: str | Path) -> pd.DataFrame:
        """Carga todos los compuestos de PubChem con SMILES válido (~235 candidatos)."""
        df = pd.read_csv(corpus_path)
        work = df.copy()
        work["smiles"] = SmilesCanonicalizer.normalize_column(work)
        valid = work[work["smiles"].notna() & (work["smiles"].astype(str).str.strip() != "")].copy()

        compounds: list[CorpusCompound] = []
        for _, row in valid.iterrows():
            name = row.get("name")
            compound_name = str(name).strip() if pd.notna(name) and str(name).strip() else f"CID_{int(row['CID'])}"
            family = (
                self.registry.family(compound_name)
                if self.registry.contains(compound_name)
                else str(row.get("family", "unknown") or "unknown")
            )
            compounds.append(
                CorpusCompound(
                    compound_name=compound_name,
                    pubchem_cid=int(row["CID"]),
                    smiles=str(row["smiles"]),
                    family=family,
                    source=str(row.get("source", "unknown") or "unknown"),
                    is_mida=self.registry.contains(compound_name),
                )
            )
        return pd.DataFrame([c.to_dict() for c in compounds])


class MappingTableStore:
    @staticmethod
    def load(path: str | Path) -> pd.DataFrame | None:
        p = Path(path)
        return pd.read_csv(p) if p.exists() else None

    @staticmethod
    def index_resolved(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        if df.empty:
            return {}
        resolved = df[
            df["chembl_id"].notna() & df["chembl_id"].astype(str).str.strip().ne("")
        ].copy()
        if resolved.empty:
            return {}
        records = json.loads(resolved.to_json(orient="records", date_format="iso"))
        return {str(row["pubchem_cid"]): row for row in records}


class PchemblImputer:
    @staticmethod
    def from_standard_value(value: float | int | str | None, units: str | None) -> float | None:
        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if numeric <= 0 or not units:
            return None
        factor = ConcentrationUnits.molar_factor(units)
        return -math.log10(numeric * factor) if factor else None

    @classmethod
    def impute_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if "pchembl_imputed" not in out.columns:
            out["pchembl_imputed"] = False
        pchembl = pd.to_numeric(out["pchembl_value"], errors="coerce")
        relation = out["standard_relation"].fillna("").astype(str)
        missing = pchembl.isna() & (relation == "=")
        if not missing.any():
            return out
        computed = out.loc[missing].apply(
            lambda r: cls.from_standard_value(r.get("standard_value"), r.get("standard_units")),
            axis=1,
        )
        imputed_mask = missing & computed.notna()
        out.loc[imputed_mask, "pchembl_value"] = computed[computed.notna()]
        out.loc[imputed_mask, "pchembl_imputed"] = True
        return out


class ActivityClassAssigner:
    @staticmethod
    def assign(df: pd.DataFrame, threshold: float | None = None) -> pd.DataFrame:
        threshold = pchembl_active_threshold() if threshold is None else threshold
        out = df.copy()
        pchembl = pd.to_numeric(out["pchembl_value"], errors="coerce")
        out["activity_class"] = pd.Series(pd.NA, index=out.index, dtype="object")
        out.loc[pchembl >= threshold, "activity_class"] = "Active"
        out.loc[pchembl < threshold, "activity_class"] = "Inactive"
        return out


class QualityFilterPipeline:
    def __init__(self, config: QualityFilterConfig | None = None) -> None:
        self.config = config or QualityFilterConfig()

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        work = PchemblImputer.impute_dataframe(df) if self.config.impute_pchembl else df.copy()
        n_start = len(work)
        rules: list[tuple[str, pd.Series]] = [
            ("pchembl_value nulo (tras imputación)", work["pchembl_value"].isna()),
        ]
        if self.config.require_exact_relation:
            rules.append(
                ("standard_relation != '='", work["standard_relation"].fillna("").astype(str) != "=")
            )
        if self.config.exclude_validity_comment:
            rules.append((
                "data_validity_comment no nulo",
                work["data_validity_comment"].notna()
                & (work["data_validity_comment"].astype(str).str.strip() != ""),
            ))

        stats: list[dict[str, Any]] = []
        excluded_mask = pd.Series(False, index=work.index)
        for label, mask in rules:
            n_flagged = int(mask.sum())
            stats.append({
                "filtro": label,
                "registros_afectados": n_flagged,
                "pct_del_total": round(100 * n_flagged / n_start, 2) if n_start else 0.0,
            })
            excluded_mask |= mask

        clean = work.loc[~excluded_mask].copy()
        stats.extend([
            {
                "filtro": "TOTAL excluidos (unión de reglas)",
                "registros_afectados": int(excluded_mask.sum()),
                "pct_del_total": round(100 * excluded_mask.sum() / n_start, 2) if n_start else 0.0,
            },
            {
                "filtro": "TOTAL conservados",
                "registros_afectados": len(clean),
                "pct_del_total": round(100 * len(clean) / n_start, 2) if n_start else 0.0,
            },
        ])
        stats_df = pd.DataFrame(stats)
        stats_df.attrs["n_raw"] = n_start
        stats_df.attrs["n_clean"] = len(clean)
        return clean, stats_df


class ExtractionSummarizer:
    @staticmethod
    def summarize(
        compounds_df: pd.DataFrame,
        mapping_df: pd.DataFrame,
        raw_df: pd.DataFrame,
        clean_df: pd.DataFrame,
    ) -> pd.DataFrame:
        rows = []
        for _, comp in compounds_df.iterrows():
            name = comp["compound_name"]
            map_row = mapping_df.loc[mapping_df["compound_name"] == name].iloc[0]
            n_raw = len(raw_df[raw_df["compound_name"] == name]) if len(raw_df) else 0
            n_clean = len(clean_df[clean_df["compound_name"] == name]) if len(clean_df) else 0
            rows.append({
                "compound_name": name,
                "family": comp["family"],
                "chembl_id": map_row["chembl_id"],
                "match_status": map_row["match_status"],
                "n_activities_raw": n_raw,
                "n_activities_clean": n_clean,
            })
        return pd.DataFrame(rows)
