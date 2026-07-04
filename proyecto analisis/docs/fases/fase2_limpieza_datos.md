# Fase 2 — Limpieza y Consolidacion de Datos

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Limpiar y consolidar el dataset ChEMBL en DOS niveles: medicion (`activities_clean.csv`) y compuesto (`compounds_features.csv`, 107 filas) |
| **Duracion** | 2-3 dias |
| **Entrada** | `data/raw/chembl_panama_bioactivity.csv` (~3,608 filas, 33 columnas) |
| **Salida** | `data/processed/activities_clean.csv` (medicion, dedup) + `data/processed/compounds_features.csv` (107 compuestos) |
| **Rol lider** | Ingeniero de Datos |
| **Notebook** | `notebooks/fase2_limpieza.ipynb` |
| **Modulo** | `src/analisis_proyecto/preprocessing/pipeline.py` |

---

## 1. Contexto

El CSV crudo de la Fase 1 contiene **3.608 filas pero solo 107 compuestos unicos** (`chembl_id`, `smiles` y `compound_name` tienen 107 valores distintos cada uno). En promedio hay 34 mediciones por compuesto y una sola molecula aporta 1.167 filas. Los 8 descriptores moleculares son **constantes dentro de cada compuesto** (`nunique = 1` por `chembl_id`): un modelo entrenado sobre filas solo "ve" 107 vectores de entrada distintos, repetidos muchas veces.

Por eso esta fase cambia la unidad de analisis: pasa de "fila/medicion" a **"compuesto" (107)** para todo lo fisicoquimico y multivariado, y conserva el nivel "medicion" solo donde es legitimo (perfil de dianas, promiscuidad, comparacion de endpoints). El resultado son **dos tablas** coherentes entre si.

Se cumplen ademas los requisitos del curso:

- Detectar y visualizar patrones de faltantes
- Eliminar columnas con mas de 250 NaN
- Imputar valores faltantes con al menos dos estrategias justificadas
- Documentar cada decision

### Decisiones metodologicas (resumen consolidado)

Estas decisiones se aplican aqui y se arrastran a Fase 3 (EDA) y a la Fase 4 (analisis multivariado). Se documentan juntas para evitar dispersion entre fases:

| Tema | Decision |
|---|---|
| **Unidad de analisis** | **Compuesto (107).** El split por compuesto se usa en el baseline predictivo de Fase 4 (§12, P6) |
| De-duplicacion | Aplicar `filter_potential_duplicates` ANTES de construir ambas tablas |
| Imputacion numerica | A nivel COMPUESTO: mediana por `family` (fallback: mediana global) |
| Imputacion categorica | Moda global o `"Unknown"` |
| Columnas con >250 NaN | Eliminar (requisito del curso) |
| Valores censurados | Conservar `standard_relation`; segregar `>`/`<` en el analisis de potencia |
| `activity_class` / `pchembl_value` | **Ya NO son variable objetivo de un modelo.** Se conservan como descriptores de bioactividad |

> **Nota sobre el split (honestidad metodologica):** el split por filas 80/20 queda **descartado como default**. El mismo plaguicida aparecia en train y test con descriptores identicos (solo cambia la diana/ensayo), lo que **infla** las metricas. La unidad de analisis correcta es el compuesto; la evaluacion predictiva honesta (P6) se documenta en [Fase 4 §12](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6). Ver tambien [METRICAS_EVALUACION.md](../../../mateo_docs/auditorias/METRICAS_EVALUACION.md).

---

## 2. Esquema del dataset crudo

### Columnas numericas (14)

