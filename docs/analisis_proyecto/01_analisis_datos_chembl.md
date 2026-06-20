# Etapa 01 — Análisis de datos ChEMBL (Flujo B)

## Objetivo

Aplicar el protocolo del curso **Análisis de Datos y Toma de Decisiones** sobre el dataset ChEMBL de plaguicidas panameños: EDA, tratamiento de faltantes, correlación, clasificación y regresión con métricas estándar.

**Pregunta que responde esta etapa:** *¿Pueden las propiedades moleculares predecir la potencia (pChEMBL) y la clase de actividad de los plaguicidas MIDA, y qué relaciones estadísticas muestran los datos?*

---

## Prerequisito

Ejecutar primero la [Etapa 00](00_extraccion_chembl.md) y verificar que existe:

```
data/raw/chembl_panama_bioactivity.csv
```

---

## Artefactos

| Archivo | Descripción |
|---|---|
| `notebooks/proyecto analisis de datos/01_chembl_analisis_datos.ipynb` | Notebook principal (Entregable 1) |
| `src/analisis_proyecto/chembl_preprocessing.py` | Funciones de preprocesamiento reutilizables |
| `scripts/analisis_proyecto/verify_flow_b.py` | Verificación del pipeline desde terminal |
| `data/processed/chembl_clean.csv` | Dataset imputado |
| `outputs/chembl/figures/*.png` | Figuras para informe |
| `outputs/chembl/models/*.pkl` | Modelos para dashboard (Flujo C) |
| `outputs/chembl/results/metrics_summary.csv` | Tabla comparativa de métricas |

---

## Pipeline

```
chembl_panama_bioactivity.csv
        │
        ▼  Sección 1 — EDA
        ▼  Sección 2 — Missingno, UpSetPlot, imputación
data/processed/chembl_clean.csv
        │
        ├── Sección 3 — Correlación (Pearson + Spearman)
        ├── Sección 4 — Clasificación (RF + SVM)
        └── Sección 5 — Regresión (SVR + RF)
                │
                ▼
        outputs/chembl/models/*.pkl
```

---

## Decisiones metodológicas

| Tema | Decisión |
|---|---|
| Split train/test | Aleatorio por filas, 80/20, `random_state=42` |
| Imputación numérica | Mediana por `family` (fallback: mediana global) |
| Imputación categórica | Moda global o `"Unknown"` |
| Columnas con >250 NaN | Eliminar (requisito del curso) |
| Clasificación | Random Forest + SVM (RBF) |
| Regresión | SVR (RBF) + Random Forest Regressor |
| Umbral Active | pChEMBL ≥ 6 (definido en Etapa 00) |

> **Nota sobre el split por filas:** el mismo plaguicida puede aparecer en train y test con descriptores moleculares idénticos (solo cambia la diana/ensayo). Esto puede **inflar** la accuracy de clasificación. Se documenta en el notebook como limitación metodológica.

---

## Sección 1 — Análisis preliminar

### Medidas de tendencia central

Para columnas numéricas (`pchembl_value`, `mw_freebase`, `alogp`, `psa`, `hba`, `hbd`, `aromatic_rings`, `heavy_atoms`, `rtb`, `cx_logp`, `cx_logd`, `standard_value`):

- `df.describe()`
- Tabla con **media, mediana, moda, desviación estándar** (`summary_statistics()`)

### Distribuciones

- Histogramas: `pchembl_value`, `mw_freebase`, `alogp`
- Boxplots: `pchembl_value` y `alogp` por `family`

### Variables categóricas

Conteos de frecuencia para:

- `activity_class`
- `assay_type`
- `standard_type`
- `target_type`

---

## Sección 2 — Valores faltantes e imputación

### Visualización (antes de limpiar)

| Herramienta | Función |
|---|---|
| `missingno.matrix()` | Patrón global de NaN |
| `missingno.bar()` | NaN por columna |
| `missingno.heatmap()` | Co-ocurrencia de faltantes |
| `upsetplot` | Combinaciones de patrones de NaN |

### Regla del curso — eliminar columnas

```python
nan_counts = df.isna().sum()
drop_cols = nan_counts[nan_counts > 250].index.tolist()
```

Se genera una tabla de auditoría: columna, nº NaN, % del total, decisión (`eliminar` / `conservar`).

Columnas que suelen eliminarse por muchos NaN: `cx_logp`, `cx_logd`, `activity_comment`.

### Imputación — mediana por familia

```python
df_clean = impute_median_by_family(df_dropped, numeric_cols=..., categorical_cols=...)
```

Lógica:

1. Por cada columna numérica, mediana dentro de cada `family`
2. Si una familia no tiene valores, usar mediana global
3. Categóricas: moda o `"Unknown"`

**Salida:** `data/processed/chembl_clean.csv`

---

## Sección 3 — Correlación

### Métodos (mínimo 2 — requisito del curso)

