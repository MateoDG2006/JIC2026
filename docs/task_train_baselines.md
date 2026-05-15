# Tarea: Implementar `scripts/train_baselines.py`

## Objetivo

Crear el script `scripts/train_baselines.py` que entrena los tres modelos baseline del proyecto
(Random Forest, MLP, SMILES2vec) y guarda los resultados en `outputs/results/baseline_results.csv`.

Este script es el **punto de validación del pipeline de datos**: si Random Forest no alcanza
AUC ~0.77, hay un bug en los datos o en el split — hay que depurar antes de continuar con la GNN.

---

## Contexto del repositorio

### Código ya existente que el script debe reutilizar

| Módulo | Qué importar | Para qué |
|---|---|---|
| `src/models/baselines.py` | `RandomForestBaseline`, `MLPBaseline`, `SMILES2vec`, `morgan_fingerprints`, `smiles_to_indices`, `VOCAB_SIZE` | Los tres modelos y sus utilidades |
| `src/data/dataset.py` | `TASK_NAMES`, `N_TASKS` | Lista de las 12 tareas Tox21 en orden correcto |
| `src/evaluation/cross_validation.py` | `evaluate_multitask_auc` | Calcular AUC por tarea + AUC medio |
| `src/training/loss.py` | `MaskedBCELoss` | Loss para MLP y SMILES2vec (maneja NaN en etiquetas) |
| `scripts/prepare_tox21_graphs.py` | `_extract_smiles_y_mask` | Extraer SMILES/y/mask de un DiskDataset de DeepChem |

### Por qué re-cargar DeepChem en lugar de usar los `.pt`

Los archivos `data/processed/graphs_{train,val,test}.pt` contienen objetos PyG `Data` **sin
SMILES almacenado** — solo tienen `x` (features de átomos), `edge_index`, `y`, `mask`.
Los baselines necesitan SMILES para calcular fingerprints Morgan o la codificación de caracteres.
La solución es re-cargar Tox21 desde DeepChem usando exactamente la misma llamada que
`prepare_tox21_graphs.py`, lo que garantiza que el scaffold split sea idéntico.

---

## Especificación del script

### Ruta de salida

```
scripts/train_baselines.py
```

### Estructura general

```python
ROOT = Path(__file__).resolve().parents[1]
# sys.path setup igual que en prepare_tox21_graphs.py

def load_tox21_smiles_labels():
    """Carga train/val/test desde DeepChem. Retorna dict con smiles, y, mask por split."""

def train_rf(smiles_train, y_train, mask_train, smiles_test, y_test, mask_test):
    """Entrena RandomForestBaseline y retorna (auc_per_task, mean_auc)."""

def train_mlp(smiles_train, y_train, mask_train, smiles_val, y_val, mask_val,
              smiles_test, y_test, mask_test, device):
    """Entrena MLPBaseline con Adam + MaskedBCELoss. Retorna (auc_per_task, mean_auc)."""

def train_smiles2vec(smiles_train, y_train, mask_train, smiles_val, y_val, mask_val,
                     smiles_test, y_test, mask_test, device):
    """Entrena SMILES2vec con Adam + MaskedBCELoss. Retorna (auc_per_task, mean_auc)."""

def save_results(results: list[dict], path: Path):
    """Guarda DataFrame con AUC por tarea y modelo en CSV."""

def main():
    ...
```

---

## Detalles de implementación

### 1. Carga de datos

```python
import deepchem as dc
from scripts.prepare_tox21_graphs import _extract_smiles_y_mask

_tasks, splits, _ = dc.molnet.load_tox21(
    featurizer=dc.feat.RawFeaturizer(),
    splitter="scaffold",
)
train_ds, val_ds, test_ds = splits

smiles_tr, y_tr, mask_tr = _extract_smiles_y_mask(train_ds)
smiles_va, y_va, mask_va = _extract_smiles_y_mask(val_ds)
smiles_te, y_te, mask_te = _extract_smiles_y_mask(test_ds)
```

### 2. Random Forest

