"""
Entrena la GNN-GIN sobre grafos moleculares Tox21 (Fase III).

Carga los grafos pre-procesados (graphs_{train,val,test}.pt), entrena
GINToxicity con early stopping sobre validación, evalúa en test y guarda
el modelo y métricas.

Requisito previo:
  python scripts/fase1/prepare_tox21_graphs.py

Uso:
  python scripts/fase3/train_gin.py
  python scripts/fase3/train_gin.py --config config/config.yaml
  python scripts/fase3/train_gin.py -v
  python scripts/fase3/train_gin.py --wandb
  python scripts/fase3/train_gin.py --device cuda --require-gpu
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from torch_geometric.loader import DataLoader

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.dataset import N_TASKS, TASK_NAMES, ToxicityDataset
from src.models.gin import GINToxicity
from src.training.trainer import evaluate, train


def compute_pos_weight(dataset: ToxicityDataset) -> torch.Tensor:
    """Calcula pos_weight por tarea: num_negativos / num_positivos.

    Compensa el desbalance de clases de Tox21 donde tareas como NR-AR
    tienen solo ~2-5% de positivos. Sin estos pesos, el modelo aprende
    a predecir 'no toxico' para todo.
    """
    pos = torch.zeros(N_TASKS)
    neg = torch.zeros(N_TASKS)
    for data in dataset:
        y = data.y.view(-1) if data.y.dim() == 1 else data.y.squeeze()
        m = data.mask.view(-1) if data.mask.dim() == 1 else data.mask.squeeze()
        for t in range(N_TASKS):
            if m[t]:
                if y[t] > 0.5:
                    pos[t] += 1
                else:
                    neg[t] += 1
    return neg / pos.clamp(min=1.0)


def load_config(path: Path) -> dict[str, Any]:
    """Carga config.yaml y resuelve rutas relativas desde la raíz del repo."""
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    save_path = ROOT / cfg["training"]["model_save_path"]
    cfg["training"]["model_save_path"] = str(save_path)
    return cfg


def set_seed(seed: int, device: torch.device) -> None:
    """Fija semillas para reproducibilidad."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)


def resolve_device(device_arg: str, require_gpu: bool) -> torch.device:
    """Selecciona dispositivo de entrenamiento (GPU preferida por defecto)."""
    choice = device_arg.strip().lower()

    if choice in ("auto", "gpu"):
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
        elif require_gpu:
            raise RuntimeError(
                "Se solicitó GPU (--require-gpu o --device cuda) pero "
                "torch.cuda.is_available() es False. "
                "Instala PyTorch con soporte CUDA: "
                "https://pytorch.org/get-started/locally/"
            )
        else:
            print("[AVISO] CUDA no disponible; entrenando en CPU.")
            device = torch.device("cpu")
    elif choice == "cpu":
        device = torch.device("cpu")
    elif choice.startswith("cuda"):
        if not torch.cuda.is_available():
            raise RuntimeError(
                f"Dispositivo '{device_arg}' solicitado pero CUDA no está disponible."
            )
        device = torch.device(device_arg)
    else:
        raise ValueError(
            f"Dispositivo no reconocido: {device_arg!r}. "
            "Usa auto, cpu, cuda o cuda:N."
        )

    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
        name = torch.cuda.get_device_name(device)
        props = torch.cuda.get_device_properties(device)
        mem_gb = props.total_memory / (1024 ** 3)
        print(f"GPU: {name} ({mem_gb:.1f} GB) — {device}")

    return device


def build_loaders(
    data_root: Path,
    batch_size: int,
    device: torch.device,
    num_workers: int = 0,
) -> tuple[DataLoader, DataLoader, DataLoader, ToxicityDataset, int, int, int]:
    """Construye DataLoaders de PyG para train, val y test."""
    train_ds = ToxicityDataset(data_root, "train")
    val_ds = ToxicityDataset(data_root, "val")
    test_ds = ToxicityDataset(data_root, "test")

    use_pin_memory = device.type == "cuda"
    loader_kwargs = {
        "batch_size": batch_size,
        "num_workers": num_workers,
        "pin_memory": use_pin_memory,
    }

    train_loader = DataLoader(train_ds, shuffle=True, **loader_kwargs)
    val_loader = DataLoader(val_ds, shuffle=False, **loader_kwargs)
    test_loader = DataLoader(test_ds, shuffle=False, **loader_kwargs)

    return (
        train_loader,
        val_loader,
        test_loader,
        train_ds,
        len(train_ds),
        len(val_ds),
        len(test_ds),
    )


