# Fase 7 — Comunicacion de Resultados (Flujo E)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Producir articulo IEEE, video explicativo y presentacion JIC que integren la caracterizacion descriptiva de ChEMBL con los resultados del proyecto hermano GNN-GIN |
| **Duracion** | 4-5 dias |
| **Entradas** | Resultados de Fases 1-4 (adquisicion, limpieza, EDA, analisis multivariado) y del Anexo (baseline predictivo honesto). Fase 5 (dashboard) para la demo en video. Fase 6 (geodatos) esta **PARQUEADA** — no se usa en ningun entregable de esta fase |
| **Salidas** | Articulo IEEE (PDF), video (5-10 min), slides de presentacion |
| **Rol lider** | Todos los roles participan |
| **Notebook** | `notebooks/proyecto analisis de datos/fase7_comunicacion.ipynb` |
| **Entregables** | `outputs/reports/articulo_ieee.pdf`, video en plataforma de entrega |

---

## 1. Contexto

El curso requiere tres entregables de comunicacion:
1. **Articulo en formato IEEE** — documento formal con estructura academica
2. **Video explicativo** — presentacion oral del trabajo (5-10 minutos)
3. **Presentacion JIC** — para la Jornada de Iniciacion Cientifica

Estos entregables sintetizan dos piezas de trabajo distintas que comparten narrativa:

- El **proyecto JIC (GNN-GIN + XAI)**, descrito en el `CLAUDE.md` raiz del repositorio: entrena una red de grafos sobre Tox21 y aplica GNNExplainer/Grad-CAM. Sus metricas (Tabla 1) **no se generan en este proyecto de analisis de datos** — se citan como resultado del proyecto hermano.
- El **proyecto de analisis de datos ChEMBL x Plaguicidas Panama** (este documento), que **caracteriza** el corpus de 107 plaguicidas panamenos por su perfil fisicoquimico, promiscuidad biologica y agrupamientos naturales, y que ademas **demuestra con un baseline honesto** que los descriptores moleculares clasicos no generalizan a compuestos no vistos.

El hilo que conecta ambos proyectos es precisamente ese limite: la evidencia de que los descriptores globales (MW, LogP, PSA, etc.) fallan al predecir potencia con un split honesto por compuesto **motiva** el uso de representaciones estructurales (grafos moleculares) en el proyecto GNN. Cada rol contribuye a la seccion que le corresponde; el Cientifico de Datos y el Analista son responsables de mantener esta distincion clara en todos los entregables (no presentar los resultados del GNN como si fueran producto de este pipeline de ChEMBL, ni viceversa).

---

## 2. Articulo IEEE

### Estructura requerida

| Seccion | Contenido | Responsable |
|---|---|---|
| **I. Introduccion** | Problema de toxicidad de plaguicidas en Panama, motivacion, objetivos de ambos proyectos | Analista de Datos |
| **II. Marco teorico** | GNN, GIN, XAI, Tox21, ChEMBL, descriptores moleculares, pruebas no parametricas (Kruskal-Wallis) | Cientifico de Datos |
| **III. Metodologia** | Pipeline de datos ChEMBL (dedup + `activities_clean` + `compounds_features`), analisis multivariado (PCA/clustering), baseline honesto (anexo), arquitectura del modelo GNN y protocolos de evaluacion | Ingeniero de Datos |
| **IV. Resultados** | Caracterizacion del corpus (107 compuestos), contraste de hipotesis, clustering, baseline honesto, metricas GNN (proyecto hermano) | Cientifico de Datos |
| **V. Discusion** | Interpretacion, limitaciones, por que el analisis clasico motiva el enfoque de grafos | Analista de Datos |
| **VI. Conclusiones** | Hallazgos principales, trabajo futuro | Todos |
| **Referencias** | Formato IEEE | Todos |

### Formato IEEE

