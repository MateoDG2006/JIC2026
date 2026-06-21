# Fase 2 — Limpieza e Ingenieria de Datos (Flujo B, parte 1)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Limpiar, imputar y preparar el dataset ChEMBL para modelado supervisado |
| **Duracion** | 2-3 dias |
| **Entrada** | `data/raw/chembl_panama_bioactivity.csv` (~3,608 filas, 33 columnas) |
| **Salida** | `data/processed/chembl_clean.csv` (mismo numero de filas, columnas reducidas) |
| **Rol lider** | Ingeniero de Datos |
| **Notebook** | `notebooks/proyecto analisis de datos/fase2_limpieza.ipynb` |
| **Modulo** | `src/analisis_proyecto/chembl_preprocessing.py` |

---

## 1. Contexto

El CSV crudo de la Fase 1 contiene columnas con porcentajes variables de NaN, tipos de datos mixtos y columnas que no aportan al modelado. Esta fase transforma el dataset crudo en uno listo para EDA y modelos supervisados, siguiendo los requisitos del curso:

- Detectar y visualizar patrones de faltantes
- Eliminar columnas con mas de 250 NaN
- Imputar valores faltantes con al menos dos estrategias justificadas
- Documentar cada decision

### Decisiones metodologicas (resumen consolidado)

Estas decisiones se aplican aqui y se arrastran a Fase 3 (EDA) y Fase 4 (modelado). Se documentan juntas para evitar dispersion entre fases:

| Tema | Decision |
|---|---|
| Split train/test (Fase 4) | Aleatorio por filas, 80/20, `random_state=42` |
| Imputacion numerica | Mediana por `family` (fallback: mediana global) |
| Imputacion categorica | Moda global o `"Unknown"` |
| Columnas con >250 NaN | Eliminar (requisito del curso) |
| Clasificacion (Fase 4) | Random Forest + SVM (RBF) |
| Regresion (Fase 4) | SVR (RBF) + Random Forest Regressor |
| Umbral Active | pChEMBL >= 6 (definido en Fase 1) |

> **Nota sobre el split por filas:** el mismo plaguicida puede aparecer en train y test con descriptores moleculares identicos (solo cambia la diana/ensayo). Esto puede **inflar** la accuracy de clasificacion. Se documenta en el notebook y en [METRICAS_EVALUACION.md](../../../mateo_docs/auditorias/METRICAS_EVALUACION.md) como limitacion metodologica.

---

## 2. Esquema del dataset crudo

### Columnas numericas (14)

| Columna | Descripcion | Rango tipico | % NaN esperado |
|---|---|---|---|
| `pchembl_value` | -log10(IC50 en M) — variable objetivo regresion | 3.0 - 10.0 | 0% (filtrada en Fase 1) |
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
| `activity_class` | 2 (Active/Inactive) | Variable objetivo clasificacion |
| `family` | 7 | Familia quimica MIDA |
| `standard_type` | 13 | Tipo de ensayo (IC50, EC50, etc.) |
| `assay_type` | 3-5 | Binding, Functional, ADMET |
| `target_type` | 5-8 | SINGLE PROTEIN, ORGANISM, etc. |
| `organism` | variable | Especie del organismo diana |
| `standard_units` | 3-5 | nM, uM, ug/mL |
| `standard_relation` | 1 (solo '=') | Filtrada en Fase 1 |

### Columnas de identificacion (no para modelado)

| Columna | Proposito |
|---|---|
| `compound_name` | Nombre del plaguicida |
| `chembl_id` | ID ChEMBL de la molecula |
| `activity_id` | ID unico de la medicion |
| `target_chembl_id` | ID ChEMBL de la diana |
| `target_name` | Nombre de la diana biologica |
| `assay_chembl_id` | ID del ensayo |
| `bao_label` | Formato del bioensayo |
| `data_validity_comment` | Comentario de calidad |
| `activity_comment` | Comentario del experimentador |

---

## 3. Procedimiento paso a paso

### Paso 1 — Carga y tipado

**Funcion:** `load_bioactivity(path)` no existe como funcion dedicada; se usa `pd.read_csv()` directamente en el notebook.

```python
import pandas as pd

df = pd.read_csv("data/raw/chembl_panama_bioactivity.csv")
print(f"Shape: {df.shape}")
print(f"Dtypes:\n{df.dtypes}")
```

Verificaciones:
- `pchembl_value` debe ser float64
- `activity_class` debe ser object/str con valores {Active, Inactive}
- `family` debe tener exactamente 7 valores unicos

### Paso 2 — Diagnostico de faltantes

**Funcion:** `summary_statistics(df)` en `chembl_preprocessing.py:45`

```python
def summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula media, mediana, moda y std para columnas numericas."""
    num_cols = df.select_dtypes(include="number").columns
    stats = []
    for c in num_cols:
        s = df[c]
        stats.append({
            "column": c,
            "mean": s.mean(),
            "median": s.median(),
            "mode": s.mode().iloc[0] if not s.mode().empty else None,
            "std": s.std(),
            "n_missing": s.isna().sum(),
            "pct_missing": round(s.isna().mean() * 100, 1),
        })
    return pd.DataFrame(stats)
```

