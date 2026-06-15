"""
Entrena los 3 modelos baseline sobre Tox21 y guarda resultados.

Baselines:
  1. Random Forest + fingerprints Morgan ECFP4
  2. MLP + fingerprints Morgan ECFP4
  3. SMILES2vec (CNN-GRU)

Todos se evalúan sobre el mismo test set (scaffold split) para
comparación justa con la GNN-GIN.

Uso:
  python scripts/train_baselines.py
  python scripts/train_baselines.py -v                # modo verbose
  python scripts/train_baselines.py --label-stats     # ver distribución
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

# Importar la función de extracción del script de preparación
from scripts.prepare_tox21_graphs import _extract_smiles_y_mask

from src.data.dataset import N_TASKS, TASK_NAMES
from src.evaluation.cross_validation import evaluate_multitask_auc
from src.models.baselines import (
    MLPBaseline,
    RandomForestBaseline,
    SMILES2vec,
    morgan_fingerprints,
    smiles_to_indices,
)
from src.training.loss import MaskedBCELoss

MODELS_ORDER = ("RandomForest", "MLP", "SMILES2vec")


def print_multitask_label_stats(
    title: str, y: np.ndarray, mask: np.ndarray, names: list[str]
) -> None:
    """Imprime estadísticas de etiquetas por tarea (útil para diagnóstico)."""
    print(f"  Etiquetas — {title}", flush=True)
    for t, name in enumerate(names):
        valid = mask[:, t].astype(bool)
        n_v = int(valid.sum())
        if n_v == 0:
            print(f"    {name}: 0 válidos", flush=True)
            continue
        yv = y[valid, t]
        pos = float(np.nansum(yv))
        pct = 100.0 * pos / n_v
        note = "  (muy desbalanceado)" if pct < 2.0 or pct > 98.0 else ""
        print(f"    {name}: {n_v} válidos, {pct:.1f}% positivos{note}", flush=True)


def load_tox21_smiles_labels() -> dict[str, tuple[list[str], np.ndarray, np.ndarray]]:
    """Descarga Tox21 via DeepChem y extrae SMILES, etiquetas y máscara."""
    import deepchem as dc

    _, splits, _ = dc.molnet.load_tox21(
        featurizer=dc.feat.RawFeaturizer(),
        splitter="scaffold",
    )
    train_ds, val_ds, test_ds = splits
    smiles_tr, y_tr, mask_tr = _extract_smiles_y_mask(train_ds)
    smiles_va, y_va, mask_va = _extract_smiles_y_mask(val_ds)
    smiles_te, y_te, mask_te = _extract_smiles_y_mask(test_ds)
    return {
        "train": (smiles_tr, y_tr, mask_tr),
        "val": (smiles_va, y_va, mask_va),
        "test": (smiles_te, y_te, mask_te),
    }


# ── Entrenamiento de cada baseline ────────────────────────────────────────

def train_rf(
    smiles_train: list[str], y_train: np.ndarray, mask_train: np.ndarray,
    smiles_test: list[str], y_test: np.ndarray, mask_test: np.ndarray,
    *, verbose: bool = False, rf_sklearn_verbose: int = 0,
) -> tuple[dict[str, float], float]:
    """Entrena Random Forest (usa train+val, no tiene early stopping)."""
    rf = RandomForestBaseline(verbose=verbose, sklearn_fit_verbose=rf_sklearn_verbose)
    print("  Entrenando...")
    rf.fit(smiles_train, y_train, mask_train)
    preds = rf.predict_proba(smiles_test)
    return evaluate_multitask_auc(y_test, preds, mask_test, TASK_NAMES)


def _epoch_mlp(
    model: MLPBaseline, loader: DataLoader, device: torch.device,
    optimizer: torch.optim.Optimizer, loss_fn: MaskedBCELoss,
) -> float:
    """Una época de entrenamiento del MLP."""
    model.train()
    total = 0.0
    n = 0
    for xb, yb, mb in loader:
        xb = xb.to(device)
        yb = torch.nan_to_num(yb.to(device), nan=0.0)
        mb = mb.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(xb)
        loss = loss_fn(logits, yb, mb)
        loss.backward()
        optimizer.step()
        total += float(loss.detach())
        n += 1
    return total / max(n, 1)


@torch.no_grad()
def _predict_multitask_torch(
    model: torch.nn.Module, X: np.ndarray,
    batch_size: int, device: torch.device,
) -> np.ndarray:
    """Predicción por lotes para modelos PyTorch."""
    model.eval()
    outs: list[torch.Tensor] = []
    x_t = torch.tensor(X, dtype=torch.float32, device=device)
    for start in range(0, len(X), batch_size):
        chunk = x_t[start : start + batch_size]
        outs.append(torch.sigmoid(model(chunk)).cpu())
    return torch.cat(outs, dim=0).numpy()


def train_mlp(
    smiles_train: list[str], y_train: np.ndarray, mask_train: np.ndarray,
    smiles_val: list[str], y_val: np.ndarray, mask_val: np.ndarray,
    smiles_test: list[str], y_test: np.ndarray, mask_test: np.ndarray,
    device: torch.device, epochs: int = 50, batch_size: int = 256,
    *, verbose: bool = False,
) -> tuple[dict[str, float], float]:
    """Entrena MLP con early stopping sobre validación."""
    X_tr = morgan_fingerprints(smiles_train)
    X_val = morgan_fingerprints(smiles_val)
    X_te = morgan_fingerprints(smiles_test)

    y_tr_t = torch.nan_to_num(torch.tensor(y_train, dtype=torch.float32), nan=0.0)
    m_tr_t = torch.tensor(mask_train, dtype=torch.bool)
    loader = DataLoader(
        TensorDataset(torch.tensor(X_tr, dtype=torch.float32), y_tr_t, m_tr_t),
        batch_size=batch_size, shuffle=True,
    )
    model = MLPBaseline(n_tasks=N_TASKS).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = MaskedBCELoss()

    # Early stopping sobre validación
    best_val_auc = 0.0
    patience = 10
    bad = 0
    best_state = None

    for ep in range(1, epochs + 1):
        loss = _epoch_mlp(model, loader, device, opt, loss_fn)

        # Evaluar en validación cada 5 épocas
        if ep % 5 == 0 or ep == epochs:
            val_preds = _predict_multitask_torch(model, X_val, 512, device)
            _, val_auc = evaluate_multitask_auc(y_val, val_preds, mask_val, TASK_NAMES)
            if np.isfinite(val_auc) and val_auc > best_val_auc:
                best_val_auc = val_auc
                bad = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
            if verbose or ep == 1 or ep == epochs:
                print(f"  Época {ep}/{epochs} — loss: {loss:.4f} "
                      f"val_auc: {val_auc:.4f}", flush=True)
            if bad >= patience:
                print(f"  Early stopping en época {ep}")
                break
        elif verbose:
            print(f"  Época {ep}/{epochs} — loss: {loss:.4f}", flush=True)

    # Restaurar mejor modelo y evaluar en test
    if best_state is not None:
        model.load_state_dict(best_state)
    preds = _predict_multitask_torch(model, X_te, 512, device)
    return evaluate_multitask_auc(y_test, preds, mask_test, TASK_NAMES)


def _epoch_smiles2vec(
    model: SMILES2vec, loader: DataLoader, device: torch.device,
    optimizer: torch.optim.Optimizer, loss_fn: MaskedBCELoss,
) -> float:
    """Una época de entrenamiento de SMILES2vec."""
    model.train()
    total = 0.0
    n = 0
    for xb, yb, mb in loader:
        xb = xb.to(device)
        yb = torch.nan_to_num(yb.to(device), nan=0.0)
        mb = mb.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(xb)
        loss = loss_fn(logits, yb, mb)
        loss.backward()
        optimizer.step()
        total += float(loss.detach())
        n += 1
    return total / max(n, 1)


@torch.no_grad()
def _predict_smiles2vec(
    model: SMILES2vec, idx_matrix: np.ndarray,
    batch_size: int, device: torch.device,
) -> np.ndarray:
    """Predicción por lotes para SMILES2vec."""
    model.eval()
    outs: list[torch.Tensor] = []
    x_t = torch.tensor(idx_matrix, dtype=torch.long, device=device)
    for start in range(0, len(idx_matrix), batch_size):
        chunk = x_t[start : start + batch_size]
        outs.append(torch.sigmoid(model(chunk)).cpu())
    return torch.cat(outs, dim=0).numpy()


def _smiles_to_idx_matrix(smiles_list: list[str], max_len: int = 250) -> np.ndarray:
    """Convierte lista de SMILES a matriz de índices para SMILES2vec."""
    return np.array([smiles_to_indices(s, max_len) for s in smiles_list], dtype=np.int64)


def train_smiles2vec(
    smiles_train: list[str], y_train: np.ndarray, mask_train: np.ndarray,
    smiles_val: list[str], y_val: np.ndarray, mask_val: np.ndarray,
    smiles_test: list[str], y_test: np.ndarray, mask_test: np.ndarray,
    device: torch.device, epochs: int = 30, batch_size: int = 128,
    *, verbose: bool = False,
) -> tuple[dict[str, float], float]:
    """Entrena SMILES2vec con early stopping sobre validación."""
    X_tr = _smiles_to_idx_matrix(smiles_train)
    X_val = _smiles_to_idx_matrix(smiles_val)
    X_te = _smiles_to_idx_matrix(smiles_test)

    y_tr_t = torch.nan_to_num(torch.tensor(y_train, dtype=torch.float32), nan=0.0)
    m_tr_t = torch.tensor(mask_train, dtype=torch.bool)
    loader = DataLoader(
        TensorDataset(torch.tensor(X_tr, dtype=torch.long), y_tr_t, m_tr_t),
        batch_size=batch_size, shuffle=True,
    )
    model = SMILES2vec(n_tasks=N_TASKS).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = MaskedBCELoss()

    # Early stopping
    best_val_auc = 0.0
    patience = 8
    bad = 0
    best_state = None

    for ep in range(1, epochs + 1):
        loss = _epoch_smiles2vec(model, loader, device, opt, loss_fn)

        if ep % 5 == 0 or ep == epochs:
            val_preds = _predict_smiles2vec(model, X_val, 256, device)
            _, val_auc = evaluate_multitask_auc(y_val, val_preds, mask_val, TASK_NAMES)
            if np.isfinite(val_auc) and val_auc > best_val_auc:
                best_val_auc = val_auc
                bad = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
            if verbose or ep == 1 or ep == epochs:
                print(f"  Época {ep}/{epochs} — loss: {loss:.4f} "
                      f"val_auc: {val_auc:.4f}", flush=True)
            if bad >= patience:
                print(f"  Early stopping en época {ep}")
                break
        elif verbose:
            print(f"  Época {ep}/{epochs} — loss: {loss:.4f}", flush=True)

    if best_state is not None:
        model.load_state_dict(best_state)
    preds = _predict_smiles2vec(model, X_te, 256, device)
    return evaluate_multitask_auc(y_test, preds, mask_test, TASK_NAMES)


# ── Guardar resultados ────────────────────────────────────────────────────

def save_results(results: list[dict], path: Path) -> None:
    """Guarda resultados de baseline en CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for r in results:
        row: dict[str, object] = {"model": r["model"], "mean_auc": r["mean_auc"]}
        auc_pt = r.get("auc_per_task") or {}
        for t in TASK_NAMES:
            row[t] = auc_pt.get(t, "")
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Entrenar baselines Tox21 (Fase II)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Progreso detallado")
    parser.add_argument("--label-stats", action="store_true",
                        help="Imprimir distribución de etiquetas por tarea")
    parser.add_argument("--rf-sklearn-verbose", type=int, default=0,
                        help="Nivel de verbose del RandomForest de sklearn")
    args = parser.parse_args()
    verbose = bool(args.verbose)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Dispositivo: {device}")

    print("Cargando Tox21 desde DeepChem...")
    data = load_tox21_smiles_labels()
    (st, yt, mt) = data["train"]
    (sv, yv, mv) = data["val"]
    (ste, yte, mte) = data["test"]
    print(f"  Train: {len(st)} | Val: {len(sv)} | Test: {len(ste)}")

    if args.label_stats:
        print_multitask_label_stats("train", yt, mt, TASK_NAMES)
        print_multitask_label_stats("test", yte, mte, TASK_NAMES)

    results: list[dict[str, object]] = []

    # RF usa train+val porque no tiene early stopping
    print("\n=== Baseline 1: Random Forest ===")
    smiles_rf = st + sv
    y_rf = np.concatenate([yt, yv], axis=0)
    mask_rf = np.concatenate([mt, mv], axis=0)
    print(f"  Ajuste con train+val ({len(smiles_rf)} moléculas)")
    auc_rf, mean_rf = train_rf(
        smiles_rf, y_rf, mask_rf, ste, yte, mte,
        verbose=verbose, rf_sklearn_verbose=args.rf_sklearn_verbose,
    )
    print(f"  Test AUC (media): {mean_rf:.3f}")
    results.append({"model": "RandomForest", "mean_auc": mean_rf, "auc_per_task": auc_rf})

    # Verificación de sanidad: si RF < 0.65, probablemente hay un bug
    if not np.isfinite(mean_rf) or mean_rf < 0.65:
        print(f"[ERROR] RF AUC={mean_rf:.3f} < 0.65 — posible bug en datos")
        out = ROOT / "outputs" / "results" / "baseline_results.csv"
        save_results(results, out)
        sys.exit(1)

    # MLP y SMILES2vec usan val para early stopping
    print("\n=== Baseline 2: MLP ===")
    auc_mlp, mean_mlp = train_mlp(
        st, yt, mt, sv, yv, mv, ste, yte, mte, device, verbose=verbose,
    )
    print(f"  Test AUC (media): {mean_mlp:.3f}")
    results.append({"model": "MLP", "mean_auc": mean_mlp, "auc_per_task": auc_mlp})

    print("\n=== Baseline 3: SMILES2vec ===")
    auc_s2v, mean_s2v = train_smiles2vec(
        st, yt, mt, sv, yv, mv, ste, yte, mte, device, verbose=verbose,
    )
    print(f"  Test AUC (media): {mean_s2v:.3f}")
    results.append({"model": "SMILES2vec", "mean_auc": mean_s2v, "auc_per_task": auc_s2v})

    out = ROOT / "outputs" / "results" / "baseline_results.csv"
    save_results(results, out)
    print(f"\nResultados guardados en {out}")


if __name__ == "__main__":
    main()