def save_results(
    auc_per_task: dict[str, float],
    mean_auc: float,
    val_auc: float,
    path: Path,
) -> None:
    """Guarda AUC por tarea en CSV (mismo formato que baseline_results)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    row: dict[str, object] = {
        "model": "GIN",
        "mean_auc": mean_auc,
        "val_auc": val_auc,
    }
    for task in TASK_NAMES:
        row[task] = auc_per_task.get(task, "")
    pd.DataFrame([row]).to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrenar GNN-GIN sobre Tox21")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "config.yaml",
        help="Ruta a config.yaml",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "data" / "processed",
        help="Directorio con graphs_{train,val,test}.pt",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Imprimir progreso por época",
    )
    parser.add_argument(
        "--wandb",
        action="store_true",
        help="Registrar métricas en Weights & Biases",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla aleatoria",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Dispositivo: auto (GPU si hay CUDA), cpu, cuda o cuda:N",
    )
    parser.add_argument(
        "--require-gpu",
        action="store_true",
        help="Fallar si no hay GPU CUDA disponible",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=0,
        help="Workers del DataLoader (0 recomendado en Windows)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    device = resolve_device(args.device, args.require_gpu)
    set_seed(args.seed, device)

    batch_size = int(cfg["training"]["batch_size"])
    print(f"Cargando grafos desde {args.data_dir}...")
    train_loader, val_loader, test_loader, train_ds, n_tr, n_va, n_te = build_loaders(
        args.data_dir,
        batch_size,
        device,
        num_workers=args.num_workers,
    )
    print(f"  Train: {n_tr} | Val: {n_va} | Test: {n_te}")

    # Calcular pos_weight para compensar desbalance de clases
    use_pw = cfg["training"].get("use_pos_weight", False)
    pos_weight = None
    if use_pw:
        pos_weight = compute_pos_weight(train_ds)
        print("  pos_weight por tarea:")
        for name, w in zip(TASK_NAMES, pos_weight.tolist()):
            print(f"    {name:16s} {w:.1f}")
    else:
        print("  pos_weight: desactivado")

    model_cfg = cfg["model"]
    model = GINToxicity(
        node_feat_dim=int(model_cfg["node_feat_dim"]),
        edge_feat_dim=int(model_cfg["edge_feat_dim"]),
        hidden_dim=int(model_cfg["hidden_dim"]),
        n_layers=int(model_cfg["n_layers"]),
        n_tasks=int(model_cfg["n_tasks"]),
        dropout=float(model_cfg["dropout"]),
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(
        f"Modelo GINToxicity — hidden_dim={model_cfg['hidden_dim']}, "
        f"n_layers={model_cfg['n_layers']}, parámetros: {n_params:,}"
    )

    use_wandb = bool(args.wandb)
    if use_wandb:
        import wandb

        wandb.init(
            project=cfg["wandb"]["project"],
            entity=cfg["wandb"].get("entity") or None,
            config=cfg,
        )

    print("\n=== Entrenamiento GIN ===")
    if args.verbose:
        best_val = _train_verbose(
            model, train_loader, val_loader, cfg, device, use_wandb,
            pos_weight=pos_weight,
        )
    else:
        best_val = train(
            model,
            train_loader,
            val_loader,
            cfg,
            device,
            task_names=TASK_NAMES,
            use_wandb=use_wandb,
            pos_weight=pos_weight,
        )

    save_path = Path(cfg["training"]["model_save_path"])
    if save_path.is_file():
        try:
            state = torch.load(save_path, map_location=device, weights_only=True)
        except TypeError:
            state = torch.load(save_path, map_location=device)
        model.load_state_dict(state)
    else:
        print(f"[AVISO] No se encontró checkpoint en {save_path}; "
              "evaluando el último estado del modelo.")

    print("\n=== Evaluación en test ===")
    auc_test, mean_test = evaluate(model, test_loader, device, TASK_NAMES)
    print(f"  Val AUC (mejor):  {best_val:.4f}")
    print(f"  Test AUC (media): {mean_test:.4f}")
    for task, auc in auc_test.items():
        print(f"    {task}: {auc:.4f}")

    out = ROOT / "outputs" / "results" / "gin_results.csv"
    save_results(auc_test, mean_test, best_val, out)
    print(f"\nModelo guardado en {save_path}")
    print(f"Resultados guardados en {out}")

    if use_wandb:
        import wandb

        wandb.log({"test_mean_auc": mean_test, **{f"test_auc/{k}": v for k, v in auc_test.items()}})
        wandb.finish()


def _train_verbose(
    model: torch.nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: dict[str, Any],
    device: torch.device,
    use_wandb: bool,
    pos_weight: torch.Tensor | None = None,
) -> float:
    """Loop de entrenamiento con impresión de progreso por época."""
    from src.training.trainer import train_epoch
    from src.training.loss import MaskedBCELoss

    opt = torch.optim.Adam(model.parameters(), lr=float(config["training"]["lr"]))
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt,
        mode="max",
        factor=float(config["scheduler"]["factor"]),
        patience=int(config["scheduler"]["patience"]),
    )
    pw = pos_weight.to(device) if pos_weight is not None else None
    loss_fn = MaskedBCELoss(pos_weight=pw)
    save_path = Path(config["training"]["model_save_path"])
    save_path.parent.mkdir(parents=True, exist_ok=True)

    best = 0.0
    bad = 0
    patience = int(config["training"]["early_stopping_patience"])
    max_epochs = int(config["training"]["max_epochs"])
    grad_clip = float(config["training"]["grad_clip_norm"])

    if use_wandb:
        import wandb

    for epoch in range(max_epochs):
        tl = train_epoch(model, train_loader, opt, loss_fn, device, grad_clip)
        _, val_auc = evaluate(model, val_loader, device, TASK_NAMES)

        if not np.isfinite(val_auc):
            print(f"  Época {epoch + 1}/{max_epochs} — loss: {tl:.4f} "
                  f"val_auc: nan", flush=True)
            bad += 1
            if bad >= patience:
                print(f"Early stopping en época {epoch}. Mejor val_AUC: {best:.4f}")
                break
            continue

        sched.step(val_auc)

        if use_wandb:
            wandb.log({
                "epoch": epoch,
                "train_loss": tl,
                "val_auc": val_auc,
                "lr": opt.param_groups[0]["lr"],
            })

        improved = val_auc > best
        if improved:
            best = val_auc
            bad = 0
            torch.save(model.state_dict(), save_path)
        else:
            bad += 1

        marker = " *" if improved else ""
        print(
            f"  Época {epoch + 1}/{max_epochs} — loss: {tl:.4f} "
            f"val_auc: {val_auc:.4f}{marker}",
            flush=True,
        )

        if bad >= patience:
            print(f"Early stopping en época {epoch}. Mejor val_AUC: {best:.4f}")
            break

    return best


if __name__ == "__main__":
    main()
