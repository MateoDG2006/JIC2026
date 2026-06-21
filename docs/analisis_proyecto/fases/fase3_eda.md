# Fase 3 — Analisis Exploratorio de Datos (Flujo B, parte 2)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Descubrir patrones, correlaciones y estructura del dataset ChEMBL limpio |
| **Duracion** | 2-3 dias |
| **Entrada** | `data/processed/chembl_clean.csv` |
| **Salida** | Figuras en `outputs/chembl/figures/`, tablas de correlacion |
| **Rol lider** | Analista de Datos |
| **Notebook** | `notebooks/proyecto analisis de datos/fase3_eda.ipynb` |

---

## 1. Contexto

El EDA responde tres preguntas del curso:
1. Que distribuciones tienen las variables? (tendencia central, dispersion, forma)
2. Existen correlaciones entre descriptores moleculares y potencia?
3. Como varian los datos entre familias de plaguicidas?

El EDA NO entrena modelos — solo describe y visualiza. Los hallazgos aqui informan las decisiones de la Fase 4 (modelado).

---

## 2. Medidas de tendencia central (Seccion 1 del notebook)

### Funcion: `summary_statistics(df)`

**Ubicacion:** `chembl_preprocessing.py:45`

Calcula para cada columna numerica:

| Estadistico | Metodo pandas |
|---|---|
| Media | `s.mean()` |
| Mediana | `s.median()` |
| Moda | `s.mode().iloc[0]` |
| Desviacion estandar | `s.std()` |
| N faltantes | `s.isna().sum()` |
| % faltantes | `s.isna().mean() * 100` |

**Resultado esperado** (valores aproximados del dataset real):

| Variable | Media | Mediana | Std |
|---|---|---|---|
| pchembl_value | 5.2 | 5.1 | 1.3 |
| mw_freebase | 330 | 310 | 120 |
| alogp | 2.8 | 3.1 | 2.0 |
| psa | 65 | 55 | 40 |
| hba | 4.5 | 4.0 | 2.5 |
| hbd | 1.2 | 1.0 | 1.1 |
| aromatic_rings | 1.8 | 2.0 | 1.0 |
| heavy_atoms | 22 | 21 | 8 |

---

## 3. Distribuciones y visualizaciones (Seccion 1)

### 3.1 Histogramas de variables continuas

```python
import matplotlib.pyplot as plt
import seaborn as sns

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
num_cols = ["pchembl_value", "mw_freebase", "alogp", "psa",
            "hba", "hbd", "aromatic_rings", "heavy_atoms"]

for ax, col in zip(axes.flat, num_cols):
    sns.histplot(df_clean[col], bins=30, kde=True, ax=ax)
    ax.set_title(col)
    ax.axvline(df_clean[col].median(), color='red', linestyle='--', label='mediana')
    ax.legend()

plt.tight_layout()
plt.savefig("outputs/chembl/figures/histograms_descriptors.png", dpi=150)
```

### 3.2 Boxplots por familia quimica

```python
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for ax, col in zip(axes, ["pchembl_value", "alogp", "mw_freebase"]):
    sns.boxplot(data=df_clean, x="family", y=col, ax=ax)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_title(f"{col} por familia")

plt.tight_layout()
plt.savefig("outputs/chembl/figures/boxplots_by_family.png", dpi=150)
```

**Que buscar:**
- Organofosforados con pChEMBL generalmente bajo (~4-5) — menos potentes en dianas inespecificas
- Azoles con pChEMBL mas alto (~6-7) — inhibidores potentes de CYP
- Piretroides con MW alto y alogp alto — alta lipofilicidad

### 3.3 Conteo de variables categoricas

```python
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
cat_cols = ["activity_class", "standard_type", "assay_type", "family"]

for ax, col in zip(axes.flat, cat_cols):
    df_clean[col].value_counts().plot(kind="barh", ax=ax)
    ax.set_title(f"Frecuencia: {col}")

plt.tight_layout()
plt.savefig("outputs/chembl/figures/categorical_counts.png", dpi=150)
```

### 3.4 Desbalanceo de clases

```python
class_counts = df_clean["activity_class"].value_counts()
print(f"Active:   {class_counts.get('Active', 0)}")
print(f"Inactive: {class_counts.get('Inactive', 0)}")
print(f"Ratio:    {class_counts.get('Active', 0) / class_counts.get('Inactive', 1):.2f}")
```

