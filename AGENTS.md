# agents.md — Guía de desarrollo para agentes IA (Cursor / Claude Code)

Proyecto: **GNN-GIN + XAI para predicción de toxicidad de agroquímicos panameños**  
Stack: Python 3.10 · PyTorch ≥ 2.0 · PyTorch Geometric ≥ 2.4 · RDKit ≥ 2023.09

---

## Contexto del proyecto

Sistema de química computacional que predice el perfil de toxicidad de plaguicidas agrícolas sobre **12 dianas biológicas Tox21** usando Graph Neural Networks (GIN). Entrenado sobre el dataset Tox21 (8,014 moléculas), aplicado al corpus de plaguicidas registrados en el MIDA de Panamá. Incluye Explainable AI (GNNExplainer + Grad-CAM) para identificar grupos funcionales responsables de la toxicidad.

El repositorio objetivo es `gnn-toxicity-panama/`. La estructura de módulos está definida en `CLAUDE.md`.

---

## Reglas absolutas (nunca violar)

### ML

1. **Scaffold split siempre, nunca random split.** Las moléculas con el mismo scaffold de Murcko deben ir siempre al mismo conjunto. Un random split infla el AUC artificialmente porque moléculas similares quedan en train y test. Usar `src/data/splitter.py:scaffold_split`.

2. **MaskedBCELoss obligatoria para Tox21.** El dataset tiene NaN por tarea. Nunca usar `BCELoss` directo ni ignorar NaN con `fillna(0)`. Siempre usar `src/training/loss.py:MaskedBCELoss` que divide sobre `mask.sum()`, no sobre `batch_size * 12`.

3. **Baselines antes que la GNN.** Implementar y validar los tres baselines (RF, MLP, SMILES2vec) antes de desarrollar la GNN. Si el Random Forest no alcanza AUC ~0.77 en Tox21 con scaffold split, hay un bug en el pipeline de datos. No continuar hasta resolver.

4. **AUC-ROC por tarea, nunca accuracy.** Las clases están desbalanceadas (5–20% positivos por tarea). Accuracy no es una métrica válida. Siempre reportar AUC-ROC. Omitir tareas sin las dos clases representadas en el split.

5. **El modelo base debe estar congelado durante XAI.** GNNExplainer optimiza máscaras sobre el grafo de entrada, no los pesos del modelo. Nunca llamar `optimizer.step()` sobre parámetros del modelo durante la explicación.

6. **Test set fijo en todos los folds del 5-fold CV.** El split de test se define una sola vez con `scaffold_split`. Los 5 folds se crean solo dentro de train+val.

### Código

7. **Nunca hardcodear nombres de tareas Tox21 fuera de `src/data/dataset.py`.** Usar siempre la constante `TASK_NAMES` importada desde dataset.

8. **Nunca usar `model.eval()` sin `torch.no_grad()`.** En evaluación, siempre usar el bloque `with torch.no_grad():` para evitar acumulación de gradientes.

9. **Todo acceso a PubChem API debe incluir `time.sleep(0.35)`** entre requests para respetar el rate limit. Sin esto la API devuelve 429.

10. **Guardar el modelo solo cuando mejora `val_auc`, nunca en cada época.** El path de guardado es `outputs/models/best_gin_model.pt`.

---

## Arquitectura del modelo — decisiones fijas

### Por qué GIN y no GCN

GCN usa media ponderada de vecinos → no distingue grafos con distinto número de vecinos. GIN usa `(1+ε) × h_v + Σ h_u` donde `ε` es entrenable, lo que lo hace maximalmente expresivo en la jerarquía de Weisfeiler-Leman de 1er orden. Para moléculas donde el grado del átomo es químicamente informativo (diferencia C sp3 de C sp2), GIN es más adecuado.

### Readout: CONCAT(mean_pool, max_pool)

Nunca usar solo mean_pool. Mean_pool pierde información sobre átomos de alta importancia (outliers). La concatenación mean+max captura tanto la señal promedio como los átomos más activos. Dimensión del readout: `2 × hidden_dim`.

### Conexiones residuales en GINLayer