- Clase: `RandomForestBaseline` de `src/models/baselines.py`
- Sin val set — entrenar directo sobre train, evaluar sobre test
- No usa `MaskedBCELoss`; la máscara se aplica en `fit()` (etiquetas inválidas → 0)
- Evaluar con `evaluate_multitask_auc(y_te, preds, mask_te, TASK_NAMES)`
- AUC esperado: **~0.77** — si es menor a 0.74, imprimir advertencia de bug en datos

### 3. MLP

- Clase: `MLPBaseline` de `src/models/baselines.py`
- Input: fingerprints Morgan ECFP4 (2048 bits) via `morgan_fingerprints(smiles)`
- Usar `torch.utils.data.TensorDataset` + `DataLoader(batch_size=256, shuffle=True)`
- Optimizer: `Adam(lr=1e-3)`
- Loss: `MaskedBCELoss` (importar de `src/training/loss.py`)
- Épocas: 50 (sin early stopping para simplificar)
- Evaluar sobre test al final con `torch.sigmoid(logits)`
- AUC esperado: **~0.79**

### 4. SMILES2vec

- Clase: `SMILES2vec` de `src/models/baselines.py`
- Input: secuencias de índices de caracteres via `smiles_to_indices(smi, max_len=250)`
- Usar `TensorDataset(x_idx, y_tensor, mask_tensor)` + `DataLoader(batch_size=128, shuffle=True)`
- Optimizer: `Adam(lr=1e-3)`
- Loss: `MaskedBCELoss`
- Épocas: 30
- AUC esperado: **~0.81**

### 5. Formato de salida CSV

El CSV debe tener una fila por modelo con columnas:

```
model, mean_auc, NR-AR, NR-AR-LBD, NR-AhR, NR-Aromatase, NR-ER, NR-ER-LBD,
NR-PPAR-gamma, SR-ARE, SR-AtAD5, SR-HSE, SR-MMP, SR-p53
```

Ejemplo de fila:
```
RandomForest, 0.773, 0.741, 0.762, 0.812, ...
```

Ruta: `outputs/results/baseline_results.csv` — crear directorio si no existe.

---

## Reglas críticas (no negociables)

1. **Nunca usar accuracy** — solo AUC-ROC. Tox21 es extremadamente desbalanceado.
2. **`MaskedBCELoss` obligatorio** para MLP y SMILES2vec — Tox21 tiene NaN en etiquetas.
3. **El scaffold split debe ser idéntico** al de `prepare_tox21_graphs.py` — usar exactamente
   el mismo `dc.molnet.load_tox21(featurizer=dc.feat.RawFeaturizer(), splitter="scaffold")`.
4. **`model.train()` durante el loop de entrenamiento** y **`model.eval()` durante la evaluación** —
   BatchNorm se comporta diferente en cada modo.
5. **Sanity check RF**: si `mean_auc < 0.74`, imprimir:
   `"[ERROR] RF AUC={:.3f} < 0.74 — revisar pipeline de datos antes de continuar"`
   y salir con código 1.

---

## Manejo de dispositivo

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando dispositivo: {device}")
```

Los tensores de fingerprints y SMILES deben moverse al dispositivo antes de pasarlos al modelo.

---

## Print de progreso esperado

```
Cargando Tox21 desde DeepChem...
  Train: 6265 moléculas | Val: 783 | Test: 784

=== Baseline 1: Random Forest ===
  Entrenando...
  Test AUC: 0.773
  Por tarea: NR-AR=0.741, NR-AhR=0.812, ...

=== Baseline 2: MLP ===
  Época 1/50 — loss: 0.412
  ...
  Test AUC: 0.791

=== Baseline 3: SMILES2vec ===
  Época 1/30 — loss: 0.389
  ...
  Test AUC: 0.808

Resultados guardados en outputs/results/baseline_results.csv
```

---

## Archivos que NO debe crear ni modificar

- `src/models/baselines.py` — ya implementado y correcto
- `src/evaluation/cross_validation.py` — no tocar
- `src/training/loss.py` — no tocar
- `data/processed/*.pt` — no tocar

---

## Dependencias

Todas ya instaladas en el entorno `toxgnn`:
`deepchem`, `torch`, `torch_geometric`, `rdkit`, `scikit-learn`, `numpy`, `pandas`
