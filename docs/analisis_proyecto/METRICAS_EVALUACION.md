# Métricas de evaluación — ChEMBL y Tox21

Documento de referencia para interpretar métricas del proyecto (AUDIT P2).

## Dos protocolos de split

### Split por filas (`split=filas`)

- Partición aleatoria estratificada sobre **filas de bioactividad**.
- El mismo compuesto puede aparecer en train y test con descriptores moleculares idénticos.
- **Infla accuracy y R²** porque el modelo memoriza patrones por molécula, no por ensayo.
- Útil solo si el escenario de uso incluye contexto de ensayo/diana (features adicionales).

### Split por compuesto (`split=compuesto`)

- Partición por `compound_name` / `pubchem_cid`: todas las filas de un compuesto van al mismo conjunto.
- Evalúa **generalización a moléculas nuevas** — métrica honesta para descriptores sin contexto.
- Es la **métrica principal** reportada en el dashboard (`/panama/models`) y en este documento.

## Clasificación (activity_class)

| Modelo | Split filas — accuracy | Split compuesto — accuracy |
|--------|------------------------|----------------------------|
| Random Forest | ~0.76 | ~0.38 |

La caída de ~38 pp confirma data leakage en el split por filas: descriptores moleculares solos no discriminan bien actividad entre ensayos distintos del mismo compuesto.

## Regresión (pChEMBL)

| Modelo | Feature set | Split | R² test típico |
|--------|-------------|-------|----------------|
| Random Forest | descriptores | filas | ~0.5–0.7 |
| Random Forest | descriptores | compuesto | ~0.03 |
| SVR | descriptores | compuesto | negativo |
| Random Forest | descriptores+ensayo | filas | mayor (contexto de diana) |

R² negativo en split por compuesto indica que predecir pChEMBL **solo con descriptores** es ambiguo: el mismo compuesto tiene distintos pChEMBL según diana y tipo de ensayo.

## GNN-GIN (Tox21)

- Objetivo CLAUDE.md: AUC-ROC promedio ≥ 0.82 sobre 12 tareas Tox21.
- Protocolo: scaffold split + 5-fold CV (`make train-gin-cv`).
- Comparativa baselines vs GIN: pestaña **Comparativa** en `make viz` (`/panama/models`).
- Resultados en `outputs/results/baseline_results.csv`, `gin_results.csv`, `gin_cv_summary.csv`.

## Imputación pChEMBL

- Columna `pchembl_imputed`: 1 si el valor proviene de `standard_value` convertido.
- Estadísticas en `outputs/dashboard/pchembl_imputation.json` (generado con `make prepare-dashboard`).

## Features de modelado

Tras auditoría (P7/P8), `FEATURE_COLS` excluye:

- `heavy_atoms` — colinealidad ~0.99 con `mw_freebase`
- `cx_logp`, `cx_logd` — 100% NaN en extracción local

Features activos (8): MW, LogP, PSA, HBA, HBD, anillos aromáticos, enlaces rotables, violaciones Lipinski.

## Comandos

```bash
make test-chembl-flow-b    # regenera chembl_clean + modelos + metrics_summary.csv
make prepare-dashboard     # artefactos JSON para viz
make train-gin-cv          # 5-fold CV GIN (requiere prepare-graphs)
make viz                   # servidor unificado con comparativa y disclaimers
```
