# Fase 4 — Análisis multivariado y contraste de hipótesis (Flujo B, parte 3)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Caracterizar la estructura del corpus (107 compuestos) con reducción de dimensionalidad, clustering y pruebas estadísticas |
| **Duracion** | 3-4 dias |
| **Entrada** | `data/processed/compounds_features.csv` (107 filas, nivel COMPUESTO) |
| **Salidas** | `outputs/chembl/results/stats_tests.csv`, `outputs/chembl/results/clustering_summary.json`, figuras (`pca_scatter.png`, `dendrogram.png`, `cluster_silhouette.png`, `family_boxplots_annotated.png`) |
| **Rol lider** | Cientifico de Datos |
| **Notebook** | `notebooks/proyecto analisis de datos/fase4_modelado.ipynb` |
| **Modulo** | `src/analisis_proyecto/chembl_preprocessing.py` |

---

## 1. Contexto

El proyecto pivota de un enfoque **predictivo** (que falló por diseño) a uno **descriptivo y multivariado**. La pregunta ya no es "¿podemos predecir la potencia de un compuesto?", sino "¿cómo está estructurado el corpus de 107 plaguicidas y qué patrones lo caracterizan?".

Esta fase responde a tres preguntas de investigación del rediseño:

- **P3** — ¿Los compuestos se agrupan naturalmente? ¿Los clusters coinciden con las familias químicas?
- **P4** — ¿Difiere la potencia (`pchembl`) y las propiedades fisicoquímicas entre familias?
- **P1 (extensión multivariada)** — ¿Cómo se organiza el espacio fisicoquímico de los 107 compuestos?

**Unidad de análisis:** el **compuesto** (107 filas de `compounds_features.csv`), NO la fila/medición. Los 9 descriptores moleculares son constantes dentro de cada compuesto, por lo que el análisis multivariado solo tiene sentido a nivel de compuesto único.

**Salida principal:** una caracterización honesta de la estructura del corpus — no un modelo predictivo. El baseline predictivo se traslada a un anexo separado (ver §2).

---

## 2. Por qué se abandona el modelado supervisado aquí

La versión anterior de esta fase entrenaba clasificadores (`activity_class`) y regresores (`pchembl_value`) sobre descriptores moleculares. Se elimina como producto de esta fase por tres razones de diseño, no de código:

1. **Target circular.** `activity_class` es esencialmente `pchembl_value >= 6` binarizado. Clasificar `activity_class` y regresionar `pchembl_value` es resolver dos versiones del mismo problema; la "clasificación" no aporta información independiente.

2. **`pchembl` agrupado no es comparable.** La mediana de `pchembl` por compuesto mezcla **13 `standard_type`** distintos (Ki, IC50, Potency, EC50, AC50, Kd, LD50…) y una mediana de 4 dianas por compuesto (hasta 133). Es un target agregado sobre endpoints heterogéneos: no representa una magnitud física única y por tanto no es un objetivo de regresión legítimo.

3. **Fuga de datos por split de filas / R² negativo por compuesto.** Los descriptores son idénticos para todas las filas de un mismo compuesto. Un split por filas coloca copias del mismo compuesto en train y test, inflando las métricas (accuracy y R² artificialmente altos). El split honesto —por compuesto— revela que el modelo **no generaliza**: la accuracy de test cae drásticamente y el R² de test es **negativo por compuesto** (peor que predecir la media). Esto no es un bug: los descriptores globales no bastan para ordenar por potencia a compuestos no vistos.

**Dónde vive ahora el baseline predictivo.** El baseline se conserva como ejercicio **adicional y completamente separado**, documentado en el [Anexo — Baseline predictivo honesto](anexo_baseline_predictivo.md). Allí se reporta con split por compuesto y se presenta como **límite** (no como logro): su valor es servir de puente honesto al proyecto JIC, mostrando que los descriptores clásicos no generalizan y motivando el enfoque de grafos moleculares (GNN).

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
| Baseline separado | Mantener el baseline predictivo en el anexo, sin mezclarlo con esta fase |

---

## 7. Ejecucion

```bash
# Notebook completo (PCA + clustering + tests)
jupyter notebook "notebooks/proyecto analisis de datos/fase4_modelado.ipynb"

# Verificacion desde terminal
python scripts/analisis_proyecto/fase4/verify_flow_b.py

# Ejecutar solo el análisis multivariado
python -c "
from src.analisis_proyecto.chembl_preprocessing import (
    run_pca, run_kmeans_silhouette, hierarchical_clusters,
    kruskal_by_family, posthoc_dunn, DESCRIPTOR_FEATURES)
import pandas as pd
df = pd.read_csv('data/processed/compounds_features.csv')
X = df[DESCRIPTOR_FEATURES].values
print('n compuestos:', len(df))
print(run_pca(X)['explained_variance_ratio'])
print(run_kmeans_silhouette(X)['k_optimo'])
"
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
- [ ] Sin clasificación de `activity_class` ni regresión de `pchembl_value` como producto de esta fase (viven en el anexo)

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

El notebook `fase4_modelado.ipynb` se reestructura en torno a los tres bloques del análisis multivariado. Esta tabla cierra la trazabilidad Fase -> sección del notebook -> entregable:

| Rol | Secciones del notebook | Entregable |
|---|---|---|
| Ingeniero de Datos | 0 (carga de `compounds_features.csv`, verificación 107×9) | Entrada validada |
| Analista de Datos | Interpretación de PCA, clusters y efectos | Lectura de resultados |
| Cientifico de Datos | PCA, clustering, tests estadísticos | `stats_tests.csv`, `clustering_summary.json`, figuras |
| ML Engineer | Etiqueta de cluster al explorador (Fase 5); baseline al anexo | Integración dashboard |

---

*Fase anterior:* [Fase 3 — Analisis exploratorio](fase3_eda.md)  
*Documento adicional:* [Anexo — Baseline predictivo honesto](anexo_baseline_predictivo.md)  
*Siguiente fase:* [Fase 5 — Dashboard interactivo](fase5_dashboard.md)
