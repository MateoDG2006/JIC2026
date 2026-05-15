# Documentación del Proyecto — GNN + XAI para Toxicidad de Agroquímicos

**Proyecto:** Predicción de Toxicidad de Agroquímicos con GNN-GIN + Explainable AI  
**Contexto:** Plaguicidas de la agricultura de exportación panameña (MIDA/MINSA)  
**Duración:** 10 semanas

---

## Hipótesis

> Una GNN-GIN entrenada sobre grafos moleculares del dataset Tox21 predice el perfil de toxicidad multitarea de plaguicidas agrícolas panameños con AUC-ROC superior a modelos QSAR clásicos, y las explicaciones XAI identifican grupos funcionales químicamente coherentes con los mecanismos de toxicidad documentados.

---

## Índice de documentación

| Documento | Módulos | Fase |
|---|---|---|
| [01 — Pipeline de Datos](01_pipeline_datos.md) | `src/data/` | I (Sem 1–2) |
| [02 — Modelo GNN-GIN](02_modelo_gin.md) | `src/models/gin.py` | III (Sem 5–6) |
| [03 — Baselines](03_baselines.md) | `src/models/baselines.py` | II (Sem 3–4) |
| [04 — Entrenamiento](04_entrenamiento.md) | `src/training/`, `src/evaluation/cross_validation.py` | III (Sem 5–6) |
| [05 — XAI](05_xai.md) | `src/xai/`, `src/evaluation/chemical_coherence.py` | IV (Sem 7–8) |
| [06 — Aplicación Panamá](06_aplicacion_panama.md) | `notebooks/06_*`, `notebooks/07_*` | V (Sem 9–10) |

---

## Cronograma

```
SEMANA  1   2   3   4   5   6   7   8   9  10
────────────────────────────────────────────────
FASE I  ████████
  Entorno, datos Tox21, grafo molecular,
  scaffold split, corpus panameño PubChem

FASE II         ████████
  RF + Morgan, MLP + Morgan, SMILES2vec
  (todos deben superar AUC ~0.77 para validar pipeline)

FASE III              ████████
  GNN-GIN, 5-fold CV, ablation study
  (objetivo: AUC > 0.82)

FASE IV                       ████████
  GNNExplainer, Grad-CAM, validación química
  (objetivo: Precision@3 > 80%)

FASE V                                ████████
  Corpus panameño, reportes MIDA/MINSA,
  presentación JIC
────────────────────────────────────────────────
◉ Hito: Pipeline validado       → fin semana 2
◉ Hito: Baselines > 0.77        → fin semana 4
◉ Hito: GNN AUC > 0.82          → fin semana 6
◉ Hito: XAI coherencia > 80%    → fin semana 8
◉ Hito: Reportes MIDA listos    → fin semana 10
```

---

## Stack tecnológico

| Categoría | Herramienta | Rol |
|---|---|---|
| Química computacional | RDKit ≥ 2023.09 | Canonicalización, grafos, fingerprints |
| Deep learning | PyTorch ≥ 2.0 | Framework principal |
| GNN | PyTorch Geometric ≥ 2.4 | GINConv, pooling, GNNExplainer |
| XAI | Captum | Grad-CAM adaptado a grafos |
| Datasets | DeepChem ≥ 2.7 | Loader Tox21, scaffold split |
| Logging | Weights & Biases | Tracking de experimentos |
| Datos externos | PubChem API | Corpus panameño trazable |
| Validación | PPDB | Datos experimentales de plaguicidas |
| Cómputo | Google Colab Pro (A100) | 5-fold CV en ~4–6h |

---

## Métricas objetivo

| Métrica | Mínimo | Objetivo |
|---|---|---|
| AUC-ROC promedio (GNN) | > 0.82 | > 0.84 |
| Supera RF baseline | Obligatorio | +0.05 AUC |
| Supera SMILES2vec | Objetivo principal | +0.02 AUC |
| Precision@3 XAI | > 80% | — |
| Coherencia GNNExp vs GradCAM | Spearman > 0.70 | — |