| Columna | Descripcion | Rango tipico | % NaN esperado |
|---|---|---|---|
| `pchembl_value` | -log10(actividad en M) — descriptor de bioactividad | 3.0 - 10.0 | 0% (filtrada en Fase 1) |
| `standard_value` | Valor de actividad en unidades originales | 0.001 - 1e6 | ~5% |
| `mw_freebase` | Peso molecular (Da) | 100 - 700 | ~2% |
| `alogp` | LogP calculado (lipofilicidad) | -4.0 - 8.0 | ~3% |
| `psa` | Area de superficie polar (A^2) | 0 - 200 | ~3% |
| `hba` | Aceptores de hidrogeno | 0 - 15 | ~2% |
| `hbd` | Donores de hidrogeno | 0 - 8 | ~2% |
| `aromatic_rings` | Numero de anillos aromaticos | 0 - 6 | ~2% |
| `heavy_atoms` | Atomos pesados (no-H) | 5 - 50 | ~2% |
| `rtb` | Enlaces rotables | 0 - 15 | ~2% |
| `num_ro5_violations` | Violaciones de regla de Lipinski | 0 - 4 | ~2% |
| `cx_logp` | LogP calculado (ChemAxon) | -4.0 - 8.0 | ~40% |
| `cx_logd` | LogD a pH 7.4 (ChemAxon) | -6.0 - 8.0 | ~40% |
| `molecular_species` | Especie molecular predominante | — | ~30% |

### Columnas categoricas (8 principales)

| Columna | Cardinalidad tipica | Uso |
|---|---|---|
| `activity_class` | 2 (Active/Inactive) | Descriptor de bioactividad (ya no target) |
| `family` | 7 | Familia quimica MIDA |
| `standard_type` | 13 | Tipo de endpoint (IC50, EC50, Ki, Potency...) |
| `standard_relation` | 3 (`=`, `>`, `<`) | Censura del valor medido |
| `assay_type` | 3-5 | Binding, Functional, ADMET |
| `target_type` | 5-8 | SINGLE PROTEIN, ORGANISM, etc. |
| `organism` | variable | Especie del organismo diana |
| `standard_units` | 3-5 | nM, uM, ug/mL |

### Columnas de identificacion

| Columna | Proposito |
|---|---|
| `compound_name` | Nombre del plaguicida |
| `chembl_id` | ID ChEMBL de la molecula (107 unicos) |
| `smiles` | Estructura molecular canonica |
| `activity_id` | ID unico de la medicion |
| `target_chembl_id` | ID ChEMBL de la diana |
| `target_name` | Nombre de la diana biologica |
| `assay_chembl_id` | ID del ensayo |
| `potential_duplicate` | Marca ChEMBL de duplicado (usada en dedup) |
| `data_validity_comment` | Comentario de calidad |
| `activity_comment` | Comentario del experimentador |

---

## 3. Procedimiento paso a paso

El orden importa: la **de-duplicacion se aplica primero**, y sobre el mismo dataframe dedup se construyen las dos tablas. Esto elimina la inconsistencia historica (el reporte de imputacion de pchembl corria sobre 2.807 filas dedup mientras los modelos usaban 3.608 filas sin dedup).

### Paso 1 — Carga y tipado

**Funcion:** `load_bioactivity(path)` en `preprocessing/pipeline.py:88`

```python
from src.analisis_proyecto.preprocessing.pipeline import load_bioactivity

df = load_bioactivity("data/raw/chembl_panama_bioactivity.csv")
print(f"Shape crudo: {df.shape}")          # esperado (~3608, 33)
print(f"Compuestos unicos: {df['chembl_id'].nunique()}")  # esperado 107
```

Verificaciones:
- `pchembl_value` debe ser float64
- `family` debe tener exactamente 7 valores unicos
- `chembl_id`, `smiles` y `compound_name` deben tener 107 valores unicos

### Paso 2 — De-duplicacion (correccion de bug)

**Funcion:** `filter_potential_duplicates(df)` en `preprocessing/pipeline.py:472`

En el crudo hay **801 filas (~22%) marcadas `potential_duplicate=1`** que el pipeline anterior **NO eliminaba**. Es un bug: esas mediciones sesgan los conteos de bioactividad y las agregaciones por compuesto. Se corrige aplicando la dedup como **primer** paso de transformacion.

```python
from src.analisis_proyecto.preprocessing.pipeline import filter_potential_duplicates

df_dedup, dup_report = filter_potential_duplicates(df)
print(dup_report)               # accion, filas_eliminadas (~801), filas_restantes
print(f"Filas tras dedup: {len(df_dedup)}")
```

`dup_report` se guarda como auditoria. Todo lo que sigue opera sobre `df_dedup`.

### Paso 3 — Manejo de valores censurados (`standard_relation`)

