# Fase 7 — Comunicacion de Resultados (Flujo E)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Producir articulo IEEE, video explicativo y presentacion JIC |
| **Duracion** | 4-5 dias |
| **Entradas** | Todos los resultados de Fases 1-6 |
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

Estos entregables sintetizan el trabajo de las 6 fases anteriores. Cada rol contribuye a la seccion que le corresponde.

---

## 2. Articulo IEEE

### Estructura requerida

| Seccion | Contenido | Responsable |
|---|---|---|
| **I. Introduccion** | Problema de toxicidad de plaguicidas en Panama, motivacion, objetivos | Analista de Datos |
| **II. Marco teorico** | GNN, GIN, XAI, Tox21, ChEMBL, descriptores moleculares | Cientifico de Datos |
| **III. Metodologia** | Pipeline de datos, arquitectura del modelo, protocolos de evaluacion | Ingeniero de Datos |
| **IV. Resultados** | Metricas, tablas comparativas, figuras, analisis estadistico | Cientifico de Datos |
| **V. Discusion** | Interpretacion, limitaciones, comparacion con literatura | Analista de Datos |
| **VI. Conclusiones** | Hallazgos principales, trabajo futuro | Todos |
| **Referencias** | Formato IEEE | Todos |

### Formato IEEE

```latex
\documentclass[conference]{IEEEtran}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{booktabs}

\title{Prediccion de Toxicidad de Plaguicidas Agricolas Panamenos 
       mediante Graph Neural Networks con Interpretabilidad XAI}

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
Se presenta un sistema de quimica computacional basado en Graph 
Isomorphism Networks (GIN) para predecir el perfil de toxicidad 
multitarea de plaguicidas usados en la agricultura panamena. 
El modelo, entrenado sobre grafos moleculares del dataset Tox21 
(12 dianas biologicas), alcanza un AUC-ROC promedio de 0.75, 
superando los baselines de Random Forest (0.74) y MLP (0.71). 
Las explicaciones XAI (GNNExplainer y Grad-CAM) identifican 
grupos funcionales coherentes con mecanismos de toxicidad 
documentados. Complementariamente, un analisis de datos clasico 
sobre ChEMBL demuestra que los descriptores moleculares globales 
tienen poder predictivo limitado para potencia (R² negativo 
con split por compuesto), validando la necesidad de representaciones 
estructurales como grafos moleculares.
\end{abstract}

\begin{IEEEkeywords}
graph neural networks, toxicidad, plaguicidas, XAI, Tox21, Panama
\end{IEEEkeywords}
```

### Tablas clave para el articulo

#### Tabla 1 — Comparacion de modelos (Tox21)

| Modelo | AUC-ROC promedio | Mejor tarea | Peor tarea |
|---|---|---|---|
| Random Forest + ECFP4 | 0.7433 | NR-AhR (0.86) | NR-ER (0.62) |
| MLP + ECFP4 | 0.7071 | NR-AhR (0.82) | NR-ER (0.58) |
| SMILES2vec | 0.7268 | NR-AhR (0.84) | NR-ER (0.60) |
| **GNN-GIN** | **0.7498** | NR-AhR (0.87) | NR-ER (0.65) |

*Valores reales de `outputs/results/gin_results.csv` y `baseline_results.csv`*

#### Tabla 2 — Impacto del split (ChEMBL)

| Modelo | Split filas (Acc) | Split compuesto (Acc) | Diferencia |
|---|---|---|---|
| RF Classifier | 85.1% | 37.9% | -47.2 pp |
| SVM Classifier | 82.3% | 41.2% | -41.1 pp |

#### Tabla 3 — Exposicion por provincia

| Provincia | Fraccion agricola | Indice riesgo | Plaguicidas criticos |
|---|---|---|---|
| Herrera | 60% | 0.72 | Clorpirifos, Atrazina |
| Chiriqui | 55% | 0.68 | Tebuconazol, Cipermetrina |
| Los Santos | 55% | 0.65 | Glifosato, Paraquat |

### Figuras clave

| # | Figura | Fuente | Seccion |
|---|---|---|---|
| 1 | Arquitectura GNN-GIN | Diagrama manual o draw.io | II |
| 2 | Pipeline de datos completo | Diagrama de flujo | III |
| 3 | Barras AUC por tarea (4 modelos) | `gin_results.csv` + `baseline_results.csv` | IV |
| 4 | Molecula con colores XAI (Clorpirifos) | `outputs/xai/figures/` | IV |
| 5 | Mapa coropletico de exposicion | Screenshot del dashboard | IV |
| 6 | Confusion matrix (split filas vs compuesto) | `outputs/chembl/figures/` | IV |
| 7 | Heatmap de correlacion | `outputs/chembl/figures/` | IV |