Son necesarias cuando `n_layers ≥ 3`. Sin residuales, el gradiente se degrada en capas profundas y la convergencia es inestable. Implementar siempre como `out = conv(x) + proj(x)` donde `proj` es `nn.Identity()` si `in_dim == out_dim`, o `nn.Linear(in_dim, out_dim)` si cambia.

### Features de nodo (dim 45) — no reducir

El vector de features por átomo tiene ~45 dimensiones (ver `src/data/featurizer.py`). No reducir ni simplificar este vector. Cada feature tiene justificación química: el tamaño del anillo distingue aromaticidad de alifaticidad, la hibridización identifica geometría molecular, la carga formal es crítica para compuestos iónicos como el paraquat.

### Embedding inicial antes de GIN

El primer bloque `Linear(45 → d) → BN → ReLU` es obligatorio. Sin él, las primeras capas GIN operan en el espacio de features crudas (heterogéneo), lo que dificulta la optimización. El embedding proyecta todos los átomos al mismo espacio latente.

---

## Flujo de desarrollo recomendado

Seguir estrictamente este orden. Cada fase tiene un criterio de aceptación antes de continuar:

```
Fase I — Pipeline de datos
  → Criterio: graphs_train.pt generado, MaskedBCELoss testeada,
    distribución de NaN por tarea documentada

Fase II — Baselines
  → Criterio: RF alcanza AUC ≥ 0.76 con scaffold split
    Si no: el pipeline tiene un bug. Revisar antes de continuar.

Fase III — GNN-GIN
  → Criterio: AUC ≥ 0.82 promedio en scaffold split test

Fase IV — XAI
  → Criterio: Precision@3 > 80% sobre corpus panameño

Fase V — Aplicación
  → Criterio: 6 casos de estudio + reporte MIDA/MINSA generado
```

---

## Convenciones de código

### Estructura de módulos

```
src/data/       → todo lo relacionado con datos (no poner lógica de modelo aquí)
src/models/     → solo arquitecturas (sin training loop, sin métricas)
src/training/   → trainer.py, loss.py, metrics.py (sin lógica de modelo)
src/xai/        → explicabilidad (importa modelos, nunca al revés)
src/evaluation/ → métricas y validación química (independiente del modelo)
notebooks/      → exploración y reportes (no código de producción)
```

### Naming

- Clases de modelo: `PascalCase` (`GINToxicity`, `MLPBaseline`)
- Funciones de datos: `snake_case` (`scaffold_split`, `smiles_to_graph`)
- Constantes globales: `UPPER_SNAKE` (`TASK_NAMES`, `TOX21_AIDS`, `ATOM_TYPES`)
- Archivos de checkpoint: `{arquitectura}_{dataset}_{fold}.pt` (`gin_tox21_fold1.pt`)

### Typing

Usar type hints en todas las funciones públicas:

```python
def scaffold_split(
    smiles_list: list[str],
    frac_train: float = 0.7,
    frac_val: float = 0.15,
    frac_test: float = 0.15,
) -> tuple[list[int], list[int], list[int]]:
```

### Manejo de NaN en etiquetas

```python
# CORRECTO
mask   = ~torch.isnan(labels)
labels = labels.nan_to_num(0.0)   # reemplazar NaN por 0 solo para el tensor

# INCORRECTO — nunca hacer esto
labels = labels.fillna(0)         # falsea la distribución de clases
labels[torch.isnan(labels)] = -1  # -1 no tiene semántica en BCELoss
```

---

## Implementación del featurizer — detalles críticos

### Aristas bidireccionales

```python
# CORRECTO — PyG espera grafos no dirigidos como bidireccionales
for bond in mol.GetBonds():
    i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
    edge_index += [[i, j], [j, i]]
    edge_attr  += [feat, feat]     # duplicar features para ambas direcciones

# INCORRECTO — grafo dirigido solo tiene la mitad de los mensajes
edge_index += [[i, j]]
```

### Canonicalización obligatoria

```python
# CORRECTO
mol = Chem.MolFromSmiles(smiles)
if mol is None:
    return None
smiles_canon = Chem.MolToSmiles(mol)   # canonicalizar
mol = Chem.MolFromSmiles(smiles_canon)  # re-parsear desde canónico

# INCORRECTO — el SMILES original puede tener representaciones ambiguas
mol = Chem.MolFromSmiles(smiles)
# usar mol directamente sin canonicalizar
```

