# Fase 6 — Geodatos de Panama (Flujo D)

> ⚠️ **FASE PARQUEADA** — retirada del pipeline activo, del artículo y del dashboard hasta conseguir
> datos que vinculen el análisis con la geografía.

## Resumen

| Campo | Valor |
|---|---|
| **Estado** | PARQUEADA — no se ejecuta ni se reporta en la versión actual del proyecto |
| **Objetivo original** | Construir dataset geoespacial de riesgo de exposicion a plaguicidas por provincia |
| **Entrada original** | Constantes del INEC + GeoJSON de provincias |
| **Salidas (no generadas actualmente)** | `data/processed/panama_geodata.csv`, `data/processed/panama_provinces.geojson` |
| **Rol lider** | Ingeniero de Datos |
| **Modulo (referencia, no invocado)** | `src/analisis_proyecto/geodata_panama.py` (233 lineas) |
| **Notebook** | `notebooks/proyecto analisis de datos/fase6_geodatos.ipynb` (no forma parte del pipeline activo) |
| **Comando** | `make download-geodata` (disponible pero no se ejecuta como parte del flujo reportado) |

---

## 1. Contexto y motivo del parqueo

El curso pedía un componente geoespacial, y en su momento se construyó un índice de **riesgo de
exposición** por provincia combinando densidad poblacional, fracción de superficie agrícola e índice
de pobreza — todos derivados de **constantes hardcodeadas del INEC/FAO** más un **jitter
determinístico** (`RandomState(hash(province))`) para simular variabilidad a nivel de distrito.

Al revisar el proyecto en conjunto con el reencuadre de las Fases 1-5 (ver
`docs/analisis_proyecto/fases/rediseno_brief.md`), este componente no resiste el mismo estándar de
honestidad metodológica que se aplicó al resto del análisis:

- **No hay ningún vínculo real entre los 107 compuestos analizados y la geografía panameña.** El
  índice de riesgo se calcula a partir de constantes sociodemográficas genéricas por provincia; no
  incorpora ningún dato de qué plaguicidas se usan, en qué cantidad o en qué distrito.
- El **jitter determinístico** que "simula variabilidad a nivel de distrito" no representa ninguna
  medición real — es ruido reproducible aplicado a una constante, no una estimación.
- Combinar esto con las predicciones de bioactividad/toxicidad (Fases 3-4 o el GNN de la JIC) daría la
  falsa impresión de un análisis espacial de exposición real, cuando en realidad no existe trazabilidad
  de qué compuesto se usa dónde.

Por estas razones, **la Fase 6 se retira del pipeline activo, del artículo (Fase 7) y del dashboard
(Fase 5)** hasta contar con un dataset real que vincule compuestos o familias químicas con ubicación
geográfica en Panamá (ver sección 4, "Requisitos para reactivar").

El código y los diagramas de esta fase se conservan **como referencia** para una eventual
reactivación, pero no se ejecutan ni se citan como resultado del proyecto actual.

---

## 2. Qué existe hoy (referencia, no ejecutado)

El módulo `src/analisis_proyecto/geodata_panama.py` implementa un pipeline autocontenido que:

1. Descarga un **GeoJSON** con los polígonos de las 10 provincias de Panamá (`download_geojson`) y lo
   guarda en `data/processed/panama_provinces.geojson`.
2. Construye una tabla sociodemográfica por provincia a partir de tres diccionarios de constantes
   (`PROVINCE_DENSITY`, `PROVINCE_AG_FRACTION`, `PROVINCE_POVERTY_INDEX`, líneas 15-70) vía
   `build_inec_sociodemographic_table()`, agregando jitter determinístico por provincia.
3. Calcula un índice compuesto `exposure_risk` con `compute_exposure_risk()`, como combinación lineal
   ponderada y normalizada (Min-Max) de densidad poblacional (w=0.3), fracción agrícola (w=0.5) e
   índice de pobreza (w=0.2).
4. Orquesta los tres pasos en `build_panama_geodata()` (línea 100), que guarda
   `panama_geodata.csv` y `panama_provinces.geojson`.

En el dashboard (Fase 5), este dataset se consumía en la ruta `/analytics/panama/map` mediante un
choropleth de Plotly.js (`/api/analytics/panama-map`), con selector entre `pop_density`,
`ag_fraction`, `poverty_index` y `exposure_risk`.

Esta descripción se mantiene únicamente como **mapa de referencia del código existente**; ninguno de
estos artefactos se genera, valida ni cita en la versión actual de los entregables del curso ni del
artículo JIC.

---

## 3. Trabajo por rol (histórico, no aplica en el ciclo actual)

Esta fase no tiene asignación de trabajo activa. Cuando participó en el proyecto, el rol líder era
Ingeniero de Datos (implementación del pipeline y las constantes), con apoyo de Analista de Datos
(interpretación del mapa) y ML Engineer (integración en el dashboard). El Científico de Datos no
participaba. Esta división se documenta solo por trazabilidad histórica; no debe usarse para planificar
trabajo mientras la fase esté parqueada.

---

## 4. Requisitos para reactivar

La fase se retoma únicamente si se consigue **al menos uno** de los siguientes datasets, con
trazabilidad a fuente primaria:

- [ ] **Registro de plaguicidas por distrito del MIDA** — qué ingredientes activos/productos están
  registrados o se distribuyen por distrito o provincia, con fecha y fuente verificable.
- [ ] **Datos de uso agrícola por distrito del INEC / Censo Agropecuario** — superficie cultivada por
  rubro y distrito, que permita inferir exposición potencial a familias de plaguicidas asociadas a
  esos cultivos (p. ej. banano → organofosforados/ditiocarbamatos).
- [ ] **Cualquier fuente que vincule explícitamente un compuesto o familia química del corpus de 107
  plaguicidas con una ubicación geográfica en Panamá** (no solo variables sociodemográficas genéricas).

Además, antes de reintegrar la fase al pipeline:

- [ ] Definir la unidad geográfica real de análisis (distrito vs. provincia) según la resolución del
  dataset conseguido — no asumir provincia solo porque el GeoJSON existente es a ese nivel.
- [ ] Eliminar el jitter determinístico o cualquier simulación de variabilidad; usar valores medidos.
- [ ] Documentar explícitamente qué compuestos/familias del corpus de 107 quedan cubiertos por el
  nuevo dataset y cuáles no, para evitar extrapolar a compuestos sin evidencia geográfica.
- [ ] Revisar con el equipo si el índice de riesgo (`exposure_risk`) sigue siendo la métrica adecuada
  o si el nuevo dataset permite un indicador más directo (p. ej. volumen reportado de uso).

---

## 5. Troubleshooting

No aplica mientras la fase esté parqueada. Si se reactiva, retomar el troubleshooting relevante del
módulo original (`geodata_panama.py`): validar cobertura de comarcas en el GeoJSON (Guna Yala, Ngäbe
Buglé, Emberá pueden faltar) y verificar que las claves de los diccionarios de constantes coincidan
exactamente con `featureidkey` del GeoJSON antes de recalcular `exposure_risk`.

---

*Fase anterior:* [Fase 5 — Dashboard interactivo](fase5_dashboard.md)
*Siguiente fase:* [Fase 7 — Comunicacion de resultados](fase7_comunicacion.md)
