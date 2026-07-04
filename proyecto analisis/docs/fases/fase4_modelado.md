# Fase 4 — Análisis multivariado y contraste de hipótesis (Flujo B, parte 3)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Caracterizar la estructura del corpus (107 compuestos) con reducción de dimensionalidad, clustering y pruebas estadísticas |
| **Duracion** | 3-4 dias |
| **Entrada** | `data/processed/compounds_features.csv` (107 filas, nivel COMPUESTO) |
| **Salidas** | `outputs/chembl/results/stats_tests.csv`, `outputs/chembl/results/clustering_summary.json`, `outputs/chembl/results/baseline_honest_metrics.csv`, figuras (`pca_scatter.png`, `dendrogram.png`, `cluster_silhouette.png`, `family_boxplots_annotated.png`) |
| **Rol lider** | Cientifico de Datos |
| **Notebook** | `notebooks/fase4_modelado.ipynb` (PCA + clustering + tests + baseline P6 §4) |
| **Modulos** | `chembl_multivariate.py`, `chembl_preprocessing.py`, `chembl_baseline.py` |

---

## 1. Contexto

El proyecto pivota de un enfoque **predictivo** (que falló por diseño) a uno **descriptivo y multivariado**. La pregunta ya no es "¿podemos predecir la potencia de un compuesto?", sino "¿cómo está estructurado el corpus de 107 plaguicidas y qué patrones lo caracterizan?".

Esta fase responde a tres preguntas de investigación del rediseño:

- **P3** — ¿Los compuestos se agrupan naturalmente? ¿Los clusters coinciden con las familias químicas?
- **P4** — ¿Difiere la potencia (`pchembl`) y las propiedades fisicoquímicas entre familias?
- **P1 (extensión multivariada)** — ¿Cómo se organiza el espacio fisicoquímico de los 107 compuestos?

**Unidad de análisis:** el **compuesto** (107 filas de `compounds_features.csv`), NO la fila/medición. Los 9 descriptores moleculares son constantes dentro de cada compuesto, por lo que el análisis multivariado solo tiene sentido a nivel de compuesto único.

**Salida principal:** una caracterización honesta de la estructura del corpus (P3–P5). El **baseline predictivo honesto (P6)** forma parte de esta misma fase como bloque complementario (§12): cuantifica el límite de los descriptores clásicos y cierra el puente al proyecto GNN.

---

## 2. Por qué el modelado supervisado no es el producto principal

La versión anterior de esta fase entrenaba clasificadores (`activity_class`) y regresores (`pchembl_value`) sobre descriptores moleculares. Se elimina como producto de esta fase por tres razones de diseño, no de código:

1. **Target circular.** `activity_class` es esencialmente `pchembl_value >= 6` binarizado. Clasificar `activity_class` y regresionar `pchembl_value` es resolver dos versiones del mismo problema; la "clasificación" no aporta información independiente.

2. **`pchembl` agrupado no es comparable.** La mediana de `pchembl` por compuesto mezcla **13 `standard_type`** distintos (Ki, IC50, Potency, EC50, AC50, Kd, LD50…) y una mediana de 4 dianas por compuesto (hasta 133). Es un target agregado sobre endpoints heterogéneos: no representa una magnitud física única y por tanto no es un objetivo de regresión legítimo.

3. **Fuga de datos por split de filas / R² negativo por compuesto.** Los descriptores son idénticos para todas las filas de un mismo compuesto. Un split por filas coloca copias del mismo compuesto en train y test, inflando las métricas (accuracy y R² artificialmente altos). El split honesto —por compuesto— revela que el modelo **no generaliza**: la accuracy de test cae drásticamente y el R² de test es **negativo por compuesto** (peor que predecir la media). Esto no es un bug: los descriptores globales no bastan para ordenar por potencia a compuestos no vistos.

**Dónde vive el baseline predictivo (P6).** Se ejecuta en el **Bloque 4** de esta fase (§12), con split por compuesto. No es un producto ni un logro de modelado: reporta un **límite** (R² bajo o negativo) que justifica el salto a grafos moleculares (GNN) en el proyecto JIC.

---

## 3. Bloque 1 — Estandarización + PCA

### 3.1 Descriptores de entrada

Los 9 descriptores fisicoquímicos, constantes por compuesto:

```python
DESCRIPTOR_FEATURES = [
    "mw_freebase",        # Peso molecular
    "alogp",              # LogP (lipofilicidad)
    "psa",                # Area de superficie polar
    "hba",                # Aceptores de H
    "hbd",                # Donores de H
    "aromatic_rings",     # Anillos aromaticos
    "rtb",                # Enlaces rotables
    "heavy_atoms",        # Atomos pesados
    "num_ro5_violations", # Violaciones Lipinski
]
```

