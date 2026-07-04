# Fase 3 — Analisis Exploratorio de Datos (a nivel COMPUESTO)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Caracterizar el perfil fisicoquimico y de bioactividad de los 107 compuestos: distribuciones, promiscuidad, dianas y correlaciones honestas |
| **Duracion** | 2-3 dias |
| **Entrada** | `data/processed/compounds_features.csv` (107 compuestos, principal) + `data/processed/activities_clean.csv` (nivel medicion, para dianas) |
| **Salida** | Figuras en `outputs/chembl/figures/`, tablas de correlacion y de perfil de dianas |
| **Rol lider** | Analista de Datos |
| **Notebook** | `notebooks/fase3_eda.ipynb` |
| **Modulo** | `src/analisis_proyecto/preprocessing/pipeline.py` |

---

## 1. Contexto

Este EDA caracteriza el corpus panameño de plaguicidas a partir de ChEMBL. Responde cuatro preguntas del curso:

1. Como se distribuyen las propiedades fisicoquimicas y como difieren entre familias? (P1)
2. Que compuestos y familias son mas promiscuos, es decir, tocan mas dianas biologicas? (P2)
3. Que relacion descriptiva hay entre descriptores moleculares y potencia mediana por compuesto? (P5)
4. Como es el perfil de dianas y de endpoints del corpus?

El EDA NO entrena modelos — solo describe y visualiza. Los hallazgos aqui informan el analisis multivariado y de contraste de hipotesis de la Fase 4 (PCA, clustering, tests).

### Regla central: la unidad de analisis es el COMPUESTO, no la fila

Todo el EDA fisicoquimico (histogramas, tendencia central, boxplots por familia, correlacion) se hace sobre los **107 compuestos** de `compounds_features.csv`, **no** sobre las 3.608 filas de medicion. Las razones son duras:

- **A nivel fila una sola molecula domina la distribucion.** El corpus tiene 3.608 mediciones pero solo 107 compuestos unicos (media ~34 mediciones/compuesto). Una sola molecula aporta hasta **1.167 filas**: cualquier histograma o boxplot a nivel fila estaria describiendo a ese compuesto, no al corpus.
- **Los descriptores son constantes por compuesto** (`nunique = 1` dentro de cada `chembl_id`). El peso molecular, el AlogP, la PSA, etc. no cambian entre las 34 mediciones de una misma molecula. Promediar histogramas sobre filas solo re-pesa cada compuesto por su numero de ensayos, introduciendo un sesgo puramente muestral.

Por eso el EDA fisicoquimico opera sobre las 107 filas de `compounds_features.csv` (una por compuesto). Solo se mantiene el nivel de **medicion** donde es legitimo: perfil de dianas, promiscuidad y comparacion de endpoints, que provienen de `activities_clean.csv`.

---

## 2. Medidas de tendencia central a nivel compuesto (Seccion 1 del notebook)

### Funcion: `summary_statistics(df)`

**Ubicacion:** `preprocessing/pipeline.py`

Se aplica sobre `compounds_features.csv` (107 filas). Calcula para cada columna numerica:

| Estadistico | Metodo pandas |
|---|---|
| Media | `s.mean()` |
| Mediana | `s.median()` |
| Moda | `s.mode().iloc[0]` |
| Desviacion estandar | `s.std()` |
| N faltantes | `s.isna().sum()` |
| % faltantes | `s.isna().mean() * 100` |

Variables descriptoras (constantes por compuesto): `mw_freebase`, `alogp`, `psa`, `hba`, `hbd`, `aromatic_rings`, `rtb`, `heavy_atoms`, `num_ro5_violations`.

Variables agregadas de bioactividad (una por compuesto): `pchembl_median`, `pchembl_std`, `n_activities`, `n_targets`, `n_assay_types`, `n_standard_types`, `pct_active`.

> **Nota de honestidad:** las tablas de este documento describen el ESQUEMA de la salida (columnas y forma esperada), no valores numericos reales. Los unicos numeros conocidos y verificados del dataset son: 107 compuestos, 3.608 mediciones, 801 posibles duplicados y el conteo de familias (ver Seccion 5). No se reportan medias ni correlaciones inventadas como si fueran resultados.

---

## 3. Distribuciones y visualizaciones a nivel compuesto (Seccion 1)

### 3.1 Histogramas de descriptores (107 puntos por variable)

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

comp = pd.read_csv("data/processed/compounds_features.csv")  # 107 filas

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
num_cols = ["mw_freebase", "alogp", "psa", "hba",
            "hbd", "aromatic_rings", "heavy_atoms", "pchembl_median"]