- **Pearson** — relaciones lineales
- **Spearman** — relaciones monótonas (ranking)

### Análisis

1. Tabla `pchembl_value` vs cada descriptor (Pearson + Spearman), ordenada por |Spearman|
2. Heatmap de correlación (triangular superior)
3. Pairplot de las 4–5 variables con mayor |Spearman| vs `pchembl_value`

Función: `correlation_with_target()` en `chembl_preprocessing.py`.

---

## Sección 4 — Clasificación

### Configuración

| Parámetro | Valor |
|---|---|
| Variable objetivo | `activity_class` → {Active, Inactive} |
| Features | Solo descriptores moleculares (sin leakage de ensayo/diana) |
| Split | 80/20, `stratify=y` |

### Features de modelado

```python
FEATURE_COLS = [
    "mw_freebase", "alogp", "psa", "hba", "hbd",
    "aromatic_rings", "heavy_atoms", "rtb",
    "num_ro5_violations", "cx_logp", "cx_logd",
]
```

Solo se usan las columnas que sobrevivieron al paso de imputación.

### Modelos

| Modelo | Configuración |
|---|---|
| **Random Forest** | `n_estimators=100`, `class_weight="balanced"` |
| **SVM (RBF)** | `StandardScaler` + `SVC(probability=True, class_weight="balanced")` |

### Métricas requeridas

- Accuracy train / test
- Confusion matrix (test)
- Classification report
- Curva ROC (test) — Active codificado como clase positiva

### Artefactos guardados

```
outputs/chembl/models/rf_classifier.pkl
outputs/chembl/models/svm_classifier.pkl
outputs/chembl/models/feature_cols.json
```

---

## Sección 5 — Regresión

### Configuración

| Parámetro | Valor |
|---|---|
| Variable objetivo | `pchembl_value` (continua) |
| Features | Mismas que clasificación |
| Split | 80/20, `random_state=42` (sin stratify) |

### Modelos

| Modelo | Configuración |
|---|---|
| **SVR (RBF)** | `StandardScaler` + `SVR(kernel="rbf")` |
| **Random Forest Regressor** | `n_estimators=100` |

### Métricas requeridas

- R² train / test
- MAE (test)
- RMSE (test)
- Scatter predicho vs real (test)

### Artefactos guardados

```
outputs/chembl/models/svr_regressor.pkl
outputs/chembl/models/rf_regressor.pkl
outputs/chembl/results/metrics_summary.csv
```

---

## Módulo `src/analisis_proyecto/chembl_preprocessing.py`

| Función | Descripción |
|---|---|
| `load_bioactivity(path)` | Carga CSV y normaliza dtypes |
| `summary_statistics(df)` | Media, mediana, moda, std |
| `numeric_and_categorical_cols(df)` | Separa tipos de columnas |
| `drop_columns_high_nan(df, threshold=250)` | Elimina columnas + reporte |
| `impute_median_by_family(df, ...)` | Imputación acordada |
| `get_available_feature_cols(df)` | Features presentes post-limpieza |
| `get_feature_matrix(df)` | Retorna X, y_class, y_reg |
| `train_test_split_rows(X, y, ...)` | Split con stratify opcional |
| `correlation_with_target(df)` | Pearson + Spearman vs pChEMBL |

---

## Cómo ejecutar

### Notebook (recomendado)

```bash
# Con .venv activo
jupyter notebook "notebooks/proyecto analisis de datos/01_chembl_analisis_datos.ipynb"
```

Ejecutar **Run All** tras completar la Etapa 00.

### Verificación desde terminal

```bash
python scripts/analisis_proyecto/verify_flow_b.py
```

Si `chembl_panama_bioactivity.csv` no existe, el script genera un CSV sintético temporal para probar el código. Sustituir con datos reales del Flujo A antes del informe final.

---

## Distribución por roles (curso)

| Rol | Secciones del notebook |
|---|---|
| Ingeniero de Datos | 0, 2 (faltantes, imputación, `chembl_clean.csv`) |
| Analista de Datos | 1, 3 (EDA, correlaciones, visualizaciones) |
| Científico de Datos | 4, 5 (modelos, métricas, `.pkl`) |

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Dataset vacío o muy pequeño | Verificar Flujo A; reportar `n` en cada sección |
| Desbalanceo Active/Inactive | `class_weight="balanced"` + proporción en EDA |
| SVM lento (>20k filas) | Documentar tiempo; submuestreo opcional |
| Features eliminadas por NaN | `get_available_feature_cols()` adapta la lista |
| Métricas optimistas por split por filas | Nota metodológica en Sección 4 |

---

## Siguiente etapa

→ **Flujo C** — Dashboard Dash-Plotly (`dashboard/`) usando `chembl_clean.csv` y los modelos `.pkl` generados aquí.

Ver plan general: [EXPANSION_CHEMBL_PLAN.md](../EXPANSION_CHEMBL_PLAN.md).
