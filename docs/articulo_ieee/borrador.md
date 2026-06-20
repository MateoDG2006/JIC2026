# Borrador artículo IEEE (≤ 7 páginas)

> Entregable curso JIC 2026 — expandir y formatear según plantilla IEEE.

## Título

Predicción de toxicidad de agroquímicos panameños con Graph Neural Networks e inteligencia artificial explicable

## Autores

[Nombre], Universidad [Institución], Panamá — email@ejemplo.com

## Resumen

Presentamos un pipeline de química computacional que combina extracción ChEMBL, entrenamiento GNN-GIN sobre Tox21, baselines QSAR y explicaciones XAI (GNNExplainer, Grad-CAM) aplicadas a plaguicidas del corpus MIDA/PubChem. Un visor web unificado (FastAPI) integra predicciones, EDA interactivo y mapa sociodemográfico de Panamá. Reportamos métricas bajo split por compuesto (generalización honesta) y scaffold 5-fold CV para el modelo grafo.

**Palabras clave:** GNN, toxicidad, Tox21, XAI, agroquímicos, Panamá.

## I. Introducción

La evaluación regulatoria de plaguicidas requiere perfilar toxicidad en múltiples vías biológicas. Los modelos QSAR clásicos operan sobre fingerprints; las GNN aprenden directamente sobre grafos moleculares. Hipótesis: una GNN-GIN entrenada en Tox21 supera baselines y las explicaciones XAI identifican grupos funcionales coherentes con la literatura.

## II. Metodología

### A. Datos

- **Tox21:** 12 tareas, scaffold split, grafos RDKit/PyG (45 features nodo, 9 enlace).
- **Corpus Panamá:** 235 compuestos PubChem + bioactividad ChEMBL SQLite.
- **Validación externa:** etiquetas GHS PubChem.

### B. Modelos

| Modelo | Representación | Protocolo |
|--------|----------------|-----------|
| Random Forest | Morgan ECFP4 | 5-fold scaffold |
| MLP | ECFP4 | 5-fold scaffold |
| SMILES2vec | secuencia SMILES | 5-fold scaffold |
| GIN | grafo molecular | 5-fold scaffold, hidden=256, 4 capas |

Pérdida: BCE enmascarada para etiquetas NaN. Scheduler: warmup + cosine decay.

### C. XAI

GNNExplainer y Grad-CAM sobre átomos; validación química con SMARTS de grupos tóxicos (precision@k).

### D. Analítica ChEMBL (curso)

EDA (missingno, UpSetPlot), clasificación RF/SVM, regresión pChEMBL RF/SVR. **Métrica principal:** split por compuesto (ver `docs/analisis_proyecto/METRICAS_EVALUACION.md`).

## III. Resultados

- Baselines Tox21: RF AUC ~0.74, GIN AUC ~0.75 (objetivo 0.82 — requiere re-entrenamiento con `make train-gin-cv`).
- ChEMBL clasificación: accuracy compuesto ~0.38 vs filas ~0.76 (leakage documentado).
- XAI: 98 figuras SVG para plaguicidas MIDA; casos clorpirifos (SR-ARE), atrazina (NR-ER), paraquat (SR-p53).

## IV. Discusión

El split por compuesto revela límites de descriptores sin contexto de ensayo. La GNN aporta ventaja modesta sobre RF en configuración actual; el valor diferencial está en explicabilidad atómica para actores MIDA/MINSA. Datos sociodemográficos del mapa son estimaciones geográficas — disclaimer en UI.

## V. Conclusiones

Pipeline reproducible integrado en un visor FastAPI. Trabajo futuro: edge features en message passing, datos INEC oficiales, re-entrenamiento GIN con hiperparámetros auditados.

## Referencias

[1] Xu et al., ICLR 2019. [2] Wu et al., MoleculeNet 2018. [3] Ying et al., NeurIPS 2019. [4] Kim et al., PubChem 2023.

---

*Completar tablas de AUC por tarea tras ejecutar `make train-gin-cv`.*