### 3.2 Estandarización + PCA

Antes de PCA es obligatorio estandarizar: los descriptores tienen escalas muy distintas (peso molecular en cientos, `num_ro5_violations` en {0,1,2}). Sin estandarizar, la varianza estaría dominada por `mw_freebase`.

**Funcion:** `run_pca(X)` (nueva función — a implementar) en `chembl_preprocessing.py`.

```python
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

def run_pca(X, n_components=None):
    """
    Estandariza (StandardScaler) y aplica PCA sobre los 9 descriptores.
    Retorna: scores (proyecciones), varianza explicada por componente,
             varianza acumulada, y loadings (contribuciones por descriptor).
    (nueva funcion — a implementar)
    """
    Xs = StandardScaler().fit_transform(X)
    pca = PCA(n_components=n_components, random_state=42)
    scores = pca.fit_transform(Xs)
    return {
        "scores": scores,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "cumulative_variance": pca.explained_variance_ratio_.cumsum(),
        "loadings": pca.components_,   # (n_componentes, 9 descriptores)
    }
```

### 3.3 Salidas del bloque PCA

- **Varianza explicada** por componente y acumulada (reportar cuántos PCs cubren ~80-90%).
- **Loadings / contribuciones**: qué descriptores pesan en PC1 y PC2 (interpretación química, p. ej. eje de tamaño vs eje de polaridad).
- **`pca_scatter.png`**: scatter de PC1 vs PC2, cada punto un compuesto, coloreado por `family`. Permite ver visualmente si las familias se separan en el espacio de descriptores.

> Nota de honestidad: la varianza explicada se reporta como resultado **real** una vez ejecutado el notebook; no se anticipan valores en este documento.

---

## 4. Bloque 2 — Clustering

Objetivo: descubrir agrupamientos naturales de los 107 compuestos y contrastarlos con la taxonomía química (`family`).

### 4.1 K-means con selección de k por silhouette

Se prueba **k = 2..8** y se elige el k con mayor **silhouette score** medio. La estandarización usada es la misma que en PCA.

**Funcion:** `run_kmeans_silhouette(X)` (nueva función — a implementar).

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def run_kmeans_silhouette(X, k_range=range(2, 9), random_state=42):
    """
    Ejecuta K-means para k=2..8 sobre X estandarizado y selecciona k
    por silhouette medio. Retorna k_optimo, curva de silhouette por k,
    y las etiquetas del mejor modelo.
    (nueva funcion — a implementar)
    """
    Xs = StandardScaler().fit_transform(X)
    resultados = {}
    for k in k_range:
        labels = KMeans(n_clusters=k, random_state=random_state,
                        n_init=10).fit_predict(Xs)
        resultados[k] = silhouette_score(Xs, labels)
    k_opt = max(resultados, key=resultados.get)
    return {"k_optimo": k_opt, "silhouette_por_k": resultados}
```

- **`cluster_silhouette.png`**: silhouette medio en función de k, marcando el k elegido.

### 4.2 Clustering jerárquico + dendrograma

Se aplica clustering aglomerativo (enlace de Ward sobre distancia euclídea de los descriptores estandarizados) para visualizar la jerarquía de agrupamientos.

**Funcion:** `hierarchical_clusters(X)` (nueva función — a implementar).

```python
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster

def hierarchical_clusters(X, n_clusters=None):
    """
    Clustering jerárquico (Ward) sobre X estandarizado.
    Retorna la matriz de enlace (para el dendrograma) y, opcionalmente,
    etiquetas planas cortando el árbol en n_clusters.
    (nueva funcion — a implementar)
    """
    Xs = StandardScaler().fit_transform(X)
    Z = linkage(Xs, method="ward")
    labels = fcluster(Z, t=n_clusters, criterion="maxclust") if n_clusters else None
    return {"linkage": Z, "labels": labels}
