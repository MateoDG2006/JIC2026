# Perfil de toxicidad computacional — Plaguicidas de Panamá

**Fecha:** 2026-06-15  
**Modelo:** GNN-GIN entrenada sobre Tox21 (12 dianas biológicas)  
**Compuestos evaluados:** 235  
**Ingredientes activos MIDA:** 20 / 20

## Resumen ejecutivo

Este reporte resume predicciones de toxicidad multitarea y explicaciones
XAI (átomos clave) para plaguicidas del corpus panameño. Los niveles de
riesgo se basan en la probabilidad máxima entre las 12 vías Tox21:

- **ALTO**: P > 0.7
- **MODERADO**: 0.4 < P ≤ 0.7
- **BAJO**: P ≤ 0.4

### Distribución de alertas (corpus completo)

- BAJO: 171
- ALTO: 34
- MODERADO: 30

## Casos prioritarios

### Chlorpyrifos

- **Familia:** mixed
- **CID PubChem:** 2730
- **Vía crítica:** NR-AhR — Receptor aril-hidrocarburo
- **Probabilidad máxima:** 0.98
- **Nivel de alerta:** ALTO

![XAI gnnexplainer](outputs/xai/figures/chlorpyrifos_NR-AhR_gnnexplainer.svg)

![XAI gradcam](outputs/xai/figures/chlorpyrifos_NR-AhR_gradcam.svg)

---

### Atrazine

- **Familia:** mixed
- **CID PubChem:** 2256
- **Vía crítica:** SR-HSE — Estrés por calor
- **Probabilidad máxima:** 0.27
- **Nivel de alerta:** BAJO

![XAI gnnexplainer](outputs/xai/figures/atrazine_SR-HSE_gnnexplainer.svg)

![XAI gradcam](outputs/xai/figures/atrazine_SR-HSE_gradcam.svg)

---

### Tebuconazole

- **Familia:** mixed
- **CID PubChem:** 86102
- **Vía crítica:** NR-Aromatase — Aromatasa (CYP19)
- **Probabilidad máxima:** 0.81
- **Nivel de alerta:** ALTO

![XAI gnnexplainer](outputs/xai/figures/tebuconazole_NR-Aromatase_gnnexplainer.svg)

![XAI gradcam](outputs/xai/figures/tebuconazole_NR-Aromatase_gradcam.svg)

---

### Cypermethrin

- **Familia:** mixed
- **CID PubChem:** 2912
- **Vía crítica:** NR-Aromatase — Aromatasa (CYP19)
- **Probabilidad máxima:** 0.36
- **Nivel de alerta:** BAJO

![XAI gnnexplainer](outputs/xai/figures/cypermethrin_NR-Aromatase_gnnexplainer.svg)

![XAI gradcam](outputs/xai/figures/cypermethrin_NR-Aromatase_gradcam.svg)

---

### Glyphosate

- **Familia:** mixed
- **CID PubChem:** 3496
- **Vía crítica:** NR-ER — Receptor de estrógenos
- **Probabilidad máxima:** 0.35
- **Nivel de alerta:** BAJO

![XAI gnnexplainer](outputs/xai/figures/glyphosate_NR-ER_gnnexplainer.svg)

![XAI gradcam](outputs/xai/figures/glyphosate_NR-ER_gradcam.svg)

---

### Paraquat

- **Familia:** mixed
- **CID PubChem:** 15939
- **Vía crítica:** SR-ARE — Estrés oxidativo (Nrf2)
- **Probabilidad máxima:** 0.71
- **Nivel de alerta:** ALTO

![XAI gnnexplainer](outputs/xai/figures/paraquat_SR-ARE_gnnexplainer.svg)

![XAI gradcam](outputs/xai/figures/paraquat_SR-ARE_gradcam.svg)

---

## Metodología

1. Corpus molecular desde PubChem (ingredientes MIDA + familias químicas).
2. Conversión SMILES → grafo molecular (RDKit + PyTorch Geometric).
3. Predicción multitarea con GNN-GIN.
4. Explicación XAI: GNNExplainer y Grad-CAM sobre la vía de mayor riesgo.
5. Validación externa opcional contra etiquetas GHS (no usadas en entrenamiento).

*Generado automáticamente por scripts/fase5/generate_report.py*