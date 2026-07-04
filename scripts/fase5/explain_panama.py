#!/usr/bin/env python3
"""
Predicciones multitarea + explicaciones XAI sobre el corpus panameño (Fase V).

Uso:
  python scripts/fase5/explain_panama.py --model outputs/models/best_gin_model.pt \\
      --corpus data/processed/panama_corpus.pt
  python scripts/fase5/explain_panama.py --skip-xai          # solo predicciones (rápido)
  python scripts/fase5/explain_panama.py --xai-mida-only      # XAI solo ingredientes MIDA
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.dataset import TASK_NAMES  # noqa: E402
from src.data.pubchem_api import MIDA_ACTIVE_INGREDIENTS  # noqa: E402
from src.evaluation.chemical_coherence import precision_at_k  # noqa: E402
from src.models.gin import GINToxicity  # noqa: E402


def risk_level(prob: float) -> str:
    if prob > 0.7:
        return "ALTO"
    if prob > 0.4:
        return "MODERADO"
    return "BAJO"


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "compound"


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_model(model_path: Path, config_path: Path, device: torch.device) -> GINToxicity:
    cfg = load_config(config_path)["model"]
    model = GINToxicity(
        node_feat_dim=int(cfg["node_feat_dim"]),
        edge_feat_dim=int(cfg["edge_feat_dim"]),
        hidden_dim=int(cfg["hidden_dim"]),
        n_layers=int(cfg["n_layers"]),
        n_tasks=int(cfg["n_tasks"]),
        dropout=float(cfg["dropout"]),
    ).to(device)
    try:
        state = torch.load(model_path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(model_path, map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model


def load_corpus(corpus_path: Path) -> list[tuple[str, Any]]:
    try:
        corpus = torch.load(corpus_path, map_location="cpu", weights_only=False)
    except TypeError:
        corpus = torch.load(corpus_path, map_location="cpu")
    return corpus["entries"]


def predict_graph(
    model: GINToxicity,
    graph: Any,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    g = graph.to(device)
    batch = torch.zeros(g.x.size(0), dtype=torch.long, device=device)
    edge_attr = g.edge_attr if hasattr(g, "edge_attr") else None
    with torch.no_grad():
        logits = model(g.x, g.edge_index, batch, edge_attr=edge_attr)
        return torch.sigmoid(logits).squeeze().cpu().numpy()


def _normalize_importance(imp: torch.Tensor) -> list[float] | None:
    arr = imp.detach().cpu().numpy().astype(np.float64)
    if arr.size == 0:
        return None
    arr = (arr - arr.min()) / (arr.max() - arr.min() + 1e-8)
    return [float(round(v, 4)) for v in arr]


def _importance_aligns_with_graph(
    imp: list[float] | None,
    graph: Any,
    smiles: str,
) -> bool:
    """True si las importancias coinciden con el grafo y el SMILES canónico."""
    if imp is None:
        return False
    if len(imp) != graph.x.size(0):
        return False
    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        n_atoms = Chem.MolFromSmiles(Chem.MolToSmiles(mol)).GetNumAtoms()
        return len(imp) == n_atoms
    except Exception:
        return False


def run_xai(
    model: GINToxicity,
    graph: Any,
    task_index: int,
    device: torch.device,
) -> tuple[list[float] | None, list[float] | None, list[float] | None]:
    g = graph.to(device)
    gnn_imp: list[float] | None = None
    gc_imp: list[float] | None = None
    edge_imp: list[float] | None = None

    try:
        try:
            from src.xai.gnn_explainer import build_explainer, explain_molecule

            explainer = build_explainer(model, task_index)
            node_imp, edge_mask = explain_molecule(explainer, g)
            gnn_imp = _normalize_importance(node_imp)
            edge_imp = _normalize_importance(edge_mask)
        except Exception as exc:
            print(f"    [WARN] GNNExplainer: {exc}")

        try:
            from src.xai.grad_cam import grad_cam_graph

            cam = grad_cam_graph(model, g, task_index)
            gc_imp = _normalize_importance(cam)
        except Exception as exc:
            print(f"    [WARN] Grad-CAM: {exc}")
    finally:
        # GNNExplainer deja el modelo en train(); el clasificador falla con batch=1.
        model.eval()

    return gnn_imp, gc_imp, edge_imp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predicciones y XAI sobre plaguicidas panameños",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT / "outputs" / "models" / "best_gin_model.pt",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "data" / "processed" / "panama_corpus.pt",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "config.yaml",
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=ROOT / "outputs" / "results" / "panama_predictions.csv",
    )
    parser.add_argument(
        "--profile-out",
        type=Path,
        default=ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv",
    )
    parser.add_argument(
        "--xai-dir",
        type=Path,
        default=ROOT / "outputs" / "xai",
    )
    parser.add_argument("--skip-xai", action="store_true", help="Solo predicciones")
    parser.add_argument(
        "--xai-mida-only",
        action="store_true",
        help="XAI solo para ingredientes activos MIDA",
    )
    parser.add_argument(
        "--xai-threshold",
        type=float,
        default=0.4,
        help="Explicar tareas con P >= umbral además de la tarea crítica",
    )
    parser.add_argument("--device", default=None, help="cuda | cpu (auto si omitido)")
    args = parser.parse_args()

    if not args.model.is_file():
        print(f"ERROR: no existe el modelo {args.model}")
        print("Ejecuta: make train-gin")
        sys.exit(1)
    if not args.corpus.is_file():
        print(f"ERROR: no existe el corpus {args.corpus}")
        print("Ejecuta: make build-panama-corpus")
        sys.exit(1)

    device = torch.device(
        args.device if args.device else ("cuda" if torch.cuda.is_available() else "cpu")
    )
    print(f"Dispositivo: {device}")
    print(f"Cargando modelo: {args.model}")
    model = load_model(args.model, args.config, device)

    entries = load_corpus(args.corpus)
    print(f"Compuestos en corpus: {len(entries)}")

    mida_lower = {n.lower() for n in MIDA_ACTIVE_INGREDIENTS}
    expl_dir = args.xai_dir / "explanations"
    fig_dir = args.xai_dir / "figures"
    if not args.skip_xai:
        expl_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for i, (name, graph) in enumerate(entries, 1):
        probs = predict_graph(model, graph, device)
        max_idx = int(np.argmax(probs))
        max_task = TASK_NAMES[max_idx]
        max_prob = float(probs[max_idx])
        smiles = getattr(graph, "smiles", "") or ""
        cid = getattr(graph, "cid", "")
        family = getattr(graph, "family", "")

        row: dict[str, Any] = {
            "compuesto": name,
            "cid": cid,
            "familia": family,
            "smiles": smiles,
            "tarea_critica": max_task,
            "prob_max": round(max_prob, 4),
            "alerta": risk_level(max_prob),
        }
        for task, p in zip(TASK_NAMES, probs):
            row[task] = round(float(p), 4)
        rows.append(row)

        is_mida = name.lower() in mida_lower
        do_xai = (
            not args.skip_xai
            and smiles
            and (not args.xai_mida_only or is_mida)
        )
        if do_xai:
            print(f"  [{i}/{len(entries)}] XAI: {name} (tarea crítica: {max_task})")
            tasks_to_explain = {max_idx}
            for ti, tname in enumerate(TASK_NAMES):
                if float(probs[ti]) >= args.xai_threshold:
                    tasks_to_explain.add(ti)

            compound_slug = slugify(name)
            xai_record: dict[str, Any] = {
                "compuesto": name,
                "cid": cid,
                "smiles": smiles,
                "predictions": {t: row[t] for t in TASK_NAMES},
            }

            for ti in sorted(tasks_to_explain):
                tname = TASK_NAMES[ti]
                gnn_imp, gc_imp, edge_imp = run_xai(model, graph, ti, device)

                if gnn_imp is not None and not _importance_aligns_with_graph(
                    gnn_imp, graph, smiles
                ):
                    print(
                        f"    [SKIP] GNNExplainer {tname}: importancias "
                        f"({len(gnn_imp)}) no coinciden con el grafo/SMILES"
                    )
                    gnn_imp = None

                if gc_imp is not None and not _importance_aligns_with_graph(
                    gc_imp, graph, smiles
                ):
                    print(
                        f"    [SKIP] Grad-CAM {tname}: importancias "
                        f"({len(gc_imp)}) no coinciden con el grafo/SMILES"
                    )
                    gc_imp = None

                xai_record.setdefault("tasks", {})[tname] = {
                    "gnnexplainer_nodes": gnn_imp,
                    "gradcam_nodes": gc_imp,
                    "gnnexplainer_edges": edge_imp,
                    "precision_at_3_gnn": (
                        precision_at_k(smiles, np.array(gnn_imp), tname, k=3)
                        if gnn_imp else None
                    ),
                    "precision_at_3_gradcam": (
                        precision_at_k(smiles, np.array(gc_imp), tname, k=3)
                        if gc_imp else None
                    ),
                }

                from src.xai.visualizer import draw_molecule_with_importance

                if gnn_imp is not None:
                    try:
                        draw_molecule_with_importance(
                            smiles,
                            np.array(gnn_imp),
                            title=f"{name} — {tname} (GNNExplainer)",
                            save_path=fig_dir / f"{compound_slug}_{tname}_gnnexplainer.svg",
                        )
                    except ValueError as exc:
                        print(f"    [SKIP] SVG GNNExplainer {tname}: {exc}")
                        gnn_imp = None
                if gc_imp is not None:
                    try:
                        draw_molecule_with_importance(
                            smiles,
                            np.array(gc_imp),
                            title=f"{name} — {tname} (Grad-CAM)",
                            save_path=fig_dir / f"{compound_slug}_{tname}_gradcam.svg",
                        )
                    except ValueError as exc:
                        print(f"    [SKIP] SVG Grad-CAM {tname}: {exc}")
                        gc_imp = None

            expl_path = expl_dir / f"{compound_slug}.json"
            expl_path.write_text(
                json.dumps(xai_record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    pred_df = pd.DataFrame(rows)
    args.predictions_out.parent.mkdir(parents=True, exist_ok=True)
    args.profile_out.parent.mkdir(parents=True, exist_ok=True)

    pred_df.to_csv(args.predictions_out, index=False)
    profile_cols = [
        "compuesto", "cid", "familia", "smiles",
        "tarea_critica", "prob_max", "alerta",
    ] + TASK_NAMES
    pred_df[profile_cols].to_csv(args.profile_out, index=False)

    print(f"\nPredicciones: {args.predictions_out} ({len(pred_df)} compuestos)")
    print(f"Perfil:       {args.profile_out}")
    if not args.skip_xai:
        print(f"XAI JSON:     {expl_dir}")
        print(f"XAI SVG:      {fig_dir}")
    print("\nDistribución de alertas:")
    print(pred_df["alerta"].value_counts().to_string())
    print("\nListo.")


if __name__ == "__main__":
    main()