### Validación antes de featurizar

Siempre retornar `None` si el SMILES es inválido. El DataLoader debe filtrar los `None` antes de crear el batch.

---

## Entrenamiento — detalles críticos

### Gradient clipping

```python
# OBLIGATORIO — sin esto las GNNs profundas explotan en las primeras épocas
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

### Scheduler

`ReduceLROnPlateau` debe monitorizar **val_AUC** como métrica a **maximizar** (`mode="max"`). Pasar el valor positivo de AUC; no negar el valor salvo uses `mode="min"`.

```python
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, mode="max", factor=0.5, patience=20,
)
scheduler.step(val_auc)
```

### Early stopping

Contar épocas sin mejora en `val_auc`. Paciencia: 50 épocas. Guardar el estado del modelo en cada mejora, no al final del entrenamiento.

### Inicialización del modelo para cada fold

```python
# CORRECTO — nuevo modelo por fold para CV válida
for fold_idx in range(5):
    model = GINToxicity(**model_config).to(device)
    best_auc = train(model, ...)

# INCORRECTO — continuar entrenando el mismo modelo entre folds
model = GINToxicity(...)
for fold_idx in range(5):
    train(model, ...)   # acumula conocimiento entre folds — CV inválida
```

---

## XAI — detalles críticos

### GNNExplainer requiere `batch` tensor

```python
# Para una sola molécula, batch debe ser un tensor de ceros
explanation = explainer(
    x          = data.x,
    edge_index = data.edge_index,
    batch      = torch.zeros(data.x.size(0), dtype=torch.long),  # obligatorio
    target     = torch.tensor([task_index]),
)
```

### Grad-CAM: limpiar hooks siempre

```python
fwd_hook = layer.register_forward_hook(save_activation)
bwd_hook = layer.register_backward_hook(save_gradient)

try:
    # forward + backward
    ...
finally:
    fwd_hook.remove()   # limpiar aunque ocurra una excepción
    bwd_hook.remove()
```

### Normalización de importancias antes de visualizar

```python
# CORRECTO — normalizar a [0,1] para colormap consistente
imp = (imp - imp.min()) / (imp.max() - imp.min() + 1e-8)

# INCORRECTO — valores sin normalizar producen colores inconsistentes entre moléculas
draw_molecule(smiles, raw_cam_values)
```

---

## PubChem API — convenciones

### Rate limit

```python
time.sleep(0.35)  # entre requests individuales
time.sleep(0.4)   # entre batches de compound/cid
time.sleep(0.5)   # entre requests de classification (más pesados)
```

### Manejo de errores

```python
try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"Error CID {cid}: {e}")
    continue   # nunca lanzar excepción en el pipeline batch
```

### Verificar con RDKit después de descargar

```python
def validate_smiles(smi):
    mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
    return Chem.MolToSmiles(mol) if mol else None

df['SMILES_canonical'] = df['SMILES'].apply(validate_smiles)
df = df.dropna(subset=['SMILES_canonical'])  # descartar SMILES inválidos de PubChem
```

---

## Logging y reproducibilidad

### Semillas — fijar siempre al inicio del script

```python
import random, numpy as np, torch

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
```

### Weights & Biases — configuración mínima

```python
wandb.init(
    project = "gnn-toxicity-panama",
    config  = {**model_config, **train_config},
    name    = f"gin_fold{fold_idx}_d{hidden_dim}_L{n_layers}",
)
```

Loggear siempre: `train_loss`, `val_auc`, `lr`, `epoch`. Loggear por tarea solo al final del fold.

### config.yaml — fuente única de verdad

Nunca hardcodear hiperparámetros en el código. Siempre leer desde `config/config.yaml`. Si se corre un experimento con hiperparámetros diferentes, crear una copia del config con sufijo descriptivo (`config_d256_L5.yaml`).

---

## Tests mínimos requeridos

Antes de entrenar el modelo completo, verificar:

```python
# 1. Forward pass sin NaN
batch = next(iter(DataLoader(train_ds, batch_size=4)))
logits = model(batch.x, batch.edge_index, batch.batch)
assert not torch.isnan(logits).any(), "NaN en logits"
assert logits.shape == (4, 12), f"Shape incorrecto: {logits.shape}"

