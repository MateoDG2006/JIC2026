# 02 — XAI avanzado: slider de umbral, fidelidad del subgrafo, comparar lado a lado

## Objetivo

Completar la interactividad XAI para que el jurado no solo **vea** la explicación
sino que la **manipule** y compruebe que es **fiel** al modelo.

## Estado actual (línea base)

`molecule.js` ya tiene: Grad-CAM, GNNExplainer, modo "Comparar" (alterna),
tabla de importancia por átomo con hover→resalte 3D, coloreo sincronizado
3D+2D, y selector de diana. Endpoints: `POST /api/explain`, `POST /api/svg`,
`POST /api/xai-colors`.

## Piezas a agregar

### A. Slider de umbral de importancia (front-end puro)

Un control `range` (0–100 %) que filtra qué átomos se iluminan: solo se colorean
los átomos con `importance ≥ umbral`; el resto se muestran neutros. El visitante
"sube el volumen" de la explicación y ve emerger el grupo funcional tóxico.

- UI: nuevo `.control-row` en la tarjeta "Explicación XAI" de `molecule.html`
  con `<input type="range" id="xai-threshold">` y etiqueta de valor.
- Lógica en `molecule.js`: al mover el slider, recalcular el vector de importancia
  aplicando la máscara (`imp[i] = imp[i] >= t ? imp[i] : 0`) y repintar 3D
  (`MoleculeViewer3D.applyAtomColors`) + tabla. El 2D SVG puede repintarse
  llamando a `/api/svg` con el vector enmascarado (con debounce ~150 ms) o —para
  fluidez— con RDKit.js (ver doc 05/nota abajo).
- Sin backend nuevo: opera sobre `state.xai[...]` ya en memoria.

> Nota de rendimiento: si el repintado del SVG por slider se siente lento por el
> round-trip a `/api/svg`, evaluar RDKit.js (WASM) para repintar el 2D en el
> cliente. Es un *habilitador de fluidez*, opcional.

### B. Panel de fidelidad del subgrafo (backend + front)

Demuestra que la explicación es fiel: se **conservan solo los top-k átomos más
importantes** (según el método/diana activos), se re-predice con el resto
enmascarado, y se compara la probabilidad contra la predicción completa.

**Backend — nuevo endpoint** `POST /api/fidelity`:

```
Request:  { smiles, task, method="gradcam", k }
Response: { task, k, prob_full, prob_topk, prob_masked_out,
            kept_atoms: [idx...], fidelity_drop }
```

Implementación en `viz/services/inference.py` (función nueva
`predict_masked(smiles, keep_indices)`):

1. `graph = smiles_to_graph(smiles)`.
2. Clonar `graph.x`; para cada átomo `i ∉ keep_indices`, poner su fila de
   features a cero (`x[i] = 0`). Mantener `edge_index`/`edge_attr` intactos
   (enmascarado de features, no borrado de nodos — pragmático y estable).
3. Reejecutar el modelo (mismo forward que `predict`) y devolver la prob de `task`.
4. `prob_topk` = predicción conservando top-k; `prob_masked_out` = predicción
   conservando el **complemento** (los no importantes) — si el modelo es fiel,
   `prob_topk ≈ prob_full` y `prob_masked_out` cae.
5. `fidelity_drop = prob_full − prob_masked_out` (deseable alto).

> Caveat a documentar en la UI: enmascarar features a cero es una aproximación
> (no equivale a eliminar el átomo del grafo); sirve como evidencia visual de
> fidelidad, no como métrica formal de sufficiency/comprehensiveness.

**Front — nuevo panel** en `molecule.html` (tarjeta "Fidelidad"):

- Slider/`select` de `k` (p. ej. 1–10 átomos).
- Al cambiar `k`: llamar `/api/fidelity`, mostrar dos barras
  (`prob_full` vs `prob_topk` y vs `prob_masked_out`) y un texto tipo
  "Con solo los 5 átomos clave el modelo mantiene 0.82 (completo 0.85)".
- Resaltar en 3D/2D los `kept_atoms` devueltos.

### C. Comparar lado a lado (mejora del modo existente)

Hoy "Comparar" alterna entre métodos. Cambiarlo a mostrar **dos SVG en paralelo**
(Grad-CAM | GNNExplainer) para la misma diana, con la correlación de Spearman
del ranking de átomos como pie de figura.

- Front: en modo `compare`, `update2dSvg()` genera ambos SVG (dos llamadas a
  `/api/svg`) y los coloca en un grid de 2 columnas dentro de `#viewer-2d`.
- Spearman: calcularlo en cliente sobre los dos vectores de importancia, o
  añadir al endpoint `/api/explain` un modo que devuelva ambos + la correlación.

## Archivos afectados

- `viz/routes/api.py` — nuevo `POST /api/fidelity` (+ modelo Pydantic).
- `viz/services/inference.py` — `predict_masked()` / `fidelity()`.
- `viz/templates/molecule.html` — controles slider umbral, panel fidelidad,
  contenedor 2×SVG.
- `viz/static/js/molecule.js` — lógica de umbral, fidelidad, comparar lado a lado.
- `viz/static/css/style.css` — estilos de los nuevos controles.

## Pasos de implementación

1. Backend fidelidad: `predict_masked()` en `inference.py` + `POST /api/fidelity`.
2. Front slider de umbral (repinta 3D + tabla; SVG con debounce).
3. Front panel de fidelidad (barras + resalte de kept_atoms).
4. Comparar lado a lado (2×SVG + Spearman).
5. (Opcional) RDKit.js para repintado 2D instantáneo del slider.
6. Verificar en navegador con Clorpirifos (P=S debe dominar en SR-ARE).

## Criterios de aceptación

- [ ] El slider filtra átomos iluminados en 3D y tabla en tiempo real.
- [ ] `/api/fidelity` responde y el panel muestra prob_full vs prob_topk.
- [ ] Con top-k pequeño la prob se mantiene y con el complemento cae (caso demo).
- [ ] Modo comparar muestra los dos métodos en paralelo con Spearman.
- [ ] Caveat de enmascarado visible en la UI del panel de fidelidad.