```

- **`dendrogram.png`**: dendrograma con hojas etiquetadas por `family` (o por `compound_name`) para inspeccionar visualmente la correspondencia.

### 4.3 Validación de clusters contra `family`

Los clusters descubiertos se comparan con la etiqueta `family` mediante:

- **Adjusted Rand Index (ARI)** entre las etiquetas de cluster y `family` — mide acuerdo corregido por azar (0 = azar, 1 = coincidencia perfecta).
- **Silhouette** del particionamiento elegido — cohesión/separación interna.

```python
from sklearn.metrics import adjusted_rand_score
ari = adjusted_rand_score(df["family"], cluster_labels)
```

### 4.4 Salida `clustering_summary.json`

```json
{
  "kmeans": {"k_optimo": "<int>", "silhouette": "<float>",
             "silhouette_por_k": {"2": "...", "3": "..."}},
  "hierarchical": {"n_clusters": "<int>", "silhouette": "<float>"},
  "validacion_vs_family": {"ari_kmeans": "<float>", "ari_hierarchical": "<float>"},
  "n_compuestos": 107,
  "n_por_familia": {"Herbicides": "<int>", "Organophosphates": "<int>", "...": "..."}
}
```

---

## 5. Bloque 3 — Contraste de hipótesis entre familias

Objetivo (P4): determinar si las propiedades fisicoquímicas y la potencia mediana difieren significativamente entre familias químicas.

### 5.1 Elección de pruebas

Con n=107 y familias desbalanceadas (varias con pocos compuestos), se usan **pruebas no paramétricas**, que no asumen normalidad ni homocedasticidad:

- **Kruskal-Wallis** por cada descriptor y por `pchembl_median`, comparando las distribuciones entre familias.
- **Post-hoc de Dunn** con corrección **Holm** cuando Kruskal-Wallis es significativo (identifica qué pares de familias difieren).
- **Tamaño de efecto**: epsilon² (ε²) para Kruskal-Wallis, para no confundir significancia estadística con magnitud del efecto.
- **Reportar SIEMPRE el n por familia** junto a cada prueba: un p-valor sobre una familia de 3 compuestos no es interpretable como uno sobre 40.

### 5.2 Funciones

**Funcion:** `kruskal_by_family(df, col)` (nueva función — a implementar). Usa `scipy.stats`.

```python
from scipy.stats import kruskal

def kruskal_by_family(df, col):
    """
    Kruskal-Wallis de `col` entre familias. Retorna H, p-valor,
    epsilon² (tamaño de efecto) y n por familia.
    (nueva funcion — a implementar)
    """
    grupos = [g[col].dropna().values for _, g in df.groupby("family")]
    n_por_familia = df.groupby("family")[col].count().to_dict()
    H, p = kruskal(*grupos)
    N = sum(len(g) for g in grupos)
    k = len(grupos)
    epsilon2 = (H - k + 1) / (N - k)     # tamaño de efecto
    return {"variable": col, "H": H, "p_value": p,
            "epsilon2": epsilon2, "n_por_familia": n_por_familia}
```

**Funcion:** `posthoc_dunn(df, col)` (nueva función — a implementar). Usa `scikit-posthocs`.

```python
import scikit_posthocs as sp

def posthoc_dunn(df, col):
    """
    Post-hoc de Dunn con corrección Holm entre familias para `col`.
    Solo se invoca si Kruskal-Wallis resultó significativo.
    Retorna matriz de p-valores por par de familias.
    (nueva funcion — a implementar)
    """
    return sp.posthoc_dunn(df, val_col=col, group_col="family",
                           p_adjust="holm")
```

### 5.3 Visualización

- **`family_boxplots_annotated.png`**: boxplots por familia de los descriptores clave y de `pchembl_median`, anotados con el resultado de Kruskal-Wallis (p y ε²) y el n por familia debajo de cada caja.

### 5.4 Salida `stats_tests.csv`

Una fila por variable contrastada:

| variable | test | statistic (H) | p_value | epsilon2 | familias_significativas (Dunn/Holm) | n_por_familia |
|---|---|---|---|---|---|---|
| mw_freebase | Kruskal-Wallis | … | … | … | … | … |
| alogp | Kruskal-Wallis | … | … | … | … | … |
| … (9 descriptores) | … | … | … | … | … | … |
| pchembl_median | Kruskal-Wallis | … | … | … | … | … |

---

## 6. Trabajo por rol

### Cientifico de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Estandarizar y ejecutar PCA (`run_pca`) | Varianza explicada + loadings |
| 2 | Generar scatter PC1-PC2 por familia | `pca_scatter.png` |
| 3 | K-means con selección de k por silhouette (`run_kmeans_silhouette`) | k óptimo + `cluster_silhouette.png` |
| 4 | Clustering jerárquico + dendrograma (`hierarchical_clusters`) | `dendrogram.png` |
| 5 | Validar clusters vs `family` (ARI + silhouette) | `clustering_summary.json` |
| 6 | Kruskal-Wallis por descriptor y `pchembl_median` (`kruskal_by_family`) | Filas de `stats_tests.csv` |
| 7 | Post-hoc Dunn/Holm donde sea significativo (`posthoc_dunn`) | Pares significativos |
| 8 | Boxplots anotados por familia | `family_boxplots_annotated.png` |

### Analista de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Interpretar loadings | Explicar qué mide PC1 y PC2 en términos químicos |
| Leer clusters | Describir qué familias caen en cada cluster y las excepciones |
| Interpretar efectos | Distinguir significancia (p) de magnitud (ε²); señalar familias pequeñas |

### Ingeniero de Datos (REVISOR)

| Tarea | Descripcion |
|---|---|
| Verificar entrada | Confirmar que `compounds_features.csv` tiene 107 filas y 9 descriptores completos |
| Verificar persistencia | Confirmar que `stats_tests.csv`, `clustering_summary.json` y las 4 figuras se guardaron |
| Verificar reproducibilidad | Re-ejecutar con `random_state=42` y comparar k, ARI y p-valores |

### ML Engineer (APOYO)

| Tarea | Descripcion |
|---|---|
| Exponer clusters en dashboard | Añadir la etiqueta de cluster por compuesto al explorador (Fase 5) |
| Baseline P6 | Ejecutar §12; **no** desplegar predictor en dashboard (Fase 5) |

---

## 7. Ejecucion

```bash
# Notebook Fase 4 (multivariado + baseline P6)
jupyter notebook "proyecto analisis/notebooks/fase4_modelado.ipynb"