ChEMBL registra la relacion del valor medido: `=` (valor puntual), `>` o `<` (censura por debajo/encima del limite de deteccion). Un `IC50 > 10000 nM` no es comparable con un `IC50 = 50 nM`.

Decision: **conservar** `standard_relation` en la tabla de medicion y **marcar/segregar** los valores censurados. En el analisis de potencia (Fase 3/4) los valores con relacion distinta de `=` se excluyen del calculo de tendencia central o se reportan aparte, para no introducir un sesgo optimista/pesimista en la potencia.

```python
df_dedup["is_censored"] = df_dedup["standard_relation"].fillna("=").ne("=")
print(df_dedup["standard_relation"].value_counts(dropna=False))
```

### Paso 4 — Diagnostico de faltantes

**Funcion:** `summary_statistics(df)` en `preprocessing/pipeline.py:116`

```python
from src.analisis_proyecto.preprocessing.pipeline import summary_statistics

stats = summary_statistics(df_dedup)   # media, mediana, moda, std, n_missing, pct_missing
print(stats.to_string())
```

### Paso 5 — Visualizacion de faltantes (requisito del curso)

**Funcion:** `plot_missingno_report(df)` en `preprocessing/pipeline.py:166`. Se mantienen las visualizaciones missingno (al menos 3).

| Visualizacion | Libreria | Proposito |
|---|---|---|
| Matriz de nulidad | `missingno.matrix(df)` | Patron visual de NaN por fila |
| Barras de completitud | `missingno.bar(df)` | Porcentaje de datos presentes por columna |
| Heatmap de co-ocurrencia | `missingno.heatmap(df)` | Correlacion entre columnas con NaN |
| UpSet plot | `upsetplot` (via `missingness_upset_series`) | Combinaciones de patrones de faltantes |

```python
from src.analisis_proyecto.preprocessing.pipeline import plot_missingno_report

plot_missingno_report(df_dedup, save_dir="outputs/chembl/figures/")
```

### Paso 6 — Eliminacion de columnas con alto NaN

**Funcion:** `drop_columns_high_nan(df, threshold=250)` en `preprocessing/pipeline.py:209`. Retorna el dataframe reducido y una tabla de auditoria con la decision por columna.

```python
from src.analisis_proyecto.preprocessing.pipeline import drop_columns_high_nan

df_reduced, audit_df = drop_columns_high_nan(df_dedup, threshold=250)
```

Columnas tipicamente eliminadas:

| Columna | % NaN tipico | Razon |
|---|---|---|
| `cx_logp` | ~40% | Redundante con `alogp` |
| `cx_logd` | ~40% | Dato ChemAxon opcional |
| `activity_comment` | ~70% | Texto libre, no modelable |
| `data_validity_comment` | ~95% | Solo presente en datos dudosos |
| `molecular_species` | ~30% | Categorica con alta cardinalidad |

### Paso 7 — Tabla 1: `activities_clean.csv` (nivel MEDICION)

Se conserva el dataframe dedup con las columnas legitimas a nivel de medicion. Es la base para P2 (promiscuidad) y P4 (endpoints/dianas).

```python
activities_cols = [
    "chembl_id", "compound_name", "family",
    "target_chembl_id", "target_name", "target_type",
    "standard_type", "standard_relation", "standard_value", "standard_units",
    "pchembl_value", "pchembl_imputed", "assay_type",
]
activities_clean = df_reduced[[c for c in activities_cols if c in df_reduced.columns]].copy()
activities_clean.to_csv("data/processed/activities_clean.csv", index=False)
```

### Paso 8 — Tabla 2: `compounds_features.csv` (nivel COMPUESTO, 107 filas)

**Funcion:** `build_compound_features(activities_df)` en `preprocessing/pipeline.py` **(nueva funcion — a implementar)**.

Agrega la tabla de mediciones a **una fila por compuesto** (107). Los descriptores moleculares son constantes por compuesto, asi que se toma el primer valor no nulo por `chembl_id`; los agregados de bioactividad se calculan sobre las mediciones (respetando la censura en `pct_active`/`pchembl_*`).