for ax, col in zip(axes.flat, num_cols):
    sns.histplot(comp[col], bins=25, kde=True, ax=ax)
    ax.set_title(f"{col} (n=107 compuestos)")
    ax.axvline(comp[col].median(), color="red", linestyle="--", label="mediana")
    ax.legend()

plt.tight_layout()
plt.savefig("outputs/chembl/figures/histograms_descriptors.png", dpi=150)
```

Cada histograma tiene exactamente 107 observaciones (una por compuesto). Interpretar la forma (asimetria de MW y PSA, bimodalidad de AlogP por lipofilicidad de piretroides, etc.) sabiendo que ningun compuesto pesa mas que otro.

### 3.2 Boxplots por familia quimica — SIEMPRE reportando n por familia

```python
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# n por familia a nivel COMPUESTO (no fila)
n_fam = comp["family"].value_counts()

for ax, col in zip(axes, ["pchembl_median", "alogp", "mw_freebase"]):
    sns.boxplot(data=comp, x="family", y=col, ax=ax)
    labels = [f"{f}\n(n={n_fam[f]})" for f in [t.get_text() for t in ax.get_xticklabels()]]
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_title(f"{col} por familia (nivel compuesto)")

plt.tight_layout()
plt.savefig("outputs/chembl/figures/family_boxplots_annotated.png", dpi=150)
```

**Advertencia sobre familias pequeñas.** A nivel COMPUESTO el n por familia es mucho menor que a nivel fila. Aunque a nivel fila Herbicides tenga 2.411 mediciones (67%), el numero de *compuestos* distintos por familia es reducido. Cada boxplot debe anotar su n y **no se debe sobre-interpretar** una familia con pocos compuestos. Vigilar especialmente **Carbamates**, que a nivel medicion aporta apenas 106 filas y a nivel compuesto queda con muy pocos representantes: una mediana o un rango intercuartil calculado sobre 2-3 compuestos no es concluyente. Cualquier diferencia entre familias observada aqui se contrasta formalmente en la Fase 4 (Kruskal-Wallis + post-hoc Dunn con correccion Holm y tamaño de efecto).

### 3.3 Distribucion de la PROMISCUIDAD (n_targets por compuesto)

La promiscuidad biologica (polifarmacologia) de un compuesto es el numero de dianas distintas que toca. Vive en la columna `n_targets` de `compounds_features.csv`.

```python
# Distribucion global de promiscuidad
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

sns.histplot(comp["n_targets"], bins=25, ax=axes[0])
axes[0].axvline(comp["n_targets"].median(), color="red", linestyle="--", label="mediana")
axes[0].set_title("Promiscuidad: n_targets por compuesto (n=107)")
axes[0].set_xlabel("n dianas distintas por compuesto")
axes[0].legend()

# Promiscuidad por familia (con n por familia)
order = comp.groupby("family")["n_targets"].median().sort_values(ascending=False).index
sns.boxplot(data=comp, x="family", y="n_targets", order=order, ax=axes[1])
labels = [f"{f}\n(n={n_fam[f]})" for f in order]
axes[1].set_xticklabels(labels, rotation=45, ha="right")
axes[1].set_title("Promiscuidad por familia")

plt.tight_layout()
plt.savefig("outputs/chembl/figures/promiscuity_distribution.png", dpi=150)
```

**Que buscar:** la distribucion de `n_targets` suele ser muy asimetrica (la mayoria de compuestos toca pocas dianas, unos pocos son muy promiscuos — mediana de ~4 dianas/compuesto, con casos de hasta ~133). Identificar que familias concentran los compuestos mas promiscuos. Este eje se relaciona luego con propiedades fisicoquimicas via Spearman en la Fase 4 (P2).

### 3.4 Conteo de variables categoricas (a nivel compuesto)

```python
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, col in zip(axes, ["family", "num_ro5_violations"]):
    comp[col].value_counts().plot(kind="barh", ax=ax)
    ax.set_title(f"Frecuencia por compuesto: {col}")
plt.tight_layout()
plt.savefig("outputs/chembl/figures/categorical_counts.png", dpi=150)
```

> Se elimina el analisis de `activity_class` como target y su "desbalanceo": `activity_class` era una binarizacion circular de `pchembl_value >= 6` (63 de 107 compuestos tienen AMBAS clases segun la diana), por lo que no describe al compuesto sino a la medicion. No se usa como variable descriptiva del corpus.

---

## 4. Perfil de dianas y de endpoints (a nivel MEDICION, desde `activities_clean.csv`)

Esta seccion SI usa el nivel de medicion, porque las dianas y los endpoints son atributos del ensayo, no del compuesto.

### 4.1 Heatmap compuesto × tipo de diana (`target_type`)

```python
act = pd.read_csv("data/processed/activities_clean.csv")  # nivel medicion, dedup

