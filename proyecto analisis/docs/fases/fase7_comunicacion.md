# Fase 7 — Comunicación de resultados (Flujo E)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Articulo IEEE + video explicativo: caracterizacion del corpus (P1–P5) y limite predictivo honesto (P6) como puente al GNN |
| **Entradas** | Figuras y tablas de Fases 3–5, `baseline_honest_metrics.csv` (Fase 4 §12) |
| **Salidas** | Articulo PDF, video MP4, slides de defensa |
| **Rol lider** | Analista de Datos (articulo) · ML Engineer (video) |
| **Notebook** | `notebooks/fase7_comunicacion.ipynb` |

---

## 1. Narrativa central

El relato del proyecto tiene **tres actos**, no dos productos separados:

1. **Caracterizacion (Fases 1–4, P1–P5):** 107 plaguicidas panameños son describibles, agrupables y contrastables por familia en el espacio fisicoquimico-bioactivo.
2. **Limite honesto (Fase 4 §12, P6):** descriptores moleculares clasicos **no predicen** potencia en compuestos no vistos (R² bajo o negativo con split por compuesto). El contraste filas vs compuesto demuestra la fuga de datos del enfoque original.
3. **Puente al JIC:** ese limite justifica el proyecto de investigacion con **grafos moleculares + GNN-GIN** sobre Tox21 (~8 000 compuestos), donde la representacion se aprende del grafo atomo–enlace.

No presentar P6 como un "anexo" ni como fracaso oculto: es la **conclusion metodologica** que cierra la rama predictiva tabular y abre la rama del monorepo JIC.

---

## 2. Contenido obligatorio sobre P6 (baseline)

Incluir en articulo y video:

| Elemento | Fuente | Mensaje |
|---|---|---|
| Tabla split filas vs compuesto | `fase4_modelado.ipynb` §4 | Fuga vs generalizacion honesta |
| R² por compuesto | `baseline_honest_metrics.csv` | No generaliza — peor que predecir la media |
| Por que no hay predictor en dashboard | [Fase 5](fase5_dashboard.md) | Retirado por honestidad, no por bug |
| Motivacion GNN | [Fase 4 §12](fase4_modelado.md#12-bloque-4--baseline-predictivo-honesto-p6) | Descriptores globales insuficientes |

---

## 3. Figuras y tablas recomendadas

- Distribuciones y boxplots por familia (Fase 3)
- PCA + clusters + ARI vs familia (Fase 4)
- Kruskal-Wallis / Dunn con tamano de efecto (Fase 4)
- **Contraste baseline:** metricas split filas (invalido) vs split compuesto (P6)
- Capturas del explorador de compuestos (Fase 5)
- (Opcional Fase 6) Mapa solo si existe trazabilidad real

---

## 4. Criterios de exito

- [ ] Articulo IEEE con unidad de analisis = compuesto explicitada
- [ ] Seccion P6: limite descriptores + puente GNN (no omitir ni minimizar)
- [ ] Video ≤ 10 min con los tres actos de la narrativa
- [ ] Ninguna afirmacion de "prediccion de toxicidad" sobre el corpus ChEMBL de 107
- [ ] Referencias cruzadas a Fases 1–5 documentadas

---

*Fase anterior:* [Fase 5 — Dashboard](fase5_dashboard.md) · [Fase 6 — Geodatos (spec)](fase6_geodatos.md)  
*Indice:* [README del proyecto](../README.md)