```python
def build_compound_features(activities_df: pd.DataFrame) -> pd.DataFrame:
    """(nueva funcion — a implementar)

    Consolida las mediciones dedup a nivel de compuesto (107 filas).

    Devuelve por cada chembl_id:
      - Identificacion: chembl_id, compound_name, family, smiles
      - Descriptores (constantes por compuesto): mw_freebase, alogp, psa,
        hba, hbd, aromatic_rings, rtb, heavy_atoms, num_ro5_violations
      - Agregados de bioactividad:
          pchembl_median   -> mediana de pchembl_value (valores no censurados)
          pchembl_std      -> desviacion de pchembl_value
          n_activities     -> numero de mediciones tras dedup
          n_targets        -> dianas distintas (= promiscuidad)
          n_assay_types    -> tipos de ensayo distintos
          n_standard_types -> endpoints distintos (Ki, IC50, ...)
          pct_active       -> fraccion de mediciones con activity_class == Active
    """
    ...
```

Columnas de la tabla resultante:

| Grupo | Columnas |
|---|---|
| Identificacion | `chembl_id`, `compound_name`, `family`, `smiles` |
| Descriptores (constantes) | `mw_freebase`, `alogp`, `psa`, `hba`, `hbd`, `aromatic_rings`, `rtb`, `heavy_atoms`, `num_ro5_violations` |
| Agregados de bioactividad | `pchembl_median`, `pchembl_std`, `n_activities`, `n_targets`, `n_assay_types`, `n_standard_types`, `pct_active` |

```python
from src.analisis_proyecto.preprocessing.pipeline import build_compound_features

compounds = build_compound_features(activities_clean)
assert len(compounds) == 107, "compounds_features debe tener 107 filas"
```

### Paso 9 — Imputacion a nivel COMPUESTO

**Funcion:** `impute_median_by_family(df, numeric_cols, categorical_cols)` en `preprocessing/pipeline.py:244`

La imputacion de descriptores se hace **sobre la tabla de compuestos (107 filas)**, no sobre las 3.608 mediciones. Asi cada molecula se imputa una sola vez y no se repite el mismo valor cientos de veces. Estrategia: mediana por `family` (preserva la estructura fisicoquimica de cada familia) con fallback a mediana global; categoricas por moda global o `"Unknown"`.

```python
from src.analisis_proyecto.preprocessing.pipeline import impute_median_by_family

descriptor_cols = ["mw_freebase", "alogp", "psa", "hba", "hbd",
                   "aromatic_rings", "rtb", "heavy_atoms", "num_ro5_violations"]
compounds = impute_median_by_family(compounds, descriptor_cols, categorical_cols=[])
assert compounds[descriptor_cols].isna().sum().sum() == 0
```

**Por que mediana por familia y no global:** un organofosforado (MW ~300, PSA alto) tiene propiedades muy distintas a un piretroide (MW ~400, PSA bajo). Imputar con la mediana de la familia preserva la estructura intrinseca del dato. Nota de honestidad: a nivel compuesto el `n` por familia es pequeno; el fallback global cubre familias con muy pocos compuestos.

### Paso 10 — Verificacion y reporte de imputacion

**Funcion:** `pchembl_imputation_report(df)` en `preprocessing/pipeline.py:492`. Se mantiene el diagnostico, ahora coherente porque corre sobre el mismo dataframe dedup que alimenta ambas tablas.

```python
from src.analisis_proyecto.preprocessing.pipeline import pchembl_imputation_report

print(pchembl_imputation_report(activities_clean))   # n_total, n_imputed, pct_imputed
assert compounds[descriptor_cols].isna().sum().sum() == 0, "Quedan NaN en descriptores"
```

### Paso 11 — Guardado

```python
compounds.to_csv("data/processed/compounds_features.csv", index=False)
audit_df.to_csv("outputs/chembl/results/nan_audit.csv", index=False)
dup_report.to_csv("outputs/chembl/results/dedup_report.csv", index=False)
```

Las salidas canonicas de esta fase son `activities_clean.csv` (nivel medicion) y `compounds_features.csv` (nivel compuesto, 107 filas).

---

## 4. Trabajo por rol

