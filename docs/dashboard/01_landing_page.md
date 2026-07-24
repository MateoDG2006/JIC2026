# 01 — Landing page profesional + re-routing del visor

## Objetivo

Crear una página de entrada en `/` que presente el proyecto a nivel gala
(problema, método, números clave, casos de estudio, autores) y termine con un
**CTA "Explorar el visor →"** que lleve a la herramienta interactiva. El visor
actual se muda a `/visor`.

## Estado actual

- `/` sirve `index.html` (visor: buscador + grid del corpus).
- Navbar en `base.html` apunta a `/`, `/eda`, `/chembl/models`, `/panama/*`
  (las últimas son del proyecto de análisis, ajenas a esta app).
- No existe landing.

## Cambios de routing (exactos)

1. `viz/routes/views.py`
   - Nueva ruta `GET /` → `landing()` que renderiza `landing.html`.
   - Renombrar la ruta del visor: la función `index()` pasa a `@router.get("/visor")`
     (misma lógica, mismo template `index.html`, `active_nav="viewer"`).
2. `viz/templates/base.html`
   - `nav-brand` → `href="/"`.
   - Reemplazar los links del navbar por los de esta app JIC:
     `Inicio` (`/`), `Visor` (`/visor`), y anclas a secciones de la landing
     (`/#metodo`, `/#casos`). Quitar `/eda`, `/chembl/*`, `/panama/*` del navbar
     de esta app (pertenecen a la otra).
3. `viz/templates/molecule.html`
   - Breadcrumb: `<a href="/">Corpus</a>` → `<a href="/visor">Corpus</a>`.
4. Revisar enlaces internos que asumen que el corpus está en `/`:
   - `index.html`, `dashboard.js`, `pubchem-search.js` usan `/analyze` y
     `/molecule/{id}` (no cambian).
   - El botón "volver al corpus" y cualquier `href="/"` que deba ir al visor → `/visor`.

## Estructura de la landing (`viz/templates/landing.html`)

Secciones (una tarjeta/full-width cada una):

1. **Hero** — título del proyecto, subtítulo (GNN-GIN + XAI para toxicidad de
   agroquímicos en Panamá), CTA primario "Explorar el visor →" (`/visor`) y
   secundario "Ver metodología" (`/#metodo`).
2. **Problema** — plaguicidas en agricultura de exportación panameña; por qué
   importa a MIDA/MINSA. 2–3 frases + 3 íconos/estadísticas.
3. **Números clave** (`#numeros`) — fila de KPIs: AUC-ROC promedio, nº de
   compuestos del corpus Panamá, nº de ingredientes MIDA, 12 dianas Tox21.
   Fuente de datos: ver "Origen de los números".
4. **Método** (`#metodo`) — diagrama del pipeline SMILES → grafo → GIN → 12
   probabilidades → XAI. Reutilizar `scripts/make_etl_svg.py` / figuras de
   `outputs/` si existen, o un SVG estático.
5. **Las 12 dianas** — grid compacto con `TASK_NAMES` + `TASK_DESCRIPTIONS`
   (pasar desde el contexto de la ruta, ya disponibles en `viz/config.py`).
6. **Casos de estudio** (`#casos`) — 6 tarjetas (Clorpirifos, Atrazina,
   Tebuconazol, Cipermetrina, Paraquat, Glifosato) que enlazan a
   `/analyze?smiles=...&name=...` para abrir el análisis en vivo.
7. **Equipo / JIC 2026** — autores y afiliación.
8. **CTA final** — repetición del "Explorar el visor →".

## Origen de los números clave

Prioridad de fuentes (usar la primera que exista, con fallback):

1. `outputs/results/gin_results.csv` / `cv_summary.csv` → AUC promedio.
2. `viz/services/panama_corpus.py` (`list_compounds()`) → total y conteo MIDA.
3. Constante estática en la ruta si los artefactos no están (marcada como
   "resultado preliminar").

Opción de implementación: endpoint `GET /api/summary` que devuelva
`{auc_mean, corpus_total, mida_count, n_tasks}` leyendo lo anterior, para que la
landing pueda refrescarse sin recompilar el template. Alternativa más simple:
calcular en la ruta `landing()` y pasar por contexto Jinja.

## Diseño

Construir la landing con la skill `design-lead` para fijar jerarquía visual,
tipografía y responsive antes de escribir el HTML. Mantener el sistema de color
de `style.css`. Estilos nuevos en una sección `/* landing */` de `style.css`
(o `viz/static/css/landing.css` enlazado solo en `landing.html` vía `{% block head %}`).

## Pasos de implementación

1. Diseñar wireframe + tokens con `design-lead` (secciones, grid, tipografía).
2. `views.py`: mover visor a `/visor`, añadir `landing()` en `/`.
3. Crear `landing.html` extendiendo `base.html` con las 8 secciones.
4. Añadir estilos de landing.
5. (Opcional) `GET /api/summary` + relleno dinámico de KPIs.
6. Actualizar navbar (`base.html`) y breadcrumb (`molecule.html`).
7. Cablear los 6 casos de estudio a `/analyze?...`.
8. Verificar responsive (móvil/tablet/desktop) y modo claro/oscuro.

## Criterios de aceptación

- [ ] `/` muestra la landing; `/visor` muestra el visor; ninguna ruta 404.
- [ ] El navbar no enlaza a rutas de la otra app (`/eda`, `/chembl/*`).
- [ ] CTA "Explorar el visor" navega a `/visor`.
- [ ] Los 6 casos de estudio abren un análisis en vivo válido.
- [ ] KPIs muestran valores reales (o marcados como preliminares si faltan artefactos).
- [ ] Responsive correcto en 375 / 768 / 1280 px.