```latex
\documentclass[conference]{IEEEtran}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{booktabs}

\title{Caracterizacion Descriptiva de Plaguicidas Agricolas Panamenos
       en ChEMBL y su Motivacion para un Enfoque de Graph Neural
       Networks con Interpretabilidad XAI}

\author{
    \IEEEauthorblockN{Autor 1, Autor 2, Autor 3, Autor 4}
    \IEEEauthorblockA{
        Universidad Tecnologica de Panama\\
        Jornada de Iniciacion Cientifica 2026
    }
}

\begin{document}
\maketitle

\begin{abstract}
Se caracteriza el perfil fisicoquimico y de bioactividad de un
corpus de 107 plaguicidas panamenos extraido de ChEMBL, mediante
analisis multivariado (PCA, clustering) y contraste estadistico
(Kruskal-Wallis, tamano de efecto) entre familias quimicas. Un
baseline predictivo evaluado con split honesto por compuesto
confirma que los descriptores moleculares globales (peso molecular,
LogP, PSA, entre otros) no generalizan a compuestos no vistos
(R\textsuperscript{2} negativo), evidenciando la fuga de datos que
produce metricas infladas cuando el split se hace por fila de
medicion. Este limite motiva un sistema complementario de quimica
computacional basado en Graph Isomorphism Networks (GIN), entrenado
sobre grafos moleculares del dataset Tox21 (12 dianas biologicas),
que incorpora interpretabilidad mediante GNNExplainer y Grad-CAM
para identificar grupos funcionales asociados a la toxicidad
predicha. Se reportan ambos resultados como piezas complementarias
de un mismo programa de investigacion.
\end{abstract}

\begin{IEEEkeywords}
graph neural networks, quimioinformatica, plaguicidas, ChEMBL,
clustering, XAI, Tox21, Panama
\end{IEEEkeywords}
```

### Tablas clave para el articulo

#### Tabla 1 — Comparacion de modelos (Tox21)

> Estos valores pertenecen al **proyecto GNN hermano de la JIC** (arquitectura GIN sobre Tox21,
> ver `CLAUDE.md` raiz). No se producen en el pipeline de ChEMBL de este proyecto de analisis de
> datos; se citan aqui porque el articulo y las slides son compartidos entre ambos proyectos.

| Modelo | AUC-ROC promedio | Mejor tarea | Peor tarea |
|---|---|---|---|
| Random Forest + ECFP4 | 0.7433 | NR-AhR (0.86) | NR-ER (0.62) |
| MLP + ECFP4 | 0.7071 | NR-AhR (0.82) | NR-ER (0.58) |
| SMILES2vec | 0.7268 | NR-AhR (0.84) | NR-ER (0.60) |
| **GNN-GIN** | **0.7498** | NR-AhR (0.87) | NR-ER (0.65) |

*Valores reales de `outputs/results/gin_results.csv` y `baseline_results.csv` (proyecto GNN hermano).*

#### Tabla A — Contraste de hipotesis entre familias (ChEMBL, nivel compuesto)

Compara cada descriptor fisicoquimico y `pchembl_median` entre familias quimicas mediante
Kruskal-Wallis (no parametrico, apropiado para grupos de tamano desigual) y reporta el tamano
de efecto (epsilon-cuadrado o eta-cuadrado). Se genera con la funcion nueva
`run_kruskal_tests(compounds_features_df, group_col='family')` **(nueva funcion — a
implementar)** en `chembl_preprocessing.py`, y se guarda en
`outputs/chembl/results/stats_tests.csv`.

| Variable | Estadistico H | p-valor | Tamano de efecto | n grupos validos | Interpretacion |
|---|---|---|---|---|---|
| `mw_freebase` | *(pendiente de ejecucion)* | *(pendiente)* | *(pendiente)* | 7 familias | *(completar tras correr el notebook)* |
| `alogp` | *(pendiente)* | *(pendiente)* | *(pendiente)* | 7 familias | *(pendiente)* |
| `psa` | *(pendiente)* | *(pendiente)* | *(pendiente)* | 7 familias | *(pendiente)* |
| `aromatic_rings` | *(pendiente)* | *(pendiente)* | *(pendiente)* | 7 familias | *(pendiente)* |
| `pchembl_median` | *(pendiente)* | *(pendiente)* | *(pendiente)* | 7 familias | *(pendiente)* |

**Regla de honestidad:** ninguna celda de esta tabla se llena con un numero inventado. Los
valores reales solo se conocen al ejecutar `run_kruskal_tests` sobre `compounds_features.csv`.
Dado que a nivel COMPUESTO el n por familia es bajo para varias familias (p. ej.
`Carbamates`, `Triazines`), el articulo debe reportar el n de cada grupo junto al p-valor y
evitar sobre-interpretar diferencias en familias con pocos compuestos.

#### Tabla B — Resumen de clustering (ChEMBL, nivel compuesto)

Generada por la funcion nueva `run_clustering_pipeline(compounds_features_df)`
**(nueva funcion — a implementar)**, que guarda `outputs/chembl/results/clustering_summary.json`.

