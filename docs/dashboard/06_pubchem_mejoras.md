# 06 — Mejoras al buscador PubChem (pulido para gala)

## Objetivo

Pulir el buscador PubChem existente para que sea cómodo en una demo en vivo, sin
reconstruir nada.

## Estado actual

`viz/static/js/pubchem-search.js` + `GET /api/pubchem/search` ya funcionan:
input con debounce (350 ms), `AbortController`, tarjeta con imagen + fórmula +
peso molecular + CID, clic → `/analyze`. Comportamiento actual: "1 letra = 10
compuestos aleatorios de PubChem".

## Mejoras

### A. Chips de sugerencia MIDA (arranque sin teclear)

Debajo del input, fila de chips con los ingredientes activos MIDA prioritarios
(Clorpirifos, Atrazina, Tebuconazol, Cipermetrina, Paraquat, Glifosato, …).
Clic en un chip → rellena el input y dispara la búsqueda (o navega directo a
`/analyze` si ya tenemos su SMILES en el corpus).

- Fuente de la lista: los nombres MIDA del corpus (`panama_corpus`) o una
  constante en el template.
- UI: `.suggestion-chips` en el panel `#tab-pubchem` de `index.html`.

### B. Navegación por teclado en resultados

En la lista `#pubchem-results`: `↑/↓` mueven la selección, `Enter` abre el
resultado activo, `Esc` cierra (ya existe Esc). Añadir manejo de foco/roles ARIA
(`role="listbox"`/`option`).

### C. Cambiar el comportamiento de "1 letra = aleatorios"

Para una demo, resultados aleatorios confunden. Opciones:
- Con 0–1 caracteres: mostrar los **chips MIDA** en vez de aleatorios.
- Requerir ≥ 2 caracteres para pegarle a PubChem (ajustar `pubchem-search.js` y
  el texto de ayuda `.hint`, y opcionalmente `search_compounds` en
  `viz/services/pubchem.py`).

## Archivos afectados

- `viz/templates/index.html` — chips + `.hint` actualizado.
- `viz/static/js/pubchem-search.js` — chips, teclado, umbral de caracteres.
- `viz/static/css/style.css` — estilos de chips y estado activo de resultado.
- (Opcional) `viz/services/pubchem.py` — si se cambia la lógica de 1 carácter.

## Pasos de implementación

1. Chips MIDA en el panel de búsqueda + handler de clic.
2. Navegación por teclado + ARIA en resultados.
3. Ajustar comportamiento de pocos caracteres (chips en vez de aleatorios).
4. Verificar en navegador con teclado y con clic.

## Criterios de aceptación

- [ ] Los chips MIDA aparecen y disparan búsqueda/análisis al hacer clic.
- [ ] `↑/↓/Enter` navegan y abren resultados; `Esc` cierra.
- [ ] Con 0–1 caracteres se muestran chips, no compuestos aleatorios.
