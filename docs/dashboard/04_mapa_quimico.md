# 04 — Mapa del espacio químico (embeddings GIN, solo JIC)

## Objetivo

Mostrar un scatter 2D del **espacio químico aprendido por el GIN**: proyectar los
embeddings del readout a 2D (UMAP) y visualizar dónde caen los plaguicidas
panameños respecto al dataset de entrenamiento Tox21. Evidencia visual directa de
la tesis de **generalización / dominio de aplicabilidad**.

> Alcance: **solo datos JIC** → Tox21 (entrenamiento) + corpus Panamá. No usa
> ChEMBL ni nada del proyecto de análisis.

## Concepto

Cada molécula → vector embedding `h_G` (el `CONCAT(mean_pool, max_pool)` de
dimensión `2·hidden_dim`, justo antes del clasificador). UMAP reduce a 2D.
En el scatter: color = probabilidad de la diana crítica (o pertenencia MIDA),
hover = estructura 2D + nombre.

## Obtener el embedding sin tocar el modelo

`GINToxicity.forward` devuelve logits. Para extraer `h_G` sin modificar
`src/models/gin.py`, usar un **forward hook** sobre la primera capa del
clasificador (su *input* es exactamente `h_G`):

1. Localizar el primer `nn.Linear` de `model.classifier`.
2. Registrar `register_forward_hook` que capture el tensor de entrada.
3. Correr `predict`/forward y leer el tensor capturado.

(Alternativa: añadir un método `embed(...)` al modelo que retorne `h_g`; el hook
evita cambiar `src/` y es preferible para no re-entrenar/serializar nada.)

## Precómputo (offline)

Script nuevo `scripts/fase5/build_embeddings.py`:

1. Cargar modelo (`viz.services.inference.get_model`) y device.
2. Fuente de moléculas:
   - Tox21: SMILES del split de entrenamiento (desde el pipeline de datos ya
     existente; ver `scripts/fase1/prepare_tox21_graphs.py` / `src/data/`).
   - Panamá: `pubchem_panama_cids.csv` (via `viz.services.panama_corpus`).
3. Para cada SMILES: `smiles_to_graph` → forward con hook → `h_G` (numpy).
4. UMAP (`umap-learn`) a 2D. Fijar `random_state` para reproducibilidad.
5. Volcar `viz/data/embeddings_umap.json`:

```
{
  "points": [
    { "x": .., "y": .., "smiles": "..", "name": "..",
      "source": "tox21"|"panama", "family": "..", "mida": bool,
      "top_task": "..", "top_prob": .. },
    ...
  ],
  "meta": { "n_tox21": .., "n_panama": .., "created": ".." }
}
```

> Nota: UMAP es dependencia nueva (`umap-learn`). Si se quiere evitar, usar
> t-SNE/PCA de scikit-learn (ya disponible). Documentar la elección en el script.

## Endpoint y vista

- `GET /api/embeddings` → sirve `embeddings_umap.json` (404 con mensaje si no se
  precomputó).
- `GET /mapa-quimico` (vista) → scatter interactivo.

**Front (scatter).** Recomendado Plotly.js servido localmente (`viz/static/js/`):
- Puntos Tox21 en gris tenue (contexto), Panamá resaltados por familia/MIDA.
- Color por `top_prob` (paleta YlOrRd) o toggle "colorear por: probabilidad /
  familia / fuente".
- Hover: nombre + imagen 2D (usar `/api/svg` sin importancia, o miniatura RDKit).
- Clic en punto Panamá → `/analyze?smiles=...`.
- Leyenda + filtro "solo Panamá / solo MIDA".

## Archivos afectados

- `scripts/fase5/build_embeddings.py` (nuevo).
- `viz/services/inference.py` — helper `embed(smiles)` vía hook (o servicio aparte).
- `viz/routes/api.py` — `GET /api/embeddings`.
- `viz/routes/views.py` — `GET /mapa-quimico`.
- `viz/templates/mapa_quimico.html` (nueva) + `viz/static/js/chemmap.js`.
- `requirements.txt` — `umap-learn` (o usar sklearn t-SNE).

## Pasos de implementación

1. Helper de embedding vía forward hook + prueba con 2–3 SMILES.
2. `build_embeddings.py`: recolectar SMILES Tox21 + Panamá, calcular `h_G`, UMAP,
   volcar JSON.
3. `GET /api/embeddings` + vista `/mapa-quimico`.
4. Scatter Plotly con color/hover/clic.
5. Filtros y leyenda; verificar que Panamá cae mayormente dentro de Tox21
   (o documentar las zonas fuera de dominio).

## Criterios de aceptación

- [ ] `build_embeddings.py` genera `embeddings_umap.json` reproducible.
- [ ] `/mapa-quimico` renderiza el scatter con Tox21 (contexto) + Panamá (resaltado).
- [ ] Hover muestra estructura + nombre; clic en punto Panamá abre el análisis.
- [ ] Toggle de coloreo (probabilidad / familia / fuente) funciona.
- [ ] Sin dependencias del proyecto de análisis (solo Tox21 + Panamá).