---

## 3. Video explicativo

### Estructura (5-10 minutos)

| Tiempo | Seccion | Contenido | Responsable |
|---|---|---|---|
| 0:00 - 1:00 | Introduccion | Problema, contexto Panama, pregunta de investigacion | Analista |
| 1:00 - 2:30 | Datos | Fuentes (Tox21, ChEMBL, PubChem), pipeline de extraccion | Ingeniero |
| 2:30 - 4:00 | Modelos | GNN-GIN, baselines, comparacion de metricas | Cientifico |
| 4:00 - 5:30 | XAI | GNNExplainer, Grad-CAM, visualizacion de moleculas | Cientifico |
| 5:30 - 7:00 | Dashboard | Demo en vivo del dashboard, predictor, mapa | ML Engineer |
| 7:00 - 8:30 | Resultados | Hallazgos principales, tabla comparativa | Analista |
| 8:30 - 10:00 | Conclusiones | Limitaciones, trabajo futuro, implicaciones para MIDA | Todos |

### Recomendaciones tecnicas

| Aspecto | Recomendacion |
|---|---|
| Resolucion | 1920x1080 minimo |
| Audio | Microfono externo, no built-in del laptop |
| Formato | MP4 con codec H.264 |
| Tamano | < 500 MB (comprimir si necesario) |
| Subtitulos | Opcionales pero recomendados |
| Demo del dashboard | Grabar pantalla con OBS o similar |
| Transiciones | Simples (fade), no distractoras |

---

## 4. Presentacion JIC

### Estructura de slides

| # | Slide | Contenido |
|---|---|---|
| 1 | Portada | Titulo, autores, universidad, logo JIC |
| 2 | Problema | Plaguicidas en Panama, 20 ingredientes MIDA, contexto regulatorio |
| 3 | Hipotesis | "Una GNN-GIN predice toxicidad con AUC > 0.82..." |
| 4 | Metodologia | Diagrama del pipeline (SMILES -> grafo -> GIN -> prediccion -> XAI) |
| 5 | Datos | Tox21 (12 tareas), ChEMBL (3,608 registros), PubChem (235 CIDs) |
| 6 | Modelo GIN | Arquitectura con bloques (Embedding -> GIN layers -> Readout -> Classifier) |
| 7 | Resultados GNN | Tabla AUC por tarea, barras comparativas vs baselines |
| 8 | XAI | Ejemplo Clorpirifos con molecula coloreada |
| 9 | Analisis ChEMBL | Split filas vs compuesto, R2 negativo |
| 10 | Dashboard | Screenshot del dashboard con anotaciones |
| 11 | Mapa Panama | Mapa coropletico + tabla de riesgo |
| 12 | Limitaciones | AUC 0.75 vs objetivo 0.82, R2 negativo, datos INEC |
| 13 | Conclusiones | 3 hallazgos principales |
| 14 | Trabajo futuro | Pretraining, datos ToxCast, validacion PPDB |
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
| 4 | Disenar slides de contexto | Slides 2, 3 de la presentacion |
| 5 | Investigar datos de MIDA para contextualizar | Parrafo de contexto regulatorio |

### Cientifico de Datos

| # | Tarea | Entregable |
|---|---|---|
| 1 | Redactar Marco teorico | Seccion II del IEEE paper |
| 2 | Redactar Resultados | Seccion IV del IEEE paper |
| 3 | Generar tablas comparativas | Tablas 1, 2, 3 del articulo |
| 4 | Explicar XAI en el video | Segmento 4:00-5:30 del video |
| 5 | Disenar slides de resultados | Slides 7, 8, 9 de la presentacion |

### Ingeniero de Datos

| # | Tarea | Entregable |
|---|---|---|
| 1 | Redactar Metodologia | Seccion III del IEEE paper |
| 2 | Crear diagramas de pipeline | Figuras 1, 2 del articulo |
| 3 | Documentar reproducibilidad | Seccion de datos y codigo en el articulo |
| 4 | Explicar datos en el video | Segmento 1:00-2:30 del video |
| 5 | Disenar slides de metodologia | Slides 4, 5 de la presentacion |

### ML Engineer

| # | Tarea | Entregable |
|---|---|---|
| 1 | Grabar demo del dashboard | Segmento 5:30-7:00 del video |
| 2 | Disenar slides del dashboard | Slides 10, 11 de la presentacion |
| 3 | Asegurar que el dashboard esta funcional para la demo | Dashboard corriendo sin errores |
| 4 | Compilar articulo en LaTeX | PDF final del articulo |
| 5 | Editar video final | MP4 con transiciones y audio limpio |

