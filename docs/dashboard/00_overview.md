# Integraciones del dashboard JIC 2026 — Índice y plan

Estos documentos describen **paso a paso** cada mejora interactiva del visor GNN
(`viz/`, app FastAPI) pensada para la Jornada de Iniciación Científica (JIC 2026).
No incluyen código de otras apps: todo lo que aquí se documenta usa **solo datos
JIC** (Tox21 + corpus Panamá). El dashboard de analytics ChEMBL vive aparte en
`proyecto analisis/viz/` y no se toca.

> Metodología acordada con el autor: **primero documentar, luego construir poco a
> poco**, confirmando antes de cada integración.

## Decisión de routing (confirmada)

- `/` → **Landing page** (nueva, elegante, punto de entrada).
- `/visor` → visor GNN actual (hoy en `/`).
- `/molecule/{id}`, `/analyze` → sin cambio de ruta; solo se actualizan enlaces
  internos y el navbar.

## Estado del código actual (línea base)

Ya implementado y funcionando (no se reconstruye):

| Pieza | Dónde | Estado |
|---|---|---|
| Búsqueda PubChem por nombre + tarjeta (imagen, fórmula, MW, CID) | `viz/static/js/pubchem-search.js`, `GET /api/pubchem/search` | ✅ |
| Visor 3D (3Dmol.js): ball-stick, toggle estilo, reset, coloreo XAI, hover átomo | `viz/static/js/viewer3d.js` | ✅ |
| Render 2D SVG coloreado por XAI (RDKit) | `POST /api/svg` | ✅ |
| Export STL (impresión 3D + llavero con placa) | `GET /api/stl` | ✅ |
| Predicción GIN 12 dianas | `POST /api/predict`, `POST /api/analyze` | ✅ |
| XAI Grad-CAM / GNNExplainer / modo Comparar (alterna) | `POST /api/explain`, `molecule.js` | ✅ |
| Tabla de importancia por átomo con hover→3D | `molecule.js` | ✅ |
| Selector de diana (Grad-CAM por vía) | `#task-select` en `molecule.html` | ✅ |

## Integraciones documentadas (a construir)

| # | Doc | Qué agrega | Backend nuevo | Esfuerzo |
|---|---|---|---|---|
| 01 | [`01_landing_page.md`](01_landing_page.md) | Landing profesional en `/` + re-routing del visor a `/visor` | ruta + (opcional) `/api/summary` | Medio |
| 02 | [`02_xai_avanzado.md`](02_xai_avanzado.md) | Slider de umbral + panel de fidelidad del subgrafo + comparar lado a lado | `POST /api/fidelity` | Medio |
| 03 | [`03_narrativa_ghs_heatmap.md`](03_narrativa_ghs_heatmap.md) | Heatmap compuesto×diana + panel Predicción vs GHS/PPDB | `GET /api/panama/matrix`, `GET /api/panama/ghs` | Medio |
| 04 | [`04_mapa_quimico.md`](04_mapa_quimico.md) | Scatter UMAP de embeddings GIN (Tox21 + Panamá) | script precómputo + `GET /api/embeddings` | Medio-alto |
| 05 | [`05_ketcher_editor.md`](05_ketcher_editor.md) | Dibujar-tu-molécula (Ketcher/JSME) → predecir | ninguno | Bajo-medio |
| 06 | [`06_pubchem_mejoras.md`](06_pubchem_mejoras.md) | Chips MIDA + navegación por teclado + arranque sin teclear | ninguno | Bajo |

## Orden de construcción propuesto

1. **Landing (01)** — define routing y estética; envuelve todo lo demás.
2. **XAI avanzado (02)** — el diferenciador técnico del proyecto.
3. **Narrativa (03)** — la vista institucional MIDA/MINSA.
4. **Mapa químico (04) + Ketcher (05) + PubChem (06)** — cierre.

Cada integración se implementa, se prueba en el navegador y se confirma antes de
pasar a la siguiente.

## Convenciones

- Estética coherente con `viz/static/css/style.css` (mismo sistema de color/tipografía).
- Endpoints nuevos bajo `/api/*` en `viz/routes/api.py`; vistas HTML en `viz/routes/views.py`.
- Sin dependencias externas por CDN si se puede evitar (la app corre offline en la
  gala): librerías JS se sirven desde `viz/static/js/` (como ya se hace con `3Dmol-cdn.js`).
- Criterio de aceptación de cada doc = lista verificable al final del archivo.