# 2. MaskedBCELoss con todo enmascarado
mask_zero = torch.zeros(4, 12, dtype=torch.bool)
# Debe retornar tensor(0.) sin error de división por cero
loss = MaskedBCELoss()(logits, batch.y, mask_zero)

# 3. Scaffold split — sin scaffolds compartidos
train_scaffolds = get_scaffolds(smiles_list, train_idx)
test_scaffolds  = get_scaffolds(smiles_list, test_idx)
assert len(train_scaffolds & test_scaffolds) == 0, "Leak de scaffold"

# 4. GNNExplainer — shape de máscara
node_imp, edge_imp = explain_molecule(explainer, data, task_index=0)
assert node_imp.shape[0] == data.x.shape[0], "Shape de node_mask incorrecto"
assert (node_imp >= 0).all(), "node_mask tiene valores negativos"
```

---

## Errores comunes y cómo evitarlos

| Error | Causa | Solución |
|---|---|---|
| AUC = 0.5 en todas las tareas | Random split en lugar de scaffold split | Usar `scaffold_split` de `src/data/splitter.py` |
| `nan` en loss desde la época 1 | NaN en labels no enmascarados | Verificar que `mask` cubra todos los NaN antes de `MaskedBCELoss` |
| `RuntimeError: Expected all tensors on same device` | `batch.mask` no movido a device | Agregar `batch = batch.to(device)` antes de forward |
| GNNExplainer devuelve importancias uniformes | `epochs=200` muy bajo o `lr` muy alto | Probar `epochs=300, lr=0.005` |
| PubChem API devuelve 429 | Sin rate limiting | Agregar `time.sleep(0.4)` entre requests |
| AUC baja por no superar baselines | Gradient explosion | Verificar que `clip_grad_norm_` está activo |
| Scaffold leak entre train y test | Scaffold split implementado incorrectamente | Verificar con el test de scaffolds compartidos |

---

## Referencia rápida: shapes de tensores

```
Featurizer output (una molécula):
  data.x:           (num_atoms, 45)
  data.edge_index:  (2, num_bonds × 2)
  data.edge_attr:   (num_bonds × 2, 9)
  data.y:           (12,)
  data.mask:        (12,)  dtype=bool

PyG batch (batch_size=B moléculas):
  batch.x:          (Σ atoms_i, 45)
  batch.edge_index: (2, Σ bonds_i × 2)
  batch.batch:      (Σ atoms_i,)  → índice de molécula por nodo
  batch.y:          (B, 12)
  batch.mask:       (B, 12)  dtype=bool

GINToxicity forward:
  input  x:         (Σ atoms, 45)
  after embedding:  (Σ atoms, d)
  after GIN layers: (Σ atoms, d)
  after mean_pool:  (B, d)
  after max_pool:   (B, d)
  after concat:     (B, 2d)
  logits output:    (B, 12)

GNNExplainer output:
  node_mask:        (num_atoms, 45)  o  (num_atoms,) según node_mask_type
  edge_mask:        (num_edges,)

Grad-CAM output:
  cam:              (num_atoms,)  valores en [0,1]
```

---

## No hacer (antipatrones específicos de este proyecto)

- **No** usar `random_split` de PyG ni `train_test_split` de sklearn para moléculas — scaffold split siempre.
- **No** reportar métricas como promedio simple sobre tareas con diferente número de muestras válidas — usar promedio sobre AUCs calculables.
- **No** entrenar GNNExplainer con el modelo en modo `model.train()` — siempre `model.eval()`.
- **No** incluir el corpus panameño en el training set de la GNN — es solo para inferencia y validación.
- **No** usar `global_add_pool` como readout — es sensible al tamaño del grafo (moléculas grandes tendrán representaciones más grandes artificialmente).
- **No** comparar AUC de la GNN con AUC de baselines evaluados en splits diferentes.
- **No** mover el `time.sleep` de PubChem API a fuera del loop — debe ejecutarse entre cada request individual.
