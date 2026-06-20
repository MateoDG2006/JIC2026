# Guion video explicativo (≤ 7 minutos)

Entregable curso JIC 2026 — grabar pantalla del visor `make viz` + narración.

## Estructura sugerida

| Min | Sección | Contenido |
|-----|---------|-----------|
| 0:00–0:45 | Intro | Problema: toxicidad de plaguicidas en agricultura panameña; objetivo GNN + XAI |
| 0:45–1:30 | Datos | Pipeline ChEMBL + Tox21; corpus 235 compuestos MIDA |
| 1:30–2:30 | Visor GNN 3D | `/` — seleccionar clorpirifos, capas GIN, predicción 12 vías |
| 2:30–3:30 | XAI | `/panama/toxicity` — heatmap + SVG GNNExplainer, átomos destacados |
| 3:30–4:30 | EDA ChEMBL | `/eda` — histogramas, correlación, filtros por familia |
| 4:30–5:15 | Modelos | `/chembl/models` — predictor pChEMBL; nota split compuesto |
| 5:15–6:00 | Comparativa | `/panama/models` — baselines vs GIN, métricas honestas |
| 6:00–6:30 | Mapa | `/panama/map` — choropleth + disclaimer INEC |
| 6:30–7:00 | Cierre | Conclusiones, limitaciones, trabajo futuro |

## Checklist pre-grabación

```bash
make prepare-dashboard
make viz
# Verificar http://127.0.0.1:8000/health → status ok
```

## Narración clave (split compuesto)

> "Las métricas por fila inflan el rendimiento porque la misma molécula aparece en entrenamiento y prueba. El split por compuesto mide si el modelo generaliza a moléculas nuevas — esa es la métrica que reportamos como principal."

## Herramientas

- OBS Studio o grabador nativo Windows
- Resolución 1920×1080, 30 fps
- Exportar MP4 H.264, ≤ 100 MB si hay límite de subida
