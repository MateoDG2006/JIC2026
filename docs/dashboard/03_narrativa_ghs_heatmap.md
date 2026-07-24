# 03 — Narrativa institucional: heatmap compuesto×diana + validación GHS/PPDB

## Objetivo

Dar una vista panorámica que un evaluador MIDA/MINSA entienda de un vistazo, y
cerrar la historia científica mostrando que las predicciones **se validan contra
etiquetas regulatorias reales (GHS)** y datos experimentales (PPDB).

## Estado actual

- Predicciones por compuesto disponibles vía modelo (`/api/analyze`) y, si existe,
  en `outputs/reports/panama_pesticides_profile.csv` (`TOXICITY_PROFILE_CSV`).
- Validación GHS ya existe como script/notebook: `scripts/fase5/validate_ghs.py`,
  `notebooks/07_ghs_validation.ipynb`, y etiquetas en
  `data/raw/pubchem_ghs_labels.csv`.
- Nada de esto está expuesto en el dashboard todavía.

## Pieza A — Heatmap compuesto × 12 dianas

Matriz interactiva: filas = compuestos del corpus Panamá, columnas = 12 dianas
Tox21, color = probabilidad predicha. Celdas clicables → `/molecule/{id}` o
`/analyze?...`.

**Datos.** Nuevo endpoint `GET /api/panama/matrix`:

```
Response: {
  tasks: [...12...],
  compounds: [{ id, name, family, mida, probs: {task: prob, ...} }, ...]
}
```

Fuente en orden de preferencia:
1. `outputs/reports/panama_pesticides_profile.csv` si contiene las 12 columnas
   de probabilidad (léelo con el servicio existente `panama_corpus`).
2. Si no, generar bajo demanda con `inference.predict` por compuesto y **cachear**
   en memoria (el corpus es pequeño, ~30–150 moléculas). Añadir un flag/estado
   "calculando…" para la primera carga.

**Front.** Nueva vista `GET /panama` (o sección en la landing) con:
- Tabla-heatmap propia (CSS grid + color por probabilidad, misma paleta YlOrRd
  que XAI) **o** Plotly.js heatmap servido localmente. Recomendado empezar con
  CSS grid para no añadir dependencia; migrar a Plotly si se quiere zoom/tooltip.
- Ordenar filas por familia; filtro "solo MIDA"; hover muestra prob exacta.
- Clic en celda o fila → página de la molécula con esa diana preseleccionada
  (`/analyze?smiles=...` + query `task=`).

## Pieza B — Panel Predicción vs GHS/PPDB

Tabla que enfrenta, por compuesto, la predicción del modelo contra la etiqueta
GHS real y (si hay) el dato PPDB, con indicador ✓/✗ de coincidencia.

**Datos.** Nuevo endpoint `GET /api/panama/ghs`:
- Cargar `data/raw/pubchem_ghs_labels.csv` (columnas ya definidas en CLAUDE.md:
  `toxic_oral`, `endocrine_risk`, `genotoxic`, `aquatic_tox`, `ghs_codes`).
- Reutilizar el mapeo de `scripts/fase5/validate_ghs.py` (correlación
  GHS↔diana Tox21: H360/H361→NR-AR/NR-ER; H340/H350→SR-p53/SR-AtAD5;
  H300–H331→SR-ARE/SR-MMP). **No duplicar lógica**: importar/compartir la función
  del script o factorizarla a `src/evaluation/`.
- Devolver por compuesto: `{ name, cid, ghs_flags, model_flags, matches: {...},
  agreement: bool }`.

**Front.** En la vista `/panama` (pestaña "Validación GHS"):
- Tabla con columnas: Compuesto · Riesgo GHS (badges H-codes) · Predicción modelo
  (diana correspondiente) · Coincidencia (✓/✗).
- Resumen arriba: "% de acuerdo modelo↔GHS" por categoría (agudo, endocrino,
  genotóxico, acuático).

## Archivos afectados

- `viz/routes/api.py` — `GET /api/panama/matrix`, `GET /api/panama/ghs`.
- `viz/routes/views.py` — `GET /panama` (vista narrativa).
- `viz/services/` — helper para leer/calcular la matriz y el cruce GHS
  (posible `viz/services/narrative.py`).
- `src/evaluation/` — factorizar el mapeo GHS↔diana si hoy vive solo en el script.
- `viz/templates/panama.html` (nueva) + estilos.
- Navbar: añadir enlace "Panamá / Validación".

## Pasos de implementación

1. Factorizar mapeo GHS↔diana a una función reutilizable.
2. `GET /api/panama/ghs` + `GET /api/panama/matrix` (con caché).
3. Vista `/panama.html`: heatmap (CSS grid) + tabla GHS.
4. Cablear celdas del heatmap → página de molécula.
5. Resúmenes de acuerdo por categoría.
6. Enlazar desde landing (sección "Resultados") y navbar.
7. Verificar contra un compuesto conocido (Atrazina: disruptor endocrino → NR-AR/ER).

## Criterios de aceptación

- [ ] `/panama` muestra el heatmap de todo el corpus con color por probabilidad.
- [ ] Clic en una celda abre la molécula con la diana correcta.
- [ ] La tabla GHS muestra coincidencias ✓/✗ y el % de acuerdo por categoría.
- [ ] La lógica GHS↔diana no está duplicada (una sola fuente de verdad).
- [ ] Si faltan artefactos, la vista informa cómo generarlos (mensaje claro).