| Metodo | k elegido | Silhouette | Adjusted Rand Index vs `family` | Observacion |
|---|---|---|---|---|
| K-means (sobre PCA) | *(pendiente)* | *(pendiente)* | *(pendiente)* | *(pendiente)* |
| Jerarquico (Ward) | *(pendiente)* | *(pendiente)* | *(pendiente)* | *(pendiente)* |

Un ARI cercano a 0 indicaria que los clusters naturales del espacio fisicoquimico **no**
coinciden con la taxonomia quimica de familia — un hallazgo tan valido como lo contrario, y
debe reportarse tal cual salga, sin forzar la interpretacion hacia el resultado "esperado".

#### Tabla C — Baseline honesto vs fuga de datos (Anexo, `docs/analisis_proyecto/fases/anexo_baseline_predictivo.md`)

Valores reales de `outputs/chembl/results/metrics_summary.csv`. Esta tabla es la evidencia
central que conecta el analisis de ChEMBL con la motivacion del GNN: el mismo modelo, sobre
los mismos descriptores, rinde muy distinto segun como se particionen los datos.

| Modelo | Tarea | Feature set | Split por fila (fuga) | Split por compuesto (honesto) | Diferencia |
|---|---|---|---|---|---|
| RandomForest | Clasificacion (Accuracy test) | descriptores | 0.758 | 0.372 | -38.6 pp |
| RandomForest | Regresion (R² test) | descriptores | 0.510 | -0.802 | de positivo a fuertemente negativo |
| SVR (RBF) | Regresion (R² test) | descriptores | 0.500 | -1.129 | de positivo a fuertemente negativo |
| RandomForest | Regresion (R² test) | descriptores + ensayo | 0.615 | -0.254 | de positivo a negativo |
| SVR (RBF) | Regresion (R² test) | descriptores + ensayo | 0.570 | -0.286 | de positivo a negativo |

*Nota: `SVM_RBF` de clasificacion solo se evaluo con split por fila en el corte actual
(0.753 accuracy_test); no reportar esa cifra como resultado valido de generalizacion.*

### Figuras clave

| # | Figura | Fuente | Seccion |
|---|---|---|---|
| 1 | Arquitectura GNN-GIN | Diagrama manual o draw.io (proyecto hermano) | II |
| 2 | Pipeline de datos completo (ChEMBL: extraccion → dedup → `activities_clean`/`compounds_features`) | Diagrama de flujo | III |
| 3 | Barras AUC por tarea (4 modelos) | `gin_results.csv` + `baseline_results.csv` (proyecto hermano) | IV |
| 4 | Molecula con colores XAI (Clorpirifos) | `outputs/xai/figures/` (proyecto hermano) | IV |
| 5 | PCA de 107 compuestos coloreado por cluster | `pca_scatter.png` (nueva) | IV |
| 6 | Dendrograma / silhouette del clustering jerarquico | `dendrogram.png`, `cluster_silhouette.png` (nuevas) | IV |
| 7 | Distribucion de promiscuidad (`n_targets` por compuesto) | `promiscuity_distribution.png` (nueva) | IV |
| 8 | Boxplots por familia con anotacion de significancia (Kruskal-Wallis) | `family_boxplots_annotated.png` (nueva) | IV |
| 9 | Heatmap compuesto x diana biologica | `heatmap_compound_target.png` (nueva) | IV |
| 10 | Comparacion split filas vs compuesto (accuracy/R²) | `outputs/chembl/figures/confusion_matrices.png` + Tabla C | IV (anexo) |

---

## 3. Video explicativo

### Estructura (5-10 minutos)

| Tiempo | Seccion | Contenido | Responsable |
|---|---|---|---|
| 0:00 - 1:00 | Introduccion | Problema, contexto Panama, pregunta de investigacion | Analista |
| 1:00 - 2:30 | Datos | Fuentes (Tox21, ChEMBL, PubChem), consolidacion en `activities_clean`/`compounds_features` (107 compuestos) | Ingeniero |
| 2:30 - 4:00 | Caracterizacion y limite clasico | PCA/clusters, promiscuidad, contraste de hipotesis, baseline honesto (R² negativo por compuesto) | Cientifico |
| 4:00 - 5:30 | Modelo GNN + XAI | GNN-GIN, baselines, GNNExplainer/Grad-CAM (proyecto hermano) | Cientifico |
| 5:30 - 7:00 | Dashboard | Demo en vivo del explorador de compuestos (perfil fisicoquimico + dianas + cluster asignado) | ML Engineer |
| 7:00 - 8:30 | Resultados | Hallazgos principales, tablas A/B/C, comparativa GNN | Analista |
| 8:30 - 10:00 | Conclusiones | Limitaciones, trabajo futuro, implicaciones para MIDA | Todos |