**Valor tipico:** ~30% Active, ~70% Inactive (desbalanceo moderado). Esto justifica `class_weight="balanced"` en la Fase 4.

---

## 4. Analisis de correlacion (Seccion 3)

### Funcion: `correlation_with_target(df, target, features)`

**Ubicacion:** `chembl_preprocessing.py:310`

```python
def correlation_with_target(
    df: pd.DataFrame,
    target: str = "pchembl_value",
    features: list[str] | None = None,
) -> pd.DataFrame:
    """
    Calcula Pearson y Spearman para cada feature vs el target.
    Retorna DataFrame ordenado por |Spearman| descendente.
    """
    if features is None:
        features = df.select_dtypes(include="number").columns.tolist()
        features = [f for f in features if f != target]
    
    rows = []
    for feat in features:
        valid = df[[feat, target]].dropna()
        if len(valid) < 10:
            continue
        pearson = valid[feat].corr(valid[target], method="pearson")
        spearman = valid[feat].corr(valid[target], method="spearman")
        rows.append({
            "feature": feat,
            "pearson": round(pearson, 4),
            "spearman": round(spearman, 4),
            "abs_spearman": abs(round(spearman, 4)),
            "n_valid": len(valid),
        })
    
    return (pd.DataFrame(rows)
              .sort_values("abs_spearman", ascending=False)
              .reset_index(drop=True))
```

### Resultado esperado (valores aproximados)

| Feature | Pearson | Spearman | Interpretacion |
|---|---|---|---|
| standard_value | -0.85 | -0.90 | Anticorrelacion esperada (pChEMBL = -log10) |
| alogp | 0.15 | 0.18 | Lipofilicidad debilmente correlacionada |
| mw_freebase | 0.10 | 0.12 | Peso molecular sin relacion clara |
| psa | -0.08 | -0.10 | Area polar debilmente anticorrelacionada |
| heavy_atoms | 0.09 | 0.11 | Similar a MW |

**Insight clave:** Las correlaciones bajas entre descriptores moleculares y pChEMBL sugieren que la potencia depende mas de la interaccion especifica molecula-diana que de propiedades globales. Esto es esperado en quimioinformatica y motiva el uso de GNN (Fase III del proyecto JIC).

### Heatmap de correlacion

```python
import numpy as np

descriptor_cols = ["mw_freebase", "alogp", "psa", "hba", "hbd",
                   "aromatic_rings", "heavy_atoms", "rtb", "pchembl_value"]
corr_matrix = df_clean[descriptor_cols].corr(method="spearman")

mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f",
            cmap="RdBu_r", center=0, ax=ax)
ax.set_title("Correlacion Spearman — Descriptores moleculares")
plt.tight_layout()
plt.savefig("outputs/chembl/figures/correlation_heatmap.png", dpi=150)
```

### Pairplot de top features

```python
top_features = corr_df.head(4)["feature"].tolist() + ["pchembl_value"]
sns.pairplot(df_clean[top_features + ["activity_class"]],
             hue="activity_class", palette={"Active": "red", "Inactive": "blue"},
             plot_kws={"alpha": 0.4, "s": 10})
plt.savefig("outputs/chembl/figures/pairplot_top_features.png", dpi=150)
```

---

## 5. Analisis por familia quimica

```python
family_summary = (df_clean.groupby("family")
    .agg(
        n_registros=("pchembl_value", "count"),
        pchembl_mean=("pchembl_value", "mean"),
        pchembl_std=("pchembl_value", "std"),
        pct_active=("activity_class", lambda x: (x == "Active").mean() * 100),
        mw_mean=("mw_freebase", "mean"),
        alogp_mean=("alogp", "mean"),
    )
    .round(2)
    .sort_values("n_registros", ascending=False)
)
```

**Resultado esperado:**

| Familia | N registros | pChEMBL medio | % Active | MW medio |
|---|---|---|---|---|
| Azole_fungicides | ~800 | 5.8 | 35% | 307 |
| Organophosphates | ~700 | 4.9 | 22% | 275 |
| Pyrethroids | ~600 | 5.3 | 28% | 415 |
| Herbicides | ~500 | 4.5 | 18% | 210 |
| Carbamates | ~400 | 5.0 | 25% | 200 |
| Triazines | ~350 | 4.7 | 20% | 215 |
| Fungicides | ~250 | 5.1 | 24% | 265 |

