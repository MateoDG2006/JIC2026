# Fase 6 — Geodatos de Panamá (Flujo D) — Especificación futura

> **Estado:** no implementada. El código previo (`geodata_panama.py`, notebook y CLI) fue retirado.
> Este documento es la **spec de reimplementación** cuando exista un dataset que vincule
> plaguicidas con geografía en Panamá.

## Resumen

| Campo | Valor |
|---|---|
| **Estado** | Pendiente — fuera del pipeline activo (Fases 1–5, 7) |
| **Objetivo** | Mapa coroplético en el dashboard analytics que contextualice el corpus de 107 compuestos con geografía panameña **solo si hay trazabilidad real** compuesto ↔ ubicación |
| **Rol líder (futuro)** | Ingeniero de Datos |
| **App destino** | `proyecto analisis/viz/` — ruta `/panama/map`, API `/api/analytics/geo*` |
| **Prerequisito bloqueante** | Dataset verificable de uso/registro/distribución de plaguicidas por unidad geográfica (ver §2) |

---

## 1. Por qué no está implementada

El enfoque anterior combinaba:

- GeoJSON de distritos (geoBoundaries ADM2)
- Constantes sociodemográficas del INEC con **jitter determinístico** por distrito
- Un índice `exposure_risk` sin vínculo con los 107 compuestos del corpus ChEMBL

Eso no cumple el estándar metodológico del resto del proyecto (honestidad, unidad de análisis clara, trazabilidad a fuente primaria). **No se debe reintroducir jitter ni índices sintéticos** como si fueran mediciones.

La Fase 6 se retoma únicamente cuando el mapa responda una pregunta defendible, por ejemplo:

> ¿En qué distritos/provincias hay mayor presencia registrada de familias químicas representadas en nuestro corpus?

---

## 2. Requisitos de datos (gate de activación)

Activar la fase solo si se consigue **al menos una** fuente con trazabilidad:

| Prioridad | Fuente | Qué aporta |
|---|---|---|
| Alta | **MIDA** — registro/distribución de plaguicidas por distrito o provincia | Ingrediente activo o producto ↔ ubicación |
| Alta | **INEC / Censo agropecuario** — superficie y rubro por distrito | Exposición potencial vía cultivo (banano → organofosforados, etc.) |
| Media | **PubChem / corpus propio** enriquecido con metadatos geográficos verificables | Vínculo explícito compuesto/familia ↔ región |

Checklist antes de escribir código:

- [ ] Documentar fuente primaria (URL, fecha de descarga, licencia)
- [ ] Definir unidad geográfica (distrito ADM2 vs provincia ADM1) según resolución del dataset
- [ ] Listar qué compuestos/familias del corpus de 107 quedan cubiertos y cuáles no
- [ ] Eliminar cualquier simulación de variabilidad (jitter, constantes inventadas)
- [ ] Aprobar métrica del mapa (conteo, volumen, índice derivado de datos reales — no `exposure_risk` heredado)

---

## 3. Arquitectura propuesta

```
data/raw/
  panama_distritos.geojson          # geoBoundaries ADM2 (ya puede existir en raw)
  inec_sociodemografico.csv        # solo columnas REALES verificadas — no jitter
  <nuevo_dataset_plaguicidas>.csv  # fuente MIDA/INEC con trazabilidad

        ↓  (notebook o script único, sin módulo hasta estabilizar)

data/processed/
  panama_distritos_merged.geojson  # geometría + atributos joinados

        ↓  prepare_dashboard.py (extensión)

outputs/dashboard/
  panama_distritos.geojson         # copia/simplificación para el visor

        ↓

proyecto analisis/viz/
  GET /panama/map                  # template analytics_map.html
  GET /api/analytics/geo           # GeoJSON + _meta.disclaimer
  GET /api/analytics/geo/summary   # agregado por provincia/distrito para Plotly choropleth
```

### Componentes a implementar (orden sugerido)

1. **`scripts/fase6/build_geodata.py`** (nombre provisional) — un solo entrypoint CLI:
   - Descarga o valida `panama_distritos.geojson` (geoBoundaries API, caché en `data/raw/`)
   - Join con el nuevo CSV de plaguicidas/uso agrícola
   - Escribe `data/processed/panama_distritos_merged.geojson` + `geodata_manifest.json` (checksum, fecha, fuentes)