### Recomendaciones tecnicas

| Aspecto | Recomendacion |
|---|---|
| Resolucion | 1920x1080 minimo |
| Audio | Microfono externo, no built-in del laptop |
| Formato | MP4 con codec H.264 |
| Tamano | < 500 MB (comprimir si necesario) |
| Subtitulos | Opcionales pero recomendados |
| Demo del dashboard | Grabar pantalla con OBS o similar (explorador de compuestos, NO el mapa — Fase 6 esta parqueada) |
| Transiciones | Simples (fade), no distractoras |

---

## 4. Presentacion JIC

### Estructura de slides

| # | Slide | Contenido |
|---|---|---|
| 1 | Portada | Titulo, autores, universidad, logo JIC |
| 2 | Problema | Plaguicidas en Panama, 20 ingredientes MIDA, contexto regulatorio |
| 3 | Hipotesis | Hipotesis del GNN ("Una GNN-GIN predice toxicidad con AUC > 0.82...") + motivacion desde ChEMBL |
| 4 | Metodologia | Diagrama del pipeline combinado (ChEMBL: caracterizacion + baseline honesto; JIC: SMILES -> grafo -> GIN -> prediccion -> XAI) |
| 5 | Datos | Tox21 (12 tareas), ChEMBL (3.608 filas → 107 compuestos unicos), PubChem (235 CIDs) |
| 6 | Modelo GIN | Arquitectura con bloques (Embedding -> GIN layers -> Readout -> Classifier) |
| 7 | Resultados GNN | Tabla AUC por tarea, barras comparativas vs baselines |
| 8 | XAI | Ejemplo Clorpirifos con molecula coloreada |
| 9 | Caracterizacion ChEMBL | PCA + clusters + distribucion de promiscuidad (Tablas A y B) |
| 10 | Baseline honesto | Split por compuesto vs por fila, R² negativo — motivacion del GNN (Tabla C) |
| 11 | Dashboard | Screenshot del explorador de compuestos (perfil fisicoquimico, dianas, cluster) |
| 12 | Limitaciones | AUC 0.75 vs objetivo 0.82, R² negativo, n=107 y familias pequenas |
| 13 | Conclusiones | 3 hallazgos principales |
| 14 | Trabajo futuro | Pretraining, datos ToxCast, validacion PPDB, retomar geodatos con datos reales de uso/registro |
| 15 | Gracias | Contacto, link al repositorio |

### Duración objetivo: 15 minutos + 5 minutos preguntas

---

## 5. Trabajo por rol

### Analista de Datos

| # | Tarea | Entregable |
|---|---|---|
| 1 | Redactar Introduccion del articulo | Seccion I del IEEE paper |
| 2 | Redactar Discusion | Seccion V del IEEE paper |
| 3 | Interpretar resultados para audiencia no tecnica | Narrativa para video y slides |
| 4 | Disenar slides de contexto e hipotesis | Slides 2, 3 de la presentacion |
| 5 | Investigar datos de MIDA para contextualizar | Parrafo de contexto regulatorio |

### Cientifico de Datos

| # | Tarea | Entregable |
|---|---|---|
| 1 | Redactar Marco teorico | Seccion II del IEEE paper |
| 2 | Redactar Resultados | Seccion IV del IEEE paper |
| 3 | Generar tablas comparativas y ejecutar `run_kruskal_tests` / `run_clustering_pipeline` | Tablas 1, A, B, C del articulo |
| 4 | Explicar caracterizacion ChEMBL y XAI en el video | Segmentos 2:30-5:30 del video |
| 5 | Disenar slides de resultados | Slides 7, 8, 9, 10 de la presentacion |

### Ingeniero de Datos

| # | Tarea | Entregable |
|---|---|---|
| 1 | Redactar Metodologia | Seccion III del IEEE paper |
| 2 | Crear diagramas de pipeline (incluyendo `activities_clean` + `compounds_features`) | Figuras 1, 2 del articulo |
| 3 | Documentar reproducibilidad | Seccion de datos y codigo en el articulo |
| 4 | Explicar datos en el video | Segmento 1:00-2:30 del video |
| 5 | Disenar slides de metodologia | Slides 4, 5 de la presentacion |

### ML Engineer