### Ingeniero de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Aplicar `filter_potential_duplicates` como primer paso | `dedup_report.csv` (~801 filas eliminadas) |
| 2 | Diagnosticar tipos de datos y NaN sobre el dedup | Tabla `summary_statistics` en notebook |
| 3 | Ejecutar `drop_columns_high_nan()` | Tabla de auditoria con decisiones |
| 4 | Implementar `build_compound_features()` (nueva) | `compounds_features.csv` con 107 filas |
| 5 | Imputar descriptores a nivel compuesto con `impute_median_by_family()` | Tabla sin NaN residuales |
| 6 | Generar `activities_clean.csv` + `compounds_features.csv` | Dos CSV en `data/processed/` |

### Analista de Datos (APOYO)

| Tarea | Entregable |
|---|---|
| Generar visualizaciones missingno | 3-4 figuras en `outputs/chembl/figures/` |
| Interpretar patrones de faltantes | Parrafo explicativo en notebook |
| Verificar que la imputacion no distorsiona | Comparar distribuciones pre/post a nivel compuesto |
| Documentar la censura `standard_relation` | Conteo de `=`/`>`/`<` |

### Cientifico de Datos (REVISOR)

| Tarea | Entregable |
|---|---|
| Validar coherencia de tamanos entre tablas | 107 compuestos = filas de `compounds_features` |
| Confirmar que dedup se aplico antes de agregar | Verificar `n_activities` consistente con dedup |
| Verificar que descriptores sobrevivieron | Lista de columnas post-limpieza |

### ML Engineer

No participa directamente en esta fase. Consume `compounds_features.csv` en el baseline predictivo de Fase 4 (§12, P6).

---

## 5. Decisiones documentadas

| Decision | Justificacion | Alternativa descartada |
|---|---|---|
| Dedup antes de agregar | Corrige el bug de 801 duplicados sin eliminar; hace coherentes ambas tablas | Ignorar `potential_duplicate` (pipeline anterior) |
| Unidad = compuesto | Los descriptores son constantes por molecula; solo hay 107 vectores reales | Analisis a nivel fila (repite el mismo dato) |
| Imputar a nivel compuesto | Cada molecula se imputa una vez, no cientos | Imputar sobre 3.608 filas |
| Mediana por familia | Preserva estructura fisicoquimica de la familia | Media global (sesgada por outliers) |
| Conservar y segregar censura | `>`/`<` no son comparables con `=` | Tratar todo como valor puntual |
| Umbral NaN = 250 filas | Requisito del curso (~7% del dataset) | Umbral porcentual |
| No usar split por filas | Fuga de datos → metricas infladas | Split aleatorio 80/20 (descartado como default) |

---

## 6. Esquema de salida (dos tablas)

### `data/processed/activities_clean.csv` (nivel MEDICION, dedup)

| Grupo | Columnas |
|---|---|
| Identificacion | `chembl_id`, `compound_name`, `family` |
| Diana | `target_chembl_id`, `target_name`, `target_type` |
| Endpoint | `standard_type`, `standard_relation`, `standard_value`, `standard_units` |
| Bioactividad | `pchembl_value`, `pchembl_imputed` |
| Ensayo | `assay_type` |

Uso: P2 (promiscuidad), P4 (endpoints/dianas).

### `data/processed/compounds_features.csv` (nivel COMPUESTO, **107 filas**)

| Grupo | Columnas |
|---|---|
| Identificacion | `chembl_id`, `compound_name`, `family`, `smiles` |
| Descriptores (constantes) | `mw_freebase`, `alogp`, `psa`, `hba`, `hbd`, `aromatic_rings`, `rtb`, `heavy_atoms`, `num_ro5_violations` |
| Agregados de bioactividad | `pchembl_median`, `pchembl_std`, `n_activities`, `n_targets`, `n_assay_types`, `n_standard_types`, `pct_active` |

Uso: P1, P3, P5 y **P6** (baseline honesto, Fase 4 §12). Es la **unidad principal** del proyecto.

---

## 7. Ejecucion