---

## 6. Contenido critico para cada entregable

### Lo que DEBE incluirse

| Elemento | Articulo | Video | Slides |
|---|---|---|---|
| Tabla AUC por tarea (4 modelos) | Si | Mencion | Si |
| Molecula XAI coloreada | Si (figura) | Si (visual) | Si |
| Comparacion split filas vs compuesto | Si (tabla) | Mencion | Si |
| Mapa de Panama | Si (figura) | Demo | Si |
| Limitacion: AUC 0.75 vs 0.82 | Si (discusion) | Mencion | Si |
| Limitacion: R2 negativo | Si (discusion) | Mencion | Si |
| Caso estudio Clorpirifos | Si (detallado) | Si (visual) | Si |
| Formula exposure_risk | Si | No | Opcional |
| Hiperparametros del modelo | Si (tabla) | No | No |
| Codigo fuente (enlaces) | Si (referencia) | No | Si (slide final) |

### Lo que NO debe incluirse

- Codigo fuente extenso en el articulo (solo pseudocodigo relevante)
- Detalles de implementacion del dashboard en el articulo
- Metricas sin interpretacion
- Afirmaciones no soportadas por los datos

---

## 7. Narrativa recomendada

### Hilo conductor

1. **Problema real:** Panama usa 20+ plaguicidas activos con distintos perfiles de toxicidad
2. **Limitacion del enfoque clasico:** Los descriptores moleculares globales (MW, LogP) no predicen bien la toxicidad (R2 negativo en split honesto)
3. **Solucion GNN:** Operar directamente sobre el grafo molecular captura interacciones atomicas que los descriptores globales pierden
4. **Evidencia:** GIN supera RF y MLP en AUC (0.75 vs 0.74 vs 0.71)
5. **Interpretabilidad:** XAI identifica los grupos funcionales toxicos correctos (P=S en organofosforados, triazol en azoles)
6. **Aplicacion:** Mapa de riesgo + perfil de toxicidad = herramienta para MIDA/MINSA

### Limitaciones a comunicar honestamente

| Limitacion | Como comunicarla |
|---|---|
| AUC 0.75 vs objetivo 0.82 | "El modelo demuestra la viabilidad del enfoque, con margen de mejora via pretraining o datos adicionales" |
| R2 negativo en regresion ChEMBL | "Confirma que descriptores globales son insuficientes — motiva el uso de GNN" |
| Datos INEC hardcodeados | "Basados en publicaciones del INEC 2023, no en API en tiempo real" |
| Solo 20 compuestos MIDA | "Subconjunto representativo de las familias quimicas mas usadas en Panama" |
| Jitter deterministico en geodatos | "Simula variabilidad; datos reales a nivel distrito requieren acceso al INEC" |

---

## 8. Ejecucion

```bash
# Verificar que todos los resultados existen
make verify-results

# Generar figuras finales para el articulo
make prepare-dashboard
python -c "
import os
for d in ['outputs/results', 'outputs/chembl/results', 'outputs/chembl/figures',
          'outputs/xai/figures', 'data/processed']:
    files = os.listdir(d) if os.path.isdir(d) else []
    print(f'{d}: {len(files)} archivos')
"

# Compilar articulo LaTeX (si se usa Overleaf, subir archivos)
# pdflatex articulo_ieee.tex
# bibtex articulo_ieee
# pdflatex articulo_ieee.tex
# pdflatex articulo_ieee.tex

# Levantar dashboard para grabacion
make viz
```

---

## 9. Criterios de exito

- [ ] Articulo IEEE completo con las 6 secciones requeridas
- [ ] Al menos 5 figuras en el articulo
- [ ] Al menos 3 tablas con datos reales
- [ ] Video de 5-10 minutos con demo del dashboard
- [ ] Presentacion de 15 slides
- [ ] Todas las limitaciones documentadas honestamente
- [ ] Al menos 1 caso de estudio completo (Clorpirifos recomendado)
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
9. MIDA — Registro Nacional de Plaguicidas
10. INEC — Censos y encuestas de Panama

---

## 11. Timeline de la fase

```
Dia 1: Recopilar todos los resultados, generar figuras finales
Dia 2: Redactar articulo IEEE (secciones asignadas por rol)
Dia 3: Revision cruzada del articulo, corregir
Dia 4: Grabar video, editar, subtitular
Dia 5: Disenar slides, ensayar presentacion, entrega final
```

---

*Fase anterior:* [Fase 6 — Geodatos de Panama](fase6_geodatos.md)  
*Primera fase:* [Fase 1 — Adquisicion de datos](fase1_adquisicion_datos.md)