### Paso 3 — Visualizacion de faltantes (requisito del curso)

Se requieren al menos 3 visualizaciones de faltantes. Herramientas usadas:

| Visualizacion | Libreria | Proposito |
|---|---|---|
| Matriz de nulidad | `missingno.matrix(df)` | Patron visual de NaN por fila |
| Barras de completitud | `missingno.bar(df)` | Porcentaje de datos presentes por columna |
| Heatmap de co-ocurrencia | `missingno.heatmap(df)` | Correlacion entre columnas con NaN |
| UpSet plot | `upsetplot` | Combinaciones de patrones de faltantes |

```python
import missingno as msno
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(20, 6))
msno.matrix(df, ax=axes[0], sparkline=False)
msno.bar(df, ax=axes[1])
msno.heatmap(df, ax=axes[2])
plt.tight_layout()
plt.savefig("outputs/chembl/figures/missing_patterns.png", dpi=150)
```

### Paso 4 — Eliminacion de columnas con alto NaN

**Funcion:** `drop_columns_high_nan(df, threshold=250)` en `chembl_preprocessing.py:78`

```python
def drop_columns_high_nan(
    df: pd.DataFrame,
    threshold: int = 250,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Elimina columnas con mas de `threshold` valores NaN.
    
    Retorna:
        df_dropped: DataFrame sin las columnas eliminadas
        audit_df:   DataFrame con reporte de decision por columna
    """
    nan_counts = df.isna().sum()
    audit_rows = []
    drop_cols = []
    
    for col in df.columns:
        n_nan = nan_counts[col]
        pct = round(n_nan / len(df) * 100, 1)
        decision = "eliminar" if n_nan > threshold else "conservar"
        if decision == "eliminar":
            drop_cols.append(col)
        audit_rows.append({
            "column": col,
            "n_nan": n_nan,
            "pct_nan": pct,
            "decision": decision,
        })
    
    audit_df = pd.DataFrame(audit_rows)
    df_dropped = df.drop(columns=drop_cols)
    return df_dropped, audit_df
```

Columnas tipicamente eliminadas:

| Columna | % NaN tipico | Razon |
|---|---|---|
| `cx_logp` | ~40% | Redundante con `alogp` |
| `cx_logd` | ~40% | Dato ChemAxon opcional |
| `activity_comment` | ~70% | Texto libre, no modelable |
| `data_validity_comment` | ~95% | Solo presente en datos dudosos |
| `molecular_species` | ~30% | Categorica con alta cardinalidad |

### Paso 5 — Imputacion

**Funcion:** `impute_median_by_family(df, numeric_cols, categorical_cols)` en `chembl_preprocessing.py:120`

```python
def impute_median_by_family(
    df: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
    group_col: str = "family",
) -> pd.DataFrame:
    """
    Imputa NaN con mediana por familia quimica (numericas)
    y moda global (categoricas).
    
    Estrategia:
        1. Para cada familia, calcular mediana de cada columna numerica
        2. Llenar NaN con la mediana de su familia
        3. Si la familia completa es NaN, usar mediana global
        4. Categoricas: moda global o "Unknown"
    """
    df_out = df.copy()
    
    for col in numeric_cols:
        if col not in df_out.columns:
            continue
        group_medians = df_out.groupby(group_col)[col].transform("median")
        df_out[col] = df_out[col].fillna(group_medians)
        global_median = df_out[col].median()
        df_out[col] = df_out[col].fillna(global_median)
    
    for col in categorical_cols:
        if col not in df_out.columns:
            continue
        mode_val = df_out[col].mode()
        fill = mode_val.iloc[0] if not mode_val.empty else "Unknown"
        df_out[col] = df_out[col].fillna(fill)
    
    return df_out
```

**Por que mediana por familia y no mediana global:**

Los descriptores moleculares varian significativamente entre familias quimicas. Un organofosforado (MW ~300, PSA alto) tiene propiedades distintas a un piretroide (MW ~400, PSA bajo). Imputar con la mediana de la familia preserva la estructura intrinseca del dato.

### Paso 6 — Verificacion post-imputacion

```python
assert df_clean.isna().sum().sum() == 0, "Quedan NaN despues de imputar"
assert len(df_clean) == len(df), "Se perdieron filas en la limpieza"

print("NaN restantes por columna:")
print(df_clean.isna().sum())
print(f"\nShape final: {df_clean.shape}")
```

### Paso 7 — Guardado

```python
df_clean.to_csv("data/processed/chembl_clean.csv", index=False)
audit_df.to_csv("outputs/chembl/results/nan_audit.csv", index=False)
```

---

## 4. Trabajo por rol