```bash
# Ejecutar notebook completo
jupyter notebook "proyecto analisis/notebooks/fase2_limpieza.ipynb"

# Pipeline completo desde terminal (dos tablas)
python -c "
from src.analisis_proyecto.preprocessing.pipeline import (
    load_bioactivity, filter_potential_duplicates, drop_columns_high_nan,
    impute_median_by_family, build_compound_features, pchembl_imputation_report,
)
df = load_bioactivity('data/raw/chembl_panama_bioactivity.csv')

# 1) Dedup PRIMERO (corrige bug de ~801 duplicados)
df, dup_report = filter_potential_duplicates(df)
print(dup_report.to_string(index=False))

# 2) Marcar censura
df['is_censored'] = df['standard_relation'].fillna('=').ne('=')

# 3) Reducir columnas con muchos NaN
df, audit = drop_columns_high_nan(df, threshold=250)

# 4) Tabla de medicion
act_cols = ['chembl_id','compound_name','family','target_chembl_id','target_name',
            'target_type','standard_type','standard_relation','standard_value',
            'standard_units','pchembl_value','pchembl_imputed','assay_type']
activities = df[[c for c in act_cols if c in df.columns]].copy()
activities.to_csv('data/processed/activities_clean.csv', index=False)

# 5) Tabla de compuesto (nueva funcion) + imputacion a nivel compuesto
compounds = build_compound_features(activities)
desc = ['mw_freebase','alogp','psa','hba','hbd','aromatic_rings','rtb','heavy_atoms','num_ro5_violations']
compounds = impute_median_by_family(compounds, desc, categorical_cols=[])
compounds.to_csv('data/processed/compounds_features.csv', index=False)

print('activities:', activities.shape, '| compounds:', compounds.shape)
print(pchembl_imputation_report(activities))
assert len(compounds) == 107
assert compounds[desc].isna().sum().sum() == 0
"
```

---

## 8. Criterios de exito

- [ ] De-duplicacion aplicada ANTES de construir las tablas (`filter_potential_duplicates`, ~801 filas eliminadas y reportadas)
- [ ] `data/processed/activities_clean.csv` generado (nivel medicion, dedup, con `standard_relation`)
- [ ] `data/processed/compounds_features.csv` generado con exactamente **107 filas**
- [ ] 0 NaN en los descriptores moleculares de `compounds_features.csv`
- [ ] Agregados de bioactividad presentes (`pchembl_median`, `pchembl_std`, `n_activities`, `n_targets`, `n_assay_types`, `n_standard_types`, `pct_active`)
- [ ] Valores censurados (`>`/`<`) marcados/segregados y documentados
- [ ] Tamanos coherentes entre fases (dedup unica que alimenta ambas tablas; sin discrepancia 2.807 vs 3.608)
- [ ] Tabla de auditoria de columnas eliminadas documentada
- [ ] Al menos 3 visualizaciones missingno generadas
- [ ] Comparacion distribucion pre/post imputacion a nivel compuesto para 2 variables

---

## 9. Troubleshooting

| Problema | Causa probable | Solucion |
|---|---|---|
| `compounds_features` no tiene 107 filas | Dedup no aplicada o `groupby` incorrecto | Verificar que se agrupa por `chembl_id` sobre el dataframe dedup |
| Quedan filas `potential_duplicate=1` | No se llamo a `filter_potential_duplicates` | Aplicarla como PRIMER paso |
| Descriptores con `nunique>1` por compuesto | Fila corrupta o merge erroneo en Fase 1 | Revisar trazabilidad; tomar primer valor no nulo por `chembl_id` |
| NaN residuales en descriptores | Familia sin valores para esa columna | Fallback a mediana global (ya implementado) |
| Potencia sesgada por censura | Se incluyeron valores `>`/`<` en la mediana | Excluir `is_censored` del calculo de `pchembl_median` |
| `missingno` / `upsetplot` no instalado | Falta dependencia | `pip install missingno upsetplot>=0.9` |
| `family` tiene NaN | Error en Fase 1 | Verificar `MIDA_FAMILY_MAP` asigna todas las familias |

---

*Fase anterior:* [Fase 1 — Adquisicion de datos](fase1_adquisicion_datos.md)  
*Siguiente fase:* [Fase 3 — Analisis exploratorio](fase3_eda.md)  
*Baseline P6:* [Fase 4 §12 — Baseline predictivo honesto](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6)