2. **Extensión de `scripts/fase5/prepare_dashboard.py`** — copiar GeoJSON procesado a `outputs/dashboard/` si existe.

3. **Servicios existentes en `viz/services/dashboard/artifacts.py`** — `load_geojson()`, `geojson_to_dataframe()` ya están; solo requieren que el artefacto exista y que `_meta.disclaimer` describa la fuente real.

4. **UI** — `analytics_map.html` + `analytics_map.js` (Plotly choropleth). Actualizar disclaimer en template; quitar referencias a `make download-geodata`.

5. **Documentación** — actualizar Fase 5 (mapa activo) y Fase 7 (figura del mapa solo si hay datos reales).

### Variables del selector de mapa (propuesta)

Definir en `viz/config.py` → `MAP_VARIABLES` según columnas **reales** del GeoJSON mergeado, por ejemplo:

| Clave | Descripción (ejemplo) |
|---|---|
| `n_compuestos_registrados` | Conteo de ingredientes activos del corpus con registro en el distrito |
| `superficie_agricola_ha` | Solo si viene del INEC medido, no estimado |
| `familia_organofosforados` | Conteo o flag agregado por familia química |

No reutilizar `exposure_risk` ni pesos 0.3/0.5/0.2 del diseño anterior sin revalidación.

---

## 4. Flujo de ejecución (futuro)

```bash
cd "proyecto analisis"

# 1. Obtener dataset geográfico + join (cuando exista script)
python scripts/fase6/build_geodata.py

# 2. Regenerar artefactos del dashboard
make prepare-dashboard

# 3. Visor analytics
make viz
# → http://127.0.0.1:8001/panama/map
```

No habrá target `make download-geodata` hasta que el script esté implementado y probado.

---

## 5. Integración con el corpus de 107 compuestos

El mapa debe consumir identificadores compatibles con `compounds_features.csv`:

- Join preferido: `chembl_id` o `compound_name` ↔ columna del dataset geográfico
- Fallback: agregar por `family` si el dataset solo tiene familia química
- El explorador de compuestos (Fase 5) **no** debe implicar ubicación hasta que esta fase esté activa

Validación mínima post-implementación:

- Al menos 1 distrito con dato no nulo para ≥1 familia del corpus
- Disclaimer visible en UI citando fuente y limitaciones de cobertura
- Test en `scripts/fase5/test_dashboard.py`: `GET /api/analytics/geo` → 200 y `_meta.disclaimer` presente

---

## 6. Criterios de éxito (cuando se implemente)

| Criterio | Umbral |
|---|---|
| Trazabilidad | Cada columna del GeoJSON mapea a fuente citada en `geodata_manifest.json` |
| Cobertura | Documentar % de compuestos/familias con dato geográfico |
| Honestidad | Cero jitter; cero constantes hardcodeadas presentadas como medición |
| Dashboard | `/panama/map` renderiza choropleth; error claro si falta artefacto |
| Artículo (Fase 7) | Figura del mapa solo si pasa revisión metodológica interna; narrativa P6 (baseline) en [Fase 7](fase7_comunicacion.md) |

---

## 7. Fuera de alcance (explícito)

- Mapas en el visor GNN root (`viz/` puerto 8000) — geografía solo en analytics
- Correlacionar predicciones GNN/Tox21 con distritos sin dataset de uso real
- Reactivar el notebook monolítico `fase6_geodatos.ipynb`; la lógica vivirá en script + celdas mínimas en Fase 5 o 7 si hace falta narrativa

---

## 8. Referencias técnicas

- [geoBoundaries — Panama ADM2](https://www.geoboundaries.org/)
- Corpus químico: `data/processed/compounds_features.csv` (107 compuestos)
- Raw geo existente (referencia): `data/raw/panama_distritos.geojson`, `data/raw/inec_sociodemografico.csv`
- Implementación UI ya preparada: `viz/routes/analytics.py` (endpoints geo), `viz/templates/analytics_map.html`

---

*Fase anterior:* [Fase 5 — Dashboard interactivo](fase5_dashboard.md)  
*Siguiente fase:* [Fase 7 — Comunicación de resultados](fase7_comunicacion.md)