### Ingeniero de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Diagnosticar tipos de datos y NaN | Tabla `summary_statistics` en notebook |
| 2 | Implementar `drop_columns_high_nan()` | Tabla de auditoria con decisiones |
| 3 | Implementar `impute_median_by_family()` | Funcion probada sin NaN residuales |
| 4 | Generar `chembl_clean.csv` | CSV limpio en `data/processed/` |
| 5 | Documentar decisiones de limpieza | Celdas Markdown en el notebook |

### Analista de Datos (APOYO)

| Tarea | Entregable |
|---|---|
| Generar visualizaciones missingno | 3-4 figuras en `outputs/chembl/figures/` |
| Interpretar patrones de faltantes | Parrafo explicativo en notebook |
| Verificar que la imputacion no distorsiona | Comparar distribuciones pre/post imputacion |

### Cientifico de Datos (REVISOR)

| Tarea | Entregable |
|---|---|
| Validar que `activity_class` esta balanceada | Conteo Active vs Inactive |
| Verificar que features modelables sobrevivieron | Lista de columnas disponibles post-limpieza |

### ML Engineer

No participa directamente en esta fase.

---

## 5. Decisiones documentadas

| Decision | Justificacion | Alternativa descartada |
|---|---|---|
| Umbral NaN = 250 filas | Requisito del curso, corresponde a ~7% del dataset | Umbral porcentual (ej. 50%) |
| Mediana por familia | Preserva estructura molecular por familia | Media global (sesgada por outliers) |
| Moda para categoricas | Impone la clase mas frecuente | One-hot con categoria "Missing" |
| No eliminar filas | Maximiza tamano del dataset | Drop rows con cualquier NaN |
| Conservar CSV raw | Auditabilidad | Sobrescribir in-place |

---

## 6. Esquema de salida (`chembl_clean.csv`)

Columnas esperadas despues de limpieza (las que sobreviven al filtro de NaN):

| Grupo | Columnas |
|---|---|
| Identificacion | compound_name, chembl_id, family |
| Actividad | pchembl_value, activity_class, standard_type, standard_value |
| Diana | target_chembl_id, target_name, target_type, organism |
| Ensayo | assay_chembl_id, assay_type |
| Descriptores moleculares | mw_freebase, alogp, psa, hba, hbd, aromatic_rings, heavy_atoms, rtb, num_ro5_violations |

Las columnas `cx_logp`, `cx_logd`, `activity_comment`, `data_validity_comment` se eliminan tipicamente.

---

## 7. Ejecucion

```bash
# Ejecutar notebook completo (Secciones 0-2)
jupyter notebook "notebooks/proyecto analisis de datos/fase2_limpieza.ipynb"

# Verificar pipeline desde terminal
python scripts/analisis_proyecto/fase4/verify_flow_b.py

# Solo generar chembl_clean.csv (si ya se tiene el raw)
python -c "
from src.analisis_proyecto.chembl_preprocessing import *
import pandas as pd
df = pd.read_csv('data/raw/chembl_panama_bioactivity.csv')
stats = summary_statistics(df)
print(stats.to_string())
df_dropped, audit = drop_columns_high_nan(df, threshold=250)
num_cols = df_dropped.select_dtypes(include='number').columns.tolist()
cat_cols = ['standard_type', 'assay_type', 'target_type', 'organism']
cat_cols = [c for c in cat_cols if c in df_dropped.columns]
df_clean = impute_median_by_family(df_dropped, num_cols, cat_cols)
df_clean.to_csv('data/processed/chembl_clean.csv', index=False)
print(f'Clean: {df_clean.shape}, NaN: {df_clean.isna().sum().sum()}')
"
```

---

## 8. Criterios de exito

- [ ] 0 valores NaN en `chembl_clean.csv`
- [ ] Tabla de auditoria de columnas eliminadas documentada
- [ ] Al menos 3 visualizaciones de faltantes generadas
- [ ] Distribucion de `activity_class` documentada (desbalanceo)
- [ ] Comparacion distribucion pre/post imputacion para al menos 2 variables
- [ ] `chembl_clean.csv` tiene las mismas filas que el raw (no se eliminaron filas)

---

## 9. Troubleshooting

| Problema | Causa probable | Solucion |
|---|---|---|
| `missingno` no instalado | Falta dependencia | `pip install missingno` |
| `upsetplot` error | Version incompatible | `pip install upsetplot>=0.9` |
| Todas las columnas tienen <250 NaN | Dataset muy limpio | Reducir threshold o documentar |
| `family` tiene NaN | Error en Fase 1 | Verificar `MIDA_FAMILY_MAP` asigna todas las familias |
| Mediana por familia da NaN | Familia con 0 valores en esa columna | Fallback a mediana global (ya implementado) |

---

*Fase anterior:* [Fase 1 — Adquisicion de datos](fase1_adquisicion_datos.md)  
*Siguiente fase:* [Fase 3 — Analisis exploratorio](fase3_eda.md)