# matriz compuesto x tipo de diana: recuento de mediciones
pivot = (act.pivot_table(index="compound_name",
                         columns="target_type",
                         values="chembl_id",
                         aggfunc="count",
                         fill_value=0))

fig, ax = plt.subplots(figsize=(12, 18))
sns.heatmap(pivot, cmap="viridis", cbar_kws={"label": "n mediciones"}, ax=ax)
ax.set_title("Perfil de dianas: compuesto x target_type")
plt.tight_layout()
plt.savefig("outputs/chembl/figures/heatmap_compound_target.png", dpi=150)
```

**Que buscar:** que compuestos concentran su actividad en un solo tipo de diana (p. ej. `SINGLE PROTEIN`) frente a los que se reparten entre muchos tipos (`ORGANISM`, `CELL-LINE`, etc.). El heatmap hace visible la estructura de polifarmacologia que luego resume `n_targets`.

### 4.2 Perfil de endpoints: distribucion de `standard_type`

```python
fig, ax = plt.subplots(figsize=(10, 6))
act["standard_type"].value_counts().plot(kind="barh", ax=ax)
ax.set_title("Distribucion de endpoints (standard_type) a nivel medicion")
ax.set_xlabel("n mediciones")
plt.tight_layout()
plt.savefig("outputs/chembl/figures/endpoint_distribution.png", dpi=150)
```

**Por que los endpoints NO son comparables entre si.** El `pchembl_value` del corpus mezcla **13 `standard_type` distintos** (Ki, IC50, Potency, EC50, AC50, Kd, LD50, etc.). Estos endpoints miden fenomenos fisicos diferentes: una Ki (constante de inhibicion de union) no es equivalente a una IC50 funcional ni a una LD50 (dosis letal in vivo). Aunque todos se expresen en la escala pChEMBL (-log10 M), agrupar el `pchembl_value` crudo entre endpoints distintos mezcla peras con manzanas. Consecuencia practica para el resto del proyecto:

- **No se agrupa `pchembl_value` crudo** sin estratificar por `standard_type` cuando se comparan potencias.
- El agregado `pchembl_median` por compuesto se reporta como un resumen descriptivo con esta salvedad explicita, y se acompaña de `n_standard_types` para saber cuantos endpoints heterogeneos entraron en cada mediana.
- La comparacion formal de potencia entre familias (Fase 4, P4) se hace controlando por endpoint o reportando la limitacion.

---

## 5. Perfil por familia quimica

Recuento de compuestos y de mediciones por familia. **A nivel fila** el reparto conocido es:

| Familia | N mediciones (fila) | Peso |
|---|---|---|
| Herbicides | 2.411 | 67% |
| Organophosphates | 323 | 9% |
| Pyrethroids | 247 | 7% |
| mixed | 202 | 6% |
| Azole_fungicides | 169 | 5% |
| Triazines | 150 | 4% |
| Carbamates | 106 | 3% |

Este reparto a nivel fila esta fuertemente desbalanceado y NO debe usarse para describir el espacio quimico. El resumen relevante para el EDA es a nivel COMPUESTO:

```python
family_summary = (comp.groupby("family")
    .agg(
        n_compuestos=("chembl_id", "nunique"),
        pchembl_median_of_medians=("pchembl_median", "median"),
        mw_median=("mw_freebase", "median"),
        alogp_median=("alogp", "median"),
        n_targets_median=("n_targets", "median"),
    )
    .round(2)
    .sort_values("n_compuestos", ascending=False)
)
```

La tabla resultante DEBE encabezarse con `n_compuestos` para que quede claro sobre cuantas moleculas se calcula cada estadistico de familia. Familias con pocos compuestos (p. ej. Carbamates) se marcan como no concluyentes.

---

## 6. Analisis de correlacion honesto (a nivel compuesto)

### Funcion: `correlation_with_target(df, target, features)`

**Ubicacion:** `preprocessing/pipeline.py`

Se aplica sobre `compounds_features.csv` con `target="pchembl_median"` (la potencia mediana por compuesto), NO sobre `pchembl_value` a nivel fila. Esto evita que un compuesto con 1.167 mediciones domine la correlacion.

```python
def correlation_with_target(
    df: pd.DataFrame,
    target: str = "pchembl_median",
    features: list[str] | None = None,
) -> pd.DataFrame:
    """
    Calcula Pearson y Spearman de cada descriptor vs el target,
    a nivel COMPUESTO. Retorna DataFrame ordenado por |Spearman| desc.
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

### Esquema de la salida

| Feature | Pearson | Spearman | n_valid | Lectura |
|---|---|---|---|---|
| alogp | (esperado) | (esperado) | 107 | Lipofilicidad vs potencia mediana |
| mw_freebase | (esperado) | (esperado) | 107 | Tamaño molecular |
| psa | (esperado) | (esperado) | 107 | Area polar |
| hba / hbd | (esperado) | (esperado) | 107 | Enlaces de H |
| heavy_atoms | (esperado) | (esperado) | 107 | Correlado con MW |

**Esto es correlacion descriptiva honesta, NO un modelo.** No hay entrenamiento ni prediccion: solo se mide la asociacion monotona (Spearman) entre cada descriptor y la potencia mediana de los 107 compuestos. Se retira del EDA la correlacion `pchembl_value` vs `standard_value` (Spearman ~-0.90): era una identidad matematica (`pChEMBL = -log10(standard_value)`), no un hallazgo quimico, y ademas mezclaba endpoints no comparables.

### Heatmap de correlacion entre descriptores

```python
import numpy as np

descriptor_cols = ["mw_freebase", "alogp", "psa", "hba", "hbd",
                   "aromatic_rings", "rtb", "heavy_atoms",
                   "n_targets", "pchembl_median"]
corr_matrix = comp[descriptor_cols].corr(method="spearman")

mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f",
            cmap="RdBu_r", center=0, ax=ax)
ax.set_title("Correlacion Spearman entre descriptores (nivel compuesto)")
plt.tight_layout()
plt.savefig("outputs/chembl/figures/correlation_heatmap.png", dpi=150)
```

**Utilidad para la Fase 4:** detectar colinealidad entre descriptores (tipicamente MW y heavy_atoms) para decidir que variables entran al PCA/clustering sin redundancia.

---

## 7. Trabajo por rol

### Analista de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Generar `summary_statistics` sobre los 107 compuestos | Tabla en Seccion 1 del notebook |
| 2 | Histogramas de descriptores (107 puntos c/u) | `histograms_descriptors.png` |
| 3 | Boxplots por familia anotando n por familia | `family_boxplots_annotated.png` |
| 4 | Distribucion de promiscuidad (n_targets) global y por familia | `promiscuity_distribution.png` |
| 5 | Heatmap compuesto x target_type | `heatmap_compound_target.png` |
| 6 | Distribucion de endpoints (standard_type) | `endpoint_distribution.png` |
| 7 | Correlacion honesta descriptores vs pchembl_median | Tabla ordenada por \|Spearman\| |
| 8 | Heatmap de correlacion entre descriptores | `correlation_heatmap.png` |
| 9 | Perfil por familia a nivel compuesto | Tabla con `n_compuestos` primero |
| 10 | Documentar hallazgos en Markdown | Interpretaciones en el notebook |

### Cientifico de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Interpretar correlaciones y promiscuidad | Explicar lectura quimica de las asociaciones (sin sobre-interpretar) |
| Seleccionar variables para Fase 4 | Descriptores no redundantes para PCA/clustering |
| Justificar no comparabilidad de endpoints | Argumentar por que no se agrupa pchembl crudo entre standard_type |

### Ingeniero de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar `compounds_features.csv` (107 filas) | Confirmar 1 fila por compuesto y descriptores nunique=1 por chembl_id en el origen |
| Verificar `activities_clean.csv` dedup | Confirmar que `filter_potential_duplicates` se aplico (801 duplicados fuera) |
| Confirmar que las figuras se guardan | Verificar `outputs/chembl/figures/` |

### ML Engineer

No participa directamente en esta fase.

---

## 8. Figuras requeridas

| # | Figura | Archivo | Nivel | Proposito |
|---|---|---|---|---|
| 1 | Histogramas de descriptores | `histograms_descriptors.png` | Compuesto | Distribucion de cada variable (n=107) |
| 2 | Boxplots por familia anotados | `family_boxplots_annotated.png` | Compuesto | Variacion inter-familia con n por grupo |
| 3 | Distribucion de promiscuidad | `promiscuity_distribution.png` | Compuesto | n_targets global y por familia |
| 4 | Heatmap compuesto x diana | `heatmap_compound_target.png` | Medicion | Perfil de dianas / polifarmacologia |
| 5 | Distribucion de endpoints | `endpoint_distribution.png` | Medicion | Frecuencia de standard_type |
| 6 | Conteo de categoricas | `categorical_counts.png` | Compuesto | Familia y violaciones de Ro5 |
| 7 | Heatmap de correlacion | `correlation_heatmap.png` | Compuesto | Colinealidad y asociacion con potencia |

---

## 9. Ejecucion

```bash
# Ejecutar notebook completo
jupyter notebook "proyecto analisis/notebooks/fase3_eda.ipynb"

# Verificar que las figuras existen
ls outputs/chembl/figures/

# Correlacion honesta a nivel compuesto desde terminal
python -c "
from src.analisis_proyecto.preprocessing.pipeline import correlation_with_target
import pandas as pd
comp = pd.read_csv('data/processed/compounds_features.csv')
print('n compuestos:', len(comp))
corr = correlation_with_target(comp, target='pchembl_median')
print(corr.to_string())
"
```

---

## 10. Criterios de exito

- [ ] Tabla de tendencia central (media, mediana, moda, std) calculada sobre los **107 compuestos**, no sobre las 3.608 filas
- [ ] EDA fisicoquimico realizado a nivel compuesto, con justificacion escrita de por que no a nivel fila (dominancia de una molecula con 1.167 filas; descriptores nunique=1)
- [ ] Distribucion de promiscuidad (`n_targets`) documentada, global y por familia (`promiscuity_distribution.png`)
- [ ] Heatmap compuesto × target_type generado desde `activities_clean.csv` (`heatmap_compound_target.png`)
- [ ] Distribucion de `standard_type` documentada, con justificacion escrita de por que los endpoints no son comparables
- [ ] Boxplots por familia con **n por familia anotado**, y advertencia sobre familias pequeñas (Carbamates)
- [ ] Correlacion honesta (Pearson + Spearman) descriptores vs `pchembl_median` a nivel compuesto, aclarando que no es un modelo
- [ ] Heatmap triangular de correlacion entre descriptores generado
- [ ] Al menos 3 insights escritos alineados a P1, P2 y P5

---

## 11. Insights esperados para el informe

1. **Patrones fisicoquimicos por familia (P1).** A nivel compuesto se esperan diferencias de perfil fisicoquimico entre familias — por ejemplo, mayor lipofilicidad (AlogP) y peso molecular en piretroides frente a herbicidas mas pequeños y polares. Toda diferencia se reporta con su n por familia y se deja el contraste formal (Kruskal-Wallis + Dunn) para la Fase 4; no se concluye nada sobre familias con pocos compuestos.

2. **Familias mas promiscuas (P2).** La distribucion de `n_targets` es fuertemente asimetrica: la mayoria de compuestos toca pocas dianas y una minoria es muy promiscua (hasta ~133 dianas). El EDA identifica que familias concentran esa polifarmacologia; la relacion entre promiscuidad y propiedades fisicoquimicas se cuantifica con Spearman en la Fase 4.

3. **Endpoints heterogeneos, no agrupables (perfil de dianas).** El corpus mezcla 13 `standard_type` que miden fenomenos distintos (Ki, IC50, LD50, Potency...). Esto obliga a tratar `pchembl_median` como resumen descriptivo con salvedades y a no comparar potencia entre familias sin controlar por endpoint.

4. **Correlaciones descriptor-potencia debiles y honestas (P5).** Se espera que los descriptores globales (MW, AlogP, PSA) muestren asociacion debil con `pchembl_median` a nivel compuesto. Esto no es un fracaso del EDA: es consistente con que la potencia depende de la interaccion especifica molecula-diana, y motiva el enfoque de grafos moleculares (GNN) del proyecto JIC. Se descarta reportar la anticorrelacion pChEMBL–standard_value por ser una identidad matematica.

5. **Anticipacion del clustering (Fase 4).** La combinacion de descriptores no redundantes (evitando colinealidad MW–heavy_atoms detectada en el heatmap) mas la promiscuidad define el espacio en el que la Fase 4 buscara agrupamientos naturales (PCA + K-means/jerarquico) y los contrastara con la taxonomia de familias (ARI).

6. **Anticipacion del baseline honesto (Fase 4 §12, P6).** Las correlaciones debiles descriptor–potencia (P5) y los descriptores constantes por compuesto anticipan que un modelo simple **no generalizara** con split por compuesto. El EDA no entrena ese modelo; la Fase 4 lo ejecuta como control negativo y puente al GNN del proyecto JIC.

---

*Fase anterior:* [Fase 2 — Limpieza de datos](fase2_limpieza_datos.md)  
*Siguiente fase:* [Fase 4 — Analisis multivariado, contraste de hipotesis y baseline P6](fase4_modelado.md)
