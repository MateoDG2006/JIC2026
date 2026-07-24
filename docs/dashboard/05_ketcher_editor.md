# 05 — Dibujar-tu-molécula (editor químico → predecir)

## Objetivo

Permitir que el visitante **dibuje una estructura** a mano, se extraiga su SMILES
y se prediga en vivo. Es la pieza participativa que hoy no existe (el visor solo
acepta búsqueda por nombre o SMILES tecleado).

## Estado actual

`index.html` tiene dos pestañas: "Buscar por nombre" (PubChem) y "Analizar SMILES"
(input de texto). No hay editor gráfico.

## Elección de editor

| Editor | Pros | Contras |
|---|---|---|
| **JSME** | Un solo `.js`, sin build, offline fácil, API `getSmiles()` simple | Estética algo anticuada |
| **Ketcher** | Moderno, potente, salida MOL/SMILES | Más pesado, integración por iframe/paquete |

Recomendación para gala **offline**: empezar con **JSME** (mínima fricción,
se sirve local desde `viz/static/js/jsme/`). Migrar a Ketcher solo si se quiere
la estética premium.

## Integración (JSME)

1. Descargar JSME y colocarlo en `viz/static/js/jsme/` (servir local, sin CDN).
2. Añadir una tercera pestaña "Dibujar" en el bloque `.search-tabs` de
   `index.html` (y opcionalmente un CTA "Dibujar una molécula" en la landing).
3. Contenedor `<div id="jsme-container">` + botón "Analizar dibujo".
4. JS nuevo `viz/static/js/draw.js`:
   - Inicializar JSME en el contenedor.
   - Al pulsar "Analizar": `const smiles = jsmeApplet.smiles();`
   - Validar que no esté vacío; navegar a `/analyze?smiles=<enc>&name=Dibujo`.
5. Reusar todo el pipeline existente de `/analyze` → `molecule.js` (predicción +
   XAI + 3D). No requiere backend nuevo.

## Consideraciones

- **Validación**: si JSME devuelve SMILES inválido para RDKit, `/api/analyze` ya
  responde 400; mostrar mensaje amable ("No pude interpretar la estructura,
  revisá los enlaces").
- **Offline**: confirmar que JSME no hace requests externos.
- **Responsive**: el editor necesita ancho mínimo; en móvil, sugerir la pestaña
  de búsqueda.

## Archivos afectados

- `viz/static/js/jsme/` (nuevo, librería).
- `viz/templates/index.html` — pestaña "Dibujar" + contenedor.
- `viz/static/js/draw.js` (nuevo).
- `viz/static/css/style.css` — estilos del contenedor del editor.

## Pasos de implementación

1. Añadir JSME local a `static/`.
2. Pestaña "Dibujar" + contenedor en `index.html`.
3. `draw.js`: init + extraer SMILES + navegar a `/analyze`.
4. Manejo de errores/estructura vacía.
5. Verificar en navegador: dibujar benceno → predice sin error.

## Criterios de aceptación

- [ ] Pestaña "Dibujar" muestra el editor y funciona offline.
- [ ] "Analizar dibujo" abre el análisis en vivo con el SMILES dibujado.
- [ ] Estructura vacía o inválida muestra mensaje claro, sin romper la app.