| # | Tarea | Entregable |
|---|---|---|
| 1 | Grabar demo del explorador de compuestos (dashboard) | Segmento 5:30-7:00 del video |
| 2 | Disenar slide del dashboard | Slide 11 de la presentacion |
| 3 | Asegurar que el dashboard esta funcional para la demo (sin depender de la Fase 6 parqueada) | Dashboard corriendo sin errores |
| 4 | Compilar articulo en LaTeX | PDF final del articulo |
| 5 | Editar video final | MP4 con transiciones y audio limpio |

---

## 6. Contenido critico para cada entregable

### Lo que DEBE incluirse

| Elemento | Articulo | Video | Slides |
|---|---|---|---|
| Tabla AUC por tarea (4 modelos, proyecto hermano) | Si | Mencion | Si |
| Molecula XAI coloreada | Si (figura) | Si (visual) | Si |
| PCA + clustering (Tabla B, figura) | Si | Mencion | Si |
| Contraste de hipotesis con p-valor y tamano de efecto (Tabla A) | Si (tabla) | Mencion | Si |
| Baseline honesto: split filas vs compuesto (Tabla C) | Si (tabla) | Mencion | Si |
| Limitacion: AUC 0.75 vs 0.82 | Si (discusion) | Mencion | Si |
| Limitacion: R² negativo con split por compuesto | Si (discusion) | Mencion | Si |
| Limitacion: n=107 y familias con pocos compuestos | Si (discusion) | Mencion | Si |
| Caso estudio Clorpirifos (perfil descriptivo) | Si (detallado) | Si (visual) | Si |
| Hiperparametros del modelo GNN | Si (tabla) | No | No |
| Codigo fuente (enlaces) | Si (referencia) | No | Si (slide final) |

### Lo que NO debe incluirse

- Codigo fuente extenso en el articulo (solo pseudocodigo relevante)
- Detalles de implementacion del dashboard en el articulo
- Metricas sin interpretacion
- Afirmaciones no soportadas por los datos
- **El split por filas (row-split) reportado como resultado valido** — solo debe aparecer junto al split por compuesto, para evidenciar la fuga de datos, nunca como metrica de desempeno del modelo
- **Afirmaciones de capacidad predictiva del modelo clasico sobre ChEMBL** (RF/SVM/SVR) — el hallazgo honesto es que NO generaliza (R² negativo); el articulo debe presentarlo como limite, no como logro
- **Mapa de exposicion / geodatos de Panama** — la Fase 6 esta PARQUEADA (falta un dataset real de uso/registro por distrito); no incluir mapas coropleticos, indices de riesgo por provincia ni capturas del mapa en ningun entregable

---

## 7. Narrativa recomendada

### Hilo conductor

1. **Problema real:** Panama usa 20+ plaguicidas activos con distintos perfiles de toxicidad
2. **Caracterizacion del corpus:** los 107 plaguicidas de ChEMBL se pueden describir y agrupar por su perfil fisicoquimico y su promiscuidad biologica (numero de dianas que afectan)
3. **Limite del enfoque clasico:** un baseline con split honesto por compuesto muestra que los descriptores moleculares globales (MW, LogP, PSA) no generalizan a compuestos no vistos (R² negativo)
4. **Solucion GNN (proyecto hermano):** operar directamente sobre el grafo molecular captura interacciones atomicas que los descriptores globales pierden
5. **Evidencia:** GIN supera RF y MLP en AUC (0.75 vs 0.74 vs 0.71) sobre Tox21
6. **Interpretabilidad:** XAI identifica los grupos funcionales toxicos correctos (P=S en organofosforados, triazol en azoles)
7. **Aplicacion:** el explorador de compuestos del dashboard permite consultar el perfil fisicoquimico, las dianas y el cluster de cada plaguicida como apoyo a MIDA/MINSA

### Limitaciones a comunicar honestamente

| Limitacion | Como comunicarla |
|---|---|
| AUC 0.75 vs objetivo 0.82 (GNN) | "El modelo demuestra la viabilidad del enfoque, con margen de mejora via pretraining o datos adicionales" |
| R² negativo con split por compuesto (ChEMBL) | "Confirma que los descriptores globales son insuficientes para generalizar — motiva el uso de grafos moleculares" |
| n=107 compuestos y familias pequenas | "Los resultados de clustering y de contraste de hipotesis deben leerse con el n de cada familia al lado; algunas familias (p. ej. Carbamates, Triazines) tienen muy pocos compuestos y no permiten generalizar" |
| `pchembl_value` mezcla 13 `standard_type` distintos | "La potencia agregada por compuesto (mediana) combina endpoints no siempre comparables entre si (Ki, IC50, EC50, LD50...); se reporta como limite metodologico" |
| Solo 20 ingredientes activos priorizados del MIDA | "Subconjunto representativo de las familias quimicas mas usadas en Panama, no el universo completo de plaguicidas registrados" |
| Geodatos de exposicion (Fase 6) | "Parqueados hasta contar con un dataset real de uso/registro de plaguicidas por distrito; no se presenta ningun mapa en este ciclo" |