---

## 6. Trabajo por rol

### Analista de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Generar tabla `summary_statistics` | Tabla en Seccion 1 del notebook |
| 2 | Crear histogramas de distribuciones | `histograms_descriptors.png` |
| 3 | Crear boxplots por familia | `boxplots_by_family.png` |
| 4 | Calcular correlaciones Pearson + Spearman | Tabla ordenada por \|Spearman\| |
| 5 | Generar heatmap de correlacion | `correlation_heatmap.png` |
| 6 | Generar pairplot | `pairplot_top_features.png` |
| 7 | Documentar hallazgos en Markdown | Interpretaciones en celdas del notebook |
| 8 | Analisis por familia quimica | Tabla resumen por familia |

### Cientifico de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Interpretar correlaciones | Explicar por que las correlaciones son bajas (implicacion quimica) |
| Sugerir features para modelado | Basado en correlaciones, decidir que columnas incluir |
| Verificar desbalanceo | Proponer estrategia (class_weight vs SMOTE vs nada) |

### Ingeniero de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar que `chembl_clean.csv` esta correcto | Confirmacion de 0 NaN |
| Confirmar que las figuras se guardan | Verificar `outputs/chembl/figures/` |

### ML Engineer

No participa directamente.

---

## 7. Figuras requeridas

| # | Figura | Archivo | Proposito |
|---|---|---|---|
| 1 | Histogramas de descriptores | `histograms_descriptors.png` | Distribucion de cada variable |
| 2 | Boxplots por familia | `boxplots_by_family.png` | Variacion inter-familia |
| 3 | Conteo de categoricas | `categorical_counts.png` | Frecuencia de cada clase |
| 4 | Heatmap de correlacion | `correlation_heatmap.png` | Relaciones entre variables |
| 5 | Pairplot top features | `pairplot_top_features.png` | Relacion bivariada con color por clase |
| 6 | Patron de faltantes | `missing_patterns.png` | De la Fase 2, pero se documenta aqui |

---

## 8. Ejecucion

```bash
# Ejecutar notebook completo
jupyter notebook "notebooks/proyecto analisis de datos/fase3_eda.ipynb"

# Verificar que las figuras existen
ls outputs/chembl/figures/

# Generar solo correlaciones desde terminal
python -c "
from src.analisis_proyecto.chembl_preprocessing import correlation_with_target
import pandas as pd
df = pd.read_csv('data/processed/chembl_clean.csv')
corr = correlation_with_target(df)
print(corr.to_string())
"
```

---

## 9. Criterios de exito

- [ ] Tabla de tendencia central con media, mediana, moda, std para cada variable
- [ ] Al menos 6 figuras generadas y guardadas en `outputs/chembl/figures/`
- [ ] Correlacion Pearson y Spearman documentadas (requisito: minimo 2 metodos)
- [ ] Heatmap triangular de correlacion generado
- [ ] Interpretacion escrita de hallazgos principales (al menos 3 insights)
- [ ] Desbalanceo de clases cuantificado
- [ ] Analisis por familia quimica documentado

---

## 10. Insights esperados para el informe

1. **Correlaciones bajas descriptor-potencia:** Los descriptores moleculares globales (MW, LogP, PSA) explican poco la potencia. Esto es normal — la potencia depende de la geometria de union molecula-diana, no de propiedades bulk.

2. **Desbalanceo moderado:** ~70% Inactive / ~30% Active con umbral pChEMBL >= 6.0. El desbalanceo no es extremo, pero justifica `class_weight="balanced"`.

3. **Variacion inter-familia:** Los azoles tienden a ser mas potentes (pChEMBL alto) porque son inhibidores enzimaticos disenados para unirse a dianas especificas. Los herbicidas tienen pChEMBL bajo porque sus dianas principales estan en plantas, no en los ensayos bioquimicos humanos de ChEMBL.

4. **Colinealidad MW-heavy_atoms:** Correlacion esperada >0.95 (un atomo pesado adicional aumenta MW). Usar solo una de las dos en el modelo.

---

*Fase anterior:* [Fase 2 — Limpieza de datos](fase2_limpieza_datos.md)  
*Siguiente fase:* [Fase 4 — Modelado supervisado](fase4_modelado.md)
