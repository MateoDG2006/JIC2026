# Entrenamiento y Evaluación

**Módulos:** `src/training/trainer.py`, `src/training/loss.py`, `src/training/metrics.py`, `src/evaluation/cross_validation.py`  
**Fase:** III — Modelo GNN-GIN (Semanas 5–6)

---

## Descripción

Loop de entrenamiento principal con early stopping, gradient clipping, scheduler de learning rate y logging a Weights & Biases. Incluye 5-fold cross-validation con scaffold split para reportar métricas robustas.

---

## Configuración del experimento

```yaml
# config/config.yaml
model:
  node_feat_dim: 45
  hidden_dim:    128
  n_layers:      3
  n_tasks:       12
  dropout:       0.3

training:
  lr:                       0.001
  batch_size:               32
  max_epochs:               250
  early_stopping_patience:  50
  grad_clip_norm:           1.0
  model_save_path:          outputs/models/best_gin_model.pt

scheduler:
  factor:    0.5
  patience:  20

evaluation:
  n_folds:   5
  split:     scaffold
```

---

## Loop de entrenamiento

```
Por cada época:
  1. train_epoch()      → calcular pérdida, backprop, clip gradientes
  2. evaluate()         → calcular val_AUC sin gradientes
  3. scheduler.step()   → reducir lr si val_AUC no mejora en 20 épocas
  4. wandb.log()        → registrar epoch, train_loss, val_auc, lr
  5. early stopping     → guardar mejor modelo, contar épocas sin mejora
```

### Detalles del entrenamiento

- **Optimizador:** Adam (lr=1e-3)
- **Scheduler:** `ReduceLROnPlateau`, factor=0.5, patience=20 épocas
- **Gradient clipping:** `max_norm=1.0` (evita explosión de gradientes)
- **Criterio de parada:** 50 épocas sin mejora en val_AUC
- **Métrica de parada:** AUC promedio sobre las 12 tareas Tox21

---

## Función de pérdida: MaskedBCELoss

Tox21 tiene valores NaN en las etiquetas (no todas las moléculas fueron ensayadas en todas las 12 dianas). La máscara evita calcular pérdida sobre entradas sin medición:

```
loss_per_entry = BCEWithLogits(logits, targets)   # (batch, 12)
masked_loss    = loss_per_entry * mask             # cero donde NaN
final_loss     = masked_loss.sum() / mask.sum()    # media solo sobre válidos
```

Esta pérdida es idéntica para la GNN y los baselines MLP/SMILES2vec.

---

## Métricas de evaluación

### AUC-ROC por tarea

```python
from sklearn.metrics import roc_auc_score

# Por cada tarea t:
valid_idx  = mask[:, t].astype(bool)
auc_task_t = roc_auc_score(y_true[valid_idx, t], y_pred[valid_idx, t])
```

Solo se calcula AUC cuando la tarea tiene ejemplos de **ambas** clases en el split. Las tareas sin representación se omiten del promedio.

### AUC promedio (métrica principal)

```
mean_AUC = promedio de AUC sobre tareas evaluables
```

---

## 5-fold Cross-Validation

```
Proceso por fold:
  1. Dividir train+val con scaffold split (diferente fold)
  2. Entrenar modelo desde cero con la config del experimento
  3. Cargar mejor checkpoint (por val_AUC)
  4. Evaluar en test set (fijo en todos los folds)
  5. Registrar AUC por tarea

Reporte final:
  mean_AUC ± std  sobre los 5 folds
```

El test set **permanece fijo** en todos los folds para comparación justa.

### Interpretación de std

| std | Interpretación |
|---|---|
| < 0.015 | Modelo estable — baja varianza entre folds |
| 0.015–0.03 | Varianza aceptable |
| > 0.03 | Posible inestabilidad — revisar scaffold split o hiperparámetros |

---

## Criterios de éxito

| Métrica | Mínimo | Objetivo |
|---|---|---|
| AUC-ROC promedio | > 0.82 | > 0.84 |
| AUC-ROC por tarea | > 0.75 en todas | > 0.80 en todas |
| Std entre folds | < 0.02 | < 0.015 |
| Diferencia val/test | < 0.02 | < 0.01 |
| Supera RF baseline | Obligatorio | +0.05 AUC |
| Supera SMILES2vec | Objetivo principal | +0.02 AUC |

---

## Logging con Weights & Biases

```python
wandb.init(project="gnn-toxicity-panama")
wandb.log({
    'epoch':      epoch,
    'train_loss': train_loss,
    'val_auc':    val_auc,
    'lr':         optimizer.param_groups[0]['lr'],
})
```

Seguimiento de curvas de convergencia, comparación de runs de ablation study y detección temprana de overfitting.

---

## Archivos de salida

```
outputs/
├── models/
│   └── best_gin_model.pt         # mejor checkpoint (val_AUC)
└── results/
    ├── gin_results.csv           # AUC por tarea y fold
    └── cv_summary.csv            # media ± std por tarea
```

---

## Entregables

- [ ] Convergencia verificada en un solo fold antes del CV completo
- [ ] 5-fold CV completo ejecutado — AUC ≥ 0.82 promedio
- [ ] `outputs/results/gin_results.csv` con AUC por tarea y fold
- [ ] Tabla comparativa GNN vs 3 baselines documentada
- [ ] Curvas de entrenamiento y convergencia en W&B
- [ ] Ablation study (d=128 vs 256, 3 vs 5 capas GIN) documentado

---

## Dependencias

```
torch>=2.0
torch_geometric>=2.4
wandb
scikit-learn     # roc_auc_score
```