# Verificacion end-to-end (desde raiz del monorepo)
make analisis-verify
```

---

## 8. Criterios de exito

- [ ] PCA ejecutado con **varianza explicada reportada** (por componente y acumulada)
- [ ] Loadings/contribuciones de los 9 descriptores documentados para PC1 y PC2
- [ ] `pca_scatter.png` generado, coloreado por `family`
- [ ] K-means con **k elegido por silhouette** (probado k=2..8) + `cluster_silhouette.png`
- [ ] Clustering jerárquico con `dendrogram.png`
- [ ] **ARI vs `family`** calculado para K-means y jerárquico
- [ ] `clustering_summary.json` con silhouette, ARI, k elegido y n por familia
- [ ] **Tabla de tests** (`stats_tests.csv`) con p-valor y **tamaño de efecto (ε²)** por variable
- [ ] Post-hoc Dunn/Holm ejecutado donde Kruskal-Wallis fue significativo
- [ ] `family_boxplots_annotated.png` con n por familia anotado
- [ ] Sin clasificación de `activity_class` ni regresión de `pchembl_value` como producto del dashboard
- [ ] Baseline honesto (§12): split por compuesto, métricas en `baseline_honest_metrics.csv`, contraste filas vs compuesto documentado

---

## 9. Troubleshooting

| Problema | Causa | Solucion |
|---|---|---|
| PCA dominado por 1 descriptor | Falta estandarizar | Aplicar `StandardScaler` antes de PCA (incluido en `run_pca`) |
| Silhouette bajo para todo k | Estructura débil o n pequeño | Reportar como hallazgo: clustering exploratorio, no confirmatorio |
| ARI cercano a 0 | Clusters no coinciden con familias | Resultado legítimo: los descriptores no reproducen la taxonomía química |
| Kruskal-Wallis sin significancia | Familias pequeñas → poca potencia | Reportar n por familia; no sobre-interpretar |
| `scikit-posthocs` no instalado | Falta dependencia | `pip install scikit-posthocs` |
| Dunn sin corrección | Inflación de falsos positivos | Usar `p_adjust="holm"` |

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| n=107 es pequeño para clustering | Tratar el clustering como **EXPLORATORIO, no confirmatorio**; reportar silhouette y ARI, no afirmar clases "reales" |
| Familias con pocos compuestos | Reportar **siempre n por familia**; no sacar conclusiones de grupos con n muy bajo; limita la potencia estadística |
| Supuestos de normalidad no se cumplen | Usar **pruebas no paramétricas** (Kruskal-Wallis, Dunn) en lugar de ANOVA/t-test |
| Comparaciones múltiples | Corrección **Holm** en el post-hoc de Dunn |
| Confundir significancia con magnitud | Reportar **tamaño de efecto (ε²)** junto al p-valor |
| Descriptores constantes por compuesto | Análisis a nivel COMPUESTO (107), nunca a nivel fila |

---

## 11. Distribucion por roles dentro del notebook

El notebook `fase4_modelado.ipynb` tiene cuatro bloques: PCA (§1), clustering (§2), tests (§3) y baseline P6 (§4). Trazabilidad Fase → sección → entregable:

| Rol | Secciones del notebook | Entregable |
|---|---|---|
| Ingeniero de Datos | 0 (carga y validación 107×9) | Entrada validada |
| Analista de Datos | Interpretación PCA, clusters, efectos, contraste baseline | Lectura de resultados |
| Cientifico de Datos | §1–§4 | `stats_tests.csv`, `clustering_summary.json`, `baseline_honest_metrics.csv`, figuras |
| ML Engineer | Etiqueta cluster al explorador (Fase 5); baseline P6 sin despliegue | Integración dashboard |

---

## 12. Bloque 4 — Baseline predictivo honesto (P6)

> **Naturaleza:** experimento de control dentro de la Fase 4, no producto del curso ni del dashboard.
> Demuestra el **límite intrínseco** de 8–9 descriptores moleculares para predecir potencia en compuestos no vistos y sirve de **puente al proyecto GNN de la JIC**.

### 12.1 Pregunta y respuesta esperada

**P6:** ¿Un modelo simple ordena/predice la potencia mediana (`pchembl_median`) a partir de descriptores, cuando la validación se hace **por compuesto**?

**Respuesta esperada (honesta):** No. Con 107 compuestos y descriptores constantes por molécula, el modelo **no generaliza** (R² bajo o **negativo** en test).

### 12.2 Diseño experimental

| Elemento | Valor |
|---|---|
| **Unidad** | Compuesto (107 filas de `compounds_features.csv`) |
| **Target** | `pchembl_median` |
| **Features** | 9 descriptores (`FEATURE_COLS` / `DESCRIPTOR_FEATURES`) |
| **Modelo principal** | `RandomForestRegressor` |
| **Contraste opcional** | `Ridge` (baseline lineal) |
| **Validación** | Split por grupo (`train_test_split_by_group`, `group_col="chembl_id"`) + `GroupKFold` |
| **Módulo** | `src/analisis_proyecto/chembl_baseline.py` → `honest_baseline_compound_level`, `leaky_baseline_row_level` |
| **Salida** | `outputs/chembl/results/baseline_honest_metrics.csv` |
| **Ejecución** | Sección §4 de `notebooks/fase4_modelado.ipynb` |

**Regla de honestidad (no negociable):** split por filas **no es válido** aquí — reintroduce fuga porque los descriptores son idénticos para todas las mediciones del mismo compuesto.

### 12.3 Contraste que revela la fuga

| Protocolo | R² (referencia) | ¿Válido? | Por qué |
|---|---|---|---|
| Split por **filas** (medición) | Alto (~0.5–0.6) | **No — fuga** | Mismas moléculas en train y test |
| Split por **compuesto** (P6) | Bajo o **negativo** | **Sí — honesto** | Generalización real a moléculas nuevas |

En el notebook se recalculan ambos protocolos lado a lado. La inflación del split por filas **no es mejora del modelo**: es fuga de datos.

### 12.4 Conclusión y puente al JIC

Con **107 compuestos** y descriptores globales **no hay señal suficiente** para predecir potencia a compuestos no vistos. La potencia depende de la interacción molécula–diana y de la topología estructural fina. Esto **motiva** el enfoque del proyecto JIC: **grafos moleculares + GNN-GIN** entrenados sobre Tox21 (~8 000 compuestos), donde la representación se aprende del grafo átomo–enlace.

### 12.5 Ejecución

```bash
jupyter notebook "proyecto analisis/notebooks/fase4_modelado.ipynb"
make analisis-verify   # incluye baseline honesto en verify_flow_b.py
```

### 12.6 Criterios de éxito (P6)

- [ ] `compounds_features.csv` con **107 filas** (unidad = compuesto)
- [ ] `RandomForestRegressor` con split por compuesto + `GroupKFold`
- [ ] R², MAE y RMSE reportados; R² por compuesto **bajo o negativo**
- [ ] Tabla comparativa: split compuesto (honesto) vs split filas (fuga)
- [ ] `baseline_honest_metrics.csv` escrito
- [ ] Puente al GNN/JIC redactado en notebook o informe (Fase 7)
- [ ] Ningún `chembl_id` compartido entre train y test

### 12.7 Troubleshooting (P6)

| Problema | Causa | Solución |
|---|---|---|
| R² negativo por compuesto | Modelo peor que la media | **Esperado** — hallazgo de P6 |
| R² alto (~0.5–0.6) | Split por filas | Usar `group_col="chembl_id"` |
| `compounds_features.csv` ausente | Falta Fase 2 | `build_compound_features()` |
| Varianza alta entre runs | n=107, split único | `GroupKFold` y promediar folds |

---

*Fase anterior:* [Fase 3 — Analisis exploratorio](fase3_eda.md)  
*Siguiente fase:* [Fase 5 — Dashboard](fase5_dashboard.md)  
*Siguiente fase:* [Fase 5 — Dashboard interactivo](fase5_dashboard.md)