---

## 8. Ejecucion

```bash
# Verificar que todos los resultados existen
make verify-results

# Generar figuras finales para el articulo (dashboard + explorador de compuestos)
make prepare-dashboard
python -c "
import os
for d in ['outputs/results', 'outputs/chembl/results', 'outputs/chembl/figures',
          'outputs/xai/figures', 'data/processed']:
    files = os.listdir(d) if os.path.isdir(d) else []
    print(f'{d}: {len(files)} archivos')
"

# (nuevo) Generar tablas A y B de este documento — funciones a implementar
# python -c "from src.analisis_proyecto.chembl_preprocessing import run_kruskal_tests, run_clustering_pipeline; ..."
# Salidas esperadas: outputs/chembl/results/stats_tests.csv, outputs/chembl/results/clustering_summary.json

# Compilar articulo LaTeX (si se usa Overleaf, subir archivos)
# pdflatex articulo_ieee.tex
# bibtex articulo_ieee
# pdflatex articulo_ieee.tex
# pdflatex articulo_ieee.tex

# Levantar dashboard para grabacion (explorador de compuestos)
make viz
```

---

## 9. Criterios de exito

- [ ] Articulo IEEE completo con las 6 secciones requeridas
- [ ] Al menos 5 figuras en el articulo, ninguna de ellas un mapa/geodatos
- [ ] Al menos 3 tablas con datos reales (Tabla 1 del proyecto hermano y Tabla C del baseline honesto son las unicas con numeros reales confirmados; Tablas A y B se completan al ejecutar el analisis)
- [ ] Video de 5-10 minutos con demo del explorador de compuestos (no del mapa)
- [ ] Presentacion de 15 slides, sin slide de mapa de Panama
- [ ] Todas las limitaciones documentadas honestamente, incluyendo n=107 y familias pequenas
- [ ] Al menos 1 caso de estudio completo (Clorpirifos, como perfil descriptivo)
- [ ] El split por filas nunca aparece como resultado valido de generalizacion, solo como contraste frente al split por compuesto
- [ ] Ninguna afirmacion de capacidad predictiva del modelo clasico sobre ChEMBL
- [ ] Referencias en formato IEEE (minimo 10)
- [ ] Articulo revisado por todos los miembros del equipo

---

## 10. Referencias a incluir

Las siguientes referencias son obligatorias en el articulo:

1. Xu et al. (2019) — "How Powerful are Graph Neural Networks?" (GIN)
2. Ying et al. (2019) — "GNNExplainer" (XAI)
3. Wu et al. (2018) — "MoleculeNet" (Tox21, benchmarks)
4. Kim et al. (2023) — "PubChem 2023 update" (fuente de datos)
5. Gaulton et al. (2017) — "ChEMBL database" (fuente de datos)
6. Fey & Lenssen (2019) — "PyTorch Geometric" (framework)

Complementarias:
7. Selvaraju et al. (2017) — Grad-CAM
8. Goh et al. (2018) — SMILES2vec
9. Kruskal & Wallis (1952) — "Use of ranks in one-criterion variance analysis" (prueba usada en Tabla A)
10. MIDA — Registro Nacional de Plaguicidas

---

## 11. Timeline de la fase

```
Dia 1: Recopilar todos los resultados, ejecutar run_kruskal_tests/run_clustering_pipeline, generar figuras finales
Dia 2: Redactar articulo IEEE (secciones asignadas por rol), incluyendo Tablas A, B y C
Dia 3: Revision cruzada del articulo, corregir
Dia 4: Grabar video, editar, subtitular
Dia 5: Disenar slides, ensayar presentacion, entrega final
```

---

*Fase anterior:* [Fase 5 — Dashboard](fase5_dashboard.md) — *(Fase 6 — Geodatos esta PARQUEADA y no forma parte del flujo activo; ver el Anexo de baseline predictivo para el puente con el proyecto GNN)*
*Primera fase:* [Fase 1 — Adquisicion de datos](fase1_adquisicion_datos.md)
