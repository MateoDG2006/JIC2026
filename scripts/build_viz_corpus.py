#!/usr/bin/env python3
"""
Genera archivos JSON pre-computados en viz/data/ para el dashboard.

Uso:
    python scripts/build_viz_corpus.py           # requiere modelo entrenado
    python scripts/build_viz_corpus.py --demo    # datos demo sin modelo (UI)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from viz.config import CORPUS_DIR, TASK_NAMES  # noqa: E402
from viz.services.molecule import (  # noqa: E402
    atom_symbols,
    molecular_properties,
    smiles_to_mol_block,
)

PANAMA_PESTICIDES = [
    {
        "id": "chlorpyrifos",
        "name": "Clorpirifos",
        "smiles": "CCOP(=S)(OCC)Oc1nc(Cl)c(Cl)cc1Cl",
        "family": "Organofosforados",
    },
    {
        "id": "atrazine",
        "name": "Atrazina",
        "smiles": "Cc1nc(Cl)c(nc1N(C)C)N(C)C",
        "family": "Triazinas",
    },
    {
        "id": "tebuconazole",
        "name": "Tebuconazol",
        "smiles": "CC(C)(C)c1nc(cs1)C(O)C(Cl)Cc2ccc(F)cc2",
        "family": "Fungicidas azólicos",
    },
    {
        "id": "cypermethrin",
        "name": "Cipermetrina",
        "smiles": "CC1(C)C(C=C(Cl)Cl)C1C(=O)OCc2ccc(OCC3(C)OC3(C)C)cc2",
        "family": "Piretroides",
    },
    {
        "id": "glyphosate",
        "name": "Glifosato",
        "smiles": "N(CC(=O)O)C(=O)P(=O)(O)O",
        "family": "Herbicidas",
    },
    {
        "id": "carbaryl",
        "name": "Carbaril",
        "smiles": "CC(=O)Oc1cccc2ccccc12",
        "family": "Carbamatos",
    },
    {
        "id": "malathion",
        "name": "Malatión",
        "smiles": "CCOC(=O)CC(S(=O)C(=O)OC)C(=O)OCC",
        "family": "Organofosforados",
    },
    {
        "id": "mancozeb",
        "name": "Mancozeb",
        "smiles": "CSc1ncnc2ncnc12",
        "family": "Fungicidas",
    },
]

# Perfiles demo orientativos (solo para --demo, no son predicciones reales)
DEMO_PREDICTIONS: dict[str, dict[str, float]] = {
    "chlorpyrifos": {
        "SR-ARE": 0.82, "NR-AhR": 0.71, "SR-MMP": 0.55, "NR-AR": 0.38,
        "NR-ER": 0.32, "SR-p53": 0.28, "NR-AR-LBD": 0.25, "NR-ER-LBD": 0.22,
        "NR-Aromatase": 0.18, "NR-PPAR-gamma": 0.15, "SR-AtAD5": 0.12, "SR-HSE": 0.10,
    },
    "atrazine": {
        "NR-AR": 0.88, "NR-ER": 0.85, "NR-ER-LBD": 0.79, "NR-Aromatase": 0.62,
        "NR-AR-LBD": 0.58, "NR-PPAR-gamma": 0.45, "SR-ARE": 0.35, "SR-p53": 0.22,
        "SR-MMP": 0.18, "SR-AtAD5": 0.15, "SR-HSE": 0.12, "NR-AhR": 0.10,
    },
    "tebuconazole": {
        "NR-Aromatase": 0.91, "NR-PPAR-gamma": 0.68, "SR-AtAD5": 0.52, "SR-p53": 0.48,
        "NR-AhR": 0.42, "SR-ARE": 0.35, "NR-AR": 0.28, "NR-ER": 0.25,
        "NR-AR-LBD": 0.20, "NR-ER-LBD": 0.18, "SR-MMP": 0.15, "SR-HSE": 0.12,
    },
    "cypermethrin": {
        "SR-HSE": 0.78, "SR-MMP": 0.72, "SR-ARE": 0.55, "NR-AhR": 0.42,
        "SR-p53": 0.35, "NR-AR": 0.28, "NR-ER": 0.22, "SR-AtAD5": 0.20,
        "NR-AR-LBD": 0.18, "NR-ER-LBD": 0.15, "NR-Aromatase": 0.12, "NR-PPAR-gamma": 0.10,
    },
    "glyphosate": {
        "SR-ARE": 0.65, "SR-MMP": 0.48, "NR-PPAR-gamma": 0.35, "SR-p53": 0.28,
        "NR-AhR": 0.22, "NR-AR": 0.18, "NR-ER": 0.15, "SR-AtAD5": 0.12,
        "NR-AR-LBD": 0.10, "NR-ER-LBD": 0.10, "NR-Aromatase": 0.08, "SR-HSE": 0.08,
    },
    "carbaryl": {
        "NR-ER": 0.72, "NR-ER-LBD": 0.68, "NR-AR": 0.55, "SR-ARE": 0.48,
        "SR-MMP": 0.42, "NR-AhR": 0.35, "SR-p53": 0.28, "NR-AR-LBD": 0.22,
        "NR-Aromatase": 0.18, "NR-PPAR-gamma": 0.15, "SR-AtAD5": 0.12, "SR-HSE": 0.10,
    },
    "malathion": {
        "SR-ARE": 0.75, "SR-MMP": 0.62, "NR-AhR": 0.48, "SR-p53": 0.35,
        "NR-AR": 0.28, "NR-ER": 0.25, "SR-AtAD5": 0.22, "NR-AR-LBD": 0.18,
        "NR-ER-LBD": 0.15, "NR-Aromatase": 0.12, "NR-PPAR-gamma": 0.10, "SR-HSE": 0.08,
    },
    "mancozeb": {
        "SR-p53": 0.80, "SR-AtAD5": 0.75, "SR-ARE": 0.58, "NR-AhR": 0.45,
        "SR-MMP": 0.38, "NR-AR": 0.28, "NR-ER": 0.22, "SR-HSE": 0.20,
        "NR-AR-LBD": 0.18, "NR-ER-LBD": 0.15, "NR-Aromatase": 0.12, "NR-PPAR-gamma": 0.10,
    },
}


def _demo_importance(n_atoms: int, seed: int = 0) -> list[float]:
    """Genera importancias demo con picos en algunos átomos."""
    import numpy as np

    rng = np.random.default_rng(seed)
    base = rng.uniform(0.05, 0.25, size=n_atoms)
    peaks = rng.choice(n_atoms, size=min(3, n_atoms), replace=False)
    for p in peaks:
        base[p] = rng.uniform(0.7, 1.0)
    base = (base - base.min()) / (base.max() - base.min() + 1e-8)
    return [float(round(v, 4)) for v in base]


def build_compound(entry: dict, demo: bool = False) -> dict | None:
    smiles = entry["smiles"]
    props = molecular_properties(smiles)
    if props is None:
        print(f"  SKIP {entry['name']}: SMILES invalido")
        return None

    canon = props["canonical_smiles"]
    symbols = atom_symbols(canon)
    mol_block = smiles_to_mol_block(canon)

    record: dict = {
        "name": entry["name"],
        "smiles": canon,
        "family": entry.get("family", ""),
        "properties": props,
        "atom_symbols": symbols,
        "mol_block": mol_block,
        "demo": demo,
    }

    if demo:
        preds = DEMO_PREDICTIONS.get(entry["id"], {})
        for t in TASK_NAMES:
            preds.setdefault(t, 0.1)
        record["predictions"] = {k: round(v, 4) for k, v in preds.items()}
        top_task = max(record["predictions"], key=record["predictions"].get)
        record["top_task"] = top_task

        n = len(symbols)
        seed = sum(ord(c) for c in entry["id"])
        gc_imp = _demo_importance(n, seed)
        ge_imp = _demo_importance(n, seed + 1)
        from src.xai.visualizer import importance_to_hex_colors
        import numpy as np

        record["xai"] = {
            "gradcam": {top_task: gc_imp},
            "gnnexplainer": {top_task: ge_imp},
        }
        record["xai_colors"] = {
            "gradcam": {top_task: importance_to_hex_colors(np.array(gc_imp))},
            "gnnexplainer": {top_task: importance_to_hex_colors(np.array(ge_imp))},
        }
        return record

    from viz.services.inference import full_analysis, model_available

    if not model_available():
        print("  Modelo no encontrado. Usa --demo para generar datos de prueba.")
        return None

    analysis = full_analysis(canon)
    if analysis is None:
        print(f"  SKIP {entry['name']}: error en inferencia")
        return None

    record["predictions"] = analysis["predictions"]
    record["top_task"] = analysis["top_task"]
    record["xai"] = analysis["xai"]
    record["xai_colors"] = analysis.get("xai_colors", {})
    record["demo"] = False
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Construir corpus pre-computado para viz/")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generar predicciones/XAI demo sin modelo entrenado",
    )
    args = parser.parse_args()

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    mode = "demo" if args.demo else "modelo"
    print(f"Generando corpus ({mode}) en {CORPUS_DIR}")

    written = 0
    for entry in PANAMA_PESTICIDES:
        print(f"  {entry['name']}…")
        record = build_compound(entry, demo=args.demo)
        if record is None:
            continue

        out_path = CORPUS_DIR / f"{entry['id']}.json"
        out_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written += 1
        print(f"    -> {out_path.name}")

    print(f"\nListo: {written} compuestos en {CORPUS_DIR}")
    if args.demo:
        print("NOTA: datos marcados como demo=true — regenera sin --demo tras entrenar el modelo.")


if __name__ == "__main__":
    main()
