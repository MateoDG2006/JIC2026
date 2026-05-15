# Fase II — Baselines (Tox21)

Desarrollo y punto de entrada del entrenamiento de **Random Forest + Morgan**, **MLP + Morgan** y **SMILES2vec**, según `docs/task_train_baselines.md`.

## Ejecución

Desde la **raíz del repositorio** (no desde esta carpeta), con el entorno virtual activado:

```powershell
python phase2_baselines/train_baselines.py
```

Requisitos: mismos que el proyecto (`deepchem`, `torch`, `rdkit`, `scikit-learn`, `pandas`, …) y haber ejecutado antes `scripts/prepare_tox21_graphs.py` **no** es obligatorio para este script (los baselines recargan Tox21 desde DeepChem con el mismo `load_tox21` + scaffold).

## Salida

- `outputs/results/baseline_results.csv` — **última** ejecución completa o parcial: una fila por modelo (`model`, `mean_auc`, columnas por `TASK_NAMES`).
- `outputs/results/baseline_runs_history.csv` — **historial append**: cada vez que se guarda un CSV de resultados se añade una fila con marca UTC y la media AUC por modelo (no se borran ejecuciones anteriores).

### Umbrales RF (scaffold split)

El RF se ajusta con **train+val**; el test no entra en el entrenamiento. Con **scaffold**, una media de test ~**0.72–0.76** es habitual; referencias ~**0.77** suelen ser **split aleatorio**.

- `mean_rf < 0.65` → el script termina con código 1 (sospecha de datos corruptos o máscaras mal definidas).
- `mean_rf < 0.72` → aviso `[WARN]` pero continúa con MLP y SMILES2vec.

### Opciones útiles

```powershell
python phase2_baselines/train_baselines.py --label-stats
python phase2_baselines/train_baselines.py -v
```
