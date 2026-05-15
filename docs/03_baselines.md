# Modelos Baseline

**Módulo:** `src/models/baselines.py`  
**Fase:** II — Baselines (Semanas 3–4)

---

## Descripción

Tres modelos de referencia que deben evaluarse **antes** de implementar la GNN, bajo el mismo protocolo de evaluación (scaffold split, 5-fold CV, `evaluate_multitask_auc`).

> **Regla de oro:** Si el Baseline 1 (Random Forest) no alcanza AUC ~0.77, el pipeline de datos tiene un bug. Siempre depurar los baselines antes de avanzar a la GNN.

---

## Baseline 1 — Random Forest + Fingerprints Morgan

**AUC esperado en Tox21: ~0.77**

### Descripción

Usa fingerprints ECFP4 (Morgan, radio=2, 2048 bits) como representación molecular y Random Forest como clasificador multitarea.

```python
class RandomForestBaseline:
    # MultiOutputClassifier(RandomForestClassifier(n_estimators=100))
    # Input: fingerprints ECFP4 [N × 2048]
    # Output: probabilidades [N × 12]
```

### Ventajas / limitaciones

| Ventaja | Limitación |
|---|---|
| Sin GPU, rápido de entrenar | No generaliza a estructuras nuevas |
| Interpretable con feature importance | Fingerprints no mapean a átomos específicos |
| Robusto, difícil de overfittear | Pierde información topológica 3D |

---

## Baseline 2 — MLP + Fingerprints Morgan

**AUC esperado en Tox21: ~0.79**

### Descripción

Red neuronal feed-forward con fingerprints ECFP4 como entrada.

```
Input: fingerprints ECFP4 [batch × 2048]
  → Linear(2048→512) + BN + ReLU + Dropout(0.3)
  → Linear(512→256)  + BN + ReLU + Dropout(0.3)
  → Linear(256→12)   — logits
```

### Entrenamiento

- Optimizador: Adam, lr=1e-3
- Loss: `MaskedBCELoss` (mismo que GNN)
- Early stopping: patience=50, monitor val_AUC

---

## Baseline 3 — SMILES2vec (CNN-GRU)

**AUC esperado en Tox21: ~0.81**

### Descripción

Arquitectura del paper Goh et al. KDD 2018. Aprende representaciones desde la secuencia de caracteres SMILES sin features moleculares manuales.

```
Input: índices de caracteres SMILES [batch × seq_len]
  → Embedding(vocab_size=60, dim=50) → [batch × 250 × 50]
  → Conv1D(filters=192, kernel=3)    → [batch × 250 × 192]
  → BiGRU(units=224)                 → [batch × 250 × 448]
  → BiGRU(units=384)                 → [batch × 384*2]
  → Dropout + Linear(768→12)         → logits
```

### Posición relativa

SMILES2vec es el baseline más fuerte. La GNN-GIN debe superarlo para validar el enfoque basado en grafos:

```
GIN objetivo  →  AUC > 0.83
SMILES2vec    →  AUC ~0.81
MLP           →  AUC ~0.79
Random Forest →  AUC ~0.77
```

---

## Generación de fingerprints ECFP4

```python
from rdkit.Chem import AllChem, MolFromSmiles

def morgan_fingerprints(smiles_list, radius=2, n_bits=2048):
    fps = []
    for smi in smiles_list:
        mol = MolFromSmiles(smi)
        fp  = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        fps.append(list(fp))
    return np.array(fps)  # [N × 2048]
```

---

## Evaluación unificada

Los tres baselines se evalúan con la misma función:

```python
from src.evaluation.cross_validation import evaluate_multitask_auc

auc_per_task, mean_auc = evaluate_multitask_auc(
    y_true     = labels_array,    # (N, 12)
    y_pred     = probs_array,     # (N, 12)
    mask       = mask_array,      # (N, 12)
    task_names = TASK_NAMES       # lista de 12 nombres
)
```

Solo se calcula AUC sobre tareas con al menos dos clases representadas en el split de evaluación.

---

## Resultados esperados por tarea

Las tareas más desafiantes (menor AUC típico) suelen ser aquellas con mayor desbalance de clases o menor número de positivos:

| Tarea | % positivos aprox. | AUC RF esperado |
|---|---|---|
| NR-AR | ~5% | ~0.75 |
| NR-ER | ~8% | ~0.77 |
| SR-ARE | ~15% | ~0.80 |
| SR-MMP | ~20% | ~0.82 |

---

## Archivos de salida

```
outputs/results/
├── baseline_results.csv    # AUC por tarea para los 3 modelos
└── cv_summary.csv          # Resumen 5-fold CV
```

Formato de `baseline_results.csv`:

```
model,NR-AR,NR-AR-LBD,NR-AhR,...,SR-p53,mean_auc
RandomForest,0.74,0.76,0.79,...,0.78,0.773
MLP,0.77,0.79,0.81,...,0.80,0.793
SMILES2vec,0.79,0.81,0.83,...,0.82,0.812
```

---

## Entregables

- [ ] Baseline 1 (RF) entrenado — AUC promedio ≥ 0.76
- [ ] Baseline 2 (MLP) entrenado — AUC promedio ≥ 0.78
- [ ] Baseline 3 (SMILES2vec) entrenado — AUC promedio ≥ 0.80
- [ ] `outputs/results/baseline_results.csv` con AUC por tarea
- [ ] Curvas ROC por tarea en `notebooks/03_baseline_models.ipynb`
- [ ] Si RF no alcanza ~0.77: revisar pipeline de datos antes de continuar

---

## Dependencias

```
scikit-learn     # RandomForestClassifier, MultiOutputClassifier
rdkit>=2023.09   # Morgan fingerprints
torch>=2.0       # MLP y SMILES2vec
numpy, pandas
```
