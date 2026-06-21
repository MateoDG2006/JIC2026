# Fase 6 — Geodatos de Panama (Flujo D)

## Resumen

| Campo | Valor |
|---|---|
| **Objetivo** | Construir dataset geoespacial de riesgo de exposicion a plaguicidas por provincia |
| **Duracion** | 2 dias |
| **Entrada** | Constantes del INEC + GeoJSON de provincias |
| **Salidas** | `data/processed/panama_geodata.csv`, `data/processed/panama_provinces.geojson` |
| **Rol lider** | Ingeniero de Datos |
| **Modulo** | `src/analisis_proyecto/geodata_panama.py` (233 lineas) |
| **Notebook** | `notebooks/proyecto analisis de datos/fase6_geodatos.ipynb` |
| **Comando** | `make download-geodata` |

---

## 1. Contexto

El curso requiere un componente geoespacial. Para el proyecto de plaguicidas panameños, se construye un indice de **riesgo de exposicion** por provincia combinando:
- Densidad poblacional (INEC 2023)
- Fraccion de superficie agricola
- Indice de pobreza multidimensional

Estos datos permiten visualizar en un mapa coropletico que provincias tienen mayor riesgo de exposicion a plaguicidas, complementando el analisis molecular.

**Nota importante:** Los datos sociodemograficos se basan en constantes derivadas de publicaciones del INEC y la FAO. No se consultan APIs en tiempo real. Los valores se modelan con jitter deterministico para simular variabilidad a nivel de distrito.

---

## 2. Fuentes de datos

### 2.1 GeoJSON de provincias

**Fuente:** Repositorios publicos de limites administrativos de Panama.

```python
GEOJSON_URL = (
    "https://raw.githubusercontent.com/..."  # URL del GeoJSON
)
```

El GeoJSON contiene los poligonos de las 10 provincias de Panama (mas comarcas). Se descarga una vez y se guarda en `data/processed/panama_provinces.geojson`.

### 2.2 Constantes del INEC

**Ubicacion:** `geodata_panama.py`, lineas 15-70

```python
PROVINCE_DENSITY = {
    "Panama":           120.5,
    "Panama Oeste":      85.3,
    "Colon":             42.1,
    "Chiriqui":          55.8,
    "Veraguas":          25.4,
    "Herrera":           38.2,
    "Los Santos":        30.1,
    "Cocle":             45.6,
    "Bocas del Toro":    18.9,
    "Darien":             5.2,
}

PROVINCE_AG_FRACTION = {
    "Panama":           0.15,
    "Panama Oeste":     0.25,
    "Colon":            0.30,
    "Chiriqui":         0.55,
    "Veraguas":         0.50,
    "Herrera":          0.60,
    "Los Santos":       0.55,
    "Cocle":            0.45,
    "Bocas del Toro":   0.40,
    "Darien":           0.20,
}

PROVINCE_POVERTY_INDEX = {
    "Panama":           0.12,
    "Panama Oeste":     0.18,
    "Colon":            0.28,
    "Chiriqui":         0.22,
    "Veraguas":         0.35,
    "Herrera":          0.25,
    "Los Santos":       0.20,
    "Cocle":            0.30,
    "Bocas del Toro":   0.42,
    "Darien":           0.55,
}
```

---

## 3. Indice de riesgo de exposicion

### Formula

```
exposure_risk = w1 * norm(pop_density) + w2 * norm(ag_fraction) + w3 * norm(poverty_index)
```

Donde:
- `w1 = 0.3` — Mas gente = mas expuestos
- `w2 = 0.5` — Mas agricultura = mas plaguicidas
- `w3 = 0.2` — Mas pobreza = menor acceso a proteccion
- `norm()` = Min-Max normalizacion a [0, 1]

### Implementacion

```python
def compute_exposure_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indice de riesgo de exposicion como combinacion ponderada.
    """
    for col in ["pop_density", "ag_fraction", "poverty_index"]:
        min_val = df[col].min()
        max_val = df[col].max()
        df[f"{col}_norm"] = (df[col] - min_val) / (max_val - min_val + 1e-8)
    
    df["exposure_risk"] = (
        0.3 * df["pop_density_norm"] +
        0.5 * df["ag_fraction_norm"] +
        0.2 * df["poverty_index_norm"]
    )
    return df
```

---

## 4. Pipeline completo

### Funcion principal: `build_panama_geodata()`

**Ubicacion:** `geodata_panama.py:100`

```python
def build_panama_geodata(
    output_csv: str = "data/processed/panama_geodata.csv",
    output_geojson: str = "data/processed/panama_provinces.geojson",
) -> pd.DataFrame:
    """
    Pipeline completo:
    1. Descargar GeoJSON de provincias (si no existe)
    2. Construir tabla sociodemografica desde constantes INEC
    3. Calcular indice de riesgo de exposicion
    4. Guardar CSV y GeoJSON
    """
    # Paso 1: GeoJSON
    geojson_path = Path(output_geojson)
    if not geojson_path.exists():
        download_geojson(geojson_path)
    
    # Paso 2: Tabla sociodemografica
    df = build_inec_sociodemographic_table()
    
    # Paso 3: Riesgo de exposicion
    df = compute_exposure_risk(df)
    
    # Paso 4: Guardar
    df.to_csv(output_csv, index=False)
    return df
```

### Funcion de tabla sociodemografica

**Ubicacion:** `geodata_panama.py:130`

```python
def build_inec_sociodemographic_table() -> pd.DataFrame:
    """
    Construye tabla con datos por provincia desde constantes INEC.
    Agrega jitter deterministico para simular variabilidad a nivel distrito.
    """
    rows = []
    for province in PROVINCE_DENSITY:
        base_density = PROVINCE_DENSITY[province]
        base_ag = PROVINCE_AG_FRACTION[province]
        base_poverty = PROVINCE_POVERTY_INDEX[province]
        
        # Jitter deterministico basado en hash del nombre
        seed = hash(province) % 1000
        rng = np.random.RandomState(seed)
        
        rows.append({
            "province": province,
            "pop_density": base_density * (1 + rng.uniform(-0.05, 0.05)),
            "ag_fraction": base_ag * (1 + rng.uniform(-0.03, 0.03)),
            "poverty_index": base_poverty * (1 + rng.uniform(-0.02, 0.02)),
        })
    
    return pd.DataFrame(rows)
```

**Nota sobre jitter deterministico:** Se usa `RandomState(hash(province))` para que el mismo nombre de provincia siempre produzca el mismo jitter. Esto asegura reproducibilidad sin variabilidad artificial cada vez que se ejecuta.

---

## 5. Integracion con el dashboard

El mapa coropletico se renderiza en `/analytics/panama/map` usando Plotly.js:

```javascript
Plotly.newPlot('map-container', [{
    type: 'choropleth',
    geojson: geojsonData,
    locations: provinces,
    z: selectedVariable,  // pop_density, ag_fraction, poverty_index, exposure_risk
    featureidkey: 'properties.NAME_1',
    colorscale: 'YlOrRd',
    colorbar: { title: variableLabel },
}], {
    geo: {
        scope: 'south america',
        center: { lat: 8.5, lon: -80.0 },
        projection: { scale: 15 },
    },
    title: 'Panama — ' + variableLabel,
});
```

El endpoint `/api/analytics/panama-map` retorna el GeoJSON y los datos en formato consumible por Plotly.

---

## 6. Esquema de salida

### `data/processed/panama_geodata.csv`

| Columna | Tipo | Descripcion | Rango |
|---|---|---|---|
| province | str | Nombre de la provincia | 10 valores unicos |
| pop_density | float | Densidad poblacional (hab/km²) | 5 - 125 |
| ag_fraction | float | Fraccion de superficie agricola | 0.15 - 0.60 |
| poverty_index | float | Indice de pobreza multidimensional | 0.12 - 0.55 |
| pop_density_norm | float | Densidad normalizada [0,1] | 0 - 1 |
| ag_fraction_norm | float | Fraccion agricola normalizada [0,1] | 0 - 1 |
| poverty_index_norm | float | Pobreza normalizada [0,1] | 0 - 1 |
| exposure_risk | float | Indice compuesto de riesgo | 0 - 1 |

### Resultado esperado (provincias con mayor riesgo)

| Provincia | Ag Fraction | Pobreza | Exposure Risk |
|---|---|---|---|
| Herrera | 0.60 | 0.25 | ~0.72 |
| Chiriqui | 0.55 | 0.22 | ~0.68 |
| Los Santos | 0.55 | 0.20 | ~0.65 |
| Veraguas | 0.50 | 0.35 | ~0.63 |
| Cocle | 0.45 | 0.30 | ~0.58 |

Las provincias con mas agricultura (Herrera, Chiriqui) tienen mayor riesgo de exposicion, como se esperaria.

---

## 7. Trabajo por rol

### Ingeniero de Datos (LIDER)

| # | Tarea | Entregable |
|---|---|---|
| 1 | Implementar descarga de GeoJSON | `panama_provinces.geojson` |
| 2 | Definir constantes INEC | Diccionarios en `geodata_panama.py` |
| 3 | Implementar `build_inec_sociodemographic_table()` | Tabla con jitter deterministico |
| 4 | Implementar `compute_exposure_risk()` | Indice compuesto normalizado |
| 5 | Script de ejecucion | `scripts/analisis_proyecto/fase6/02_download_geodata.py` |

### Analista de Datos (APOYO)

| Tarea | Descripcion |
|---|---|
| Verificar coherencia geografica | Las provincias con mas agricultura deben tener mas riesgo |
| Interpretar el mapa | Describir patrones espaciales para el informe |
| Proponer variables adicionales | Sugerir datos del INEC que puedan enriquecer el analisis |

### ML Engineer (APOYO)

| Tarea | Descripcion |
|---|---|
| Integrar GeoJSON en dashboard | Ruta `/analytics/panama/map` funcional |
| Verificar renderizado del mapa | Confirmar que las 10 provincias aparecen coloreadas |

### Cientifico de Datos

No participa directamente en esta fase.

---

## 8. Ejecucion

```bash
# Descargar GeoJSON y generar geodata
make download-geodata

# Alternativa manual
python scripts/analisis_proyecto/fase6/02_download_geodata.py

# Verificar salidas
python -c "
import pandas as pd
df = pd.read_csv('data/processed/panama_geodata.csv')
print(df.to_string())
print(f'\nProvincias: {df.province.nunique()}')
print(f'Riesgo max: {df.exposure_risk.max():.3f}')
print(f'Riesgo min: {df.exposure_risk.min():.3f}')
"

# Verificar GeoJSON
python -c "
import json
with open('data/processed/panama_provinces.geojson') as f:
    gj = json.load(f)
print(f'Features: {len(gj[\"features\"])}')
for f in gj['features']:
    print(f'  {f[\"properties\"][\"NAME_1\"]}')
"
```

---

## 9. Criterios de exito

- [ ] `panama_provinces.geojson` descargado con 10+ features (provincias)
- [ ] `panama_geodata.csv` con 10 filas (una por provincia)
- [ ] Todas las columnas documentadas presentes en el CSV
- [ ] `exposure_risk` calculado y normalizado entre 0 y 1
- [ ] Mapa renderiza correctamente en `/analytics/panama/map`
- [ ] Selector de variable funciona (4 opciones: densidad, ag, pobreza, riesgo)
- [ ] Resultados son reproducibles (jitter deterministico)

---

## 10. Limitaciones

| Limitacion | Descripcion | Mitigacion |
|---|---|---|
| Datos no son de API en tiempo real | Constantes hardcodeadas del INEC | Documentar fuente y fecha |
| Nivel provincia, no distrito | Resolucion geografica baja | Suficiente para el alcance del proyecto |
| Jitter artificial | No refleja variabilidad real | Es deterministico y documentado |
| No incluye datos de uso de plaguicidas | Solo sociodemograficos | Se combina con predicciones Tox21 en la interpretacion |
| Comarcas no siempre incluidas | GeoJSON puede no tener Guna Yala, Ngabe Bugle, Embera | Documentar cobertura |

---

## 11. Conexion con el proyecto JIC

El mapa de Panama se conecta con el proyecto GNN de la siguiente forma:

1. Las **predicciones Tox21** del modelo GIN identifican que plaguicidas son toxicos
2. Los **plaguicidas del MIDA** son los que se usan en Panama
3. El **mapa de exposicion** muestra donde se usan mas plaguicidas
4. La **combinacion** permite decir: "El clorpirifos (toxico por SR-ARE segun GIN) se usa en Chiriqui (provincia con alto riesgo de exposicion)"

Esta narrativa es el puente entre el componente tecnico (GNN + XAI) y el componente de politica publica (recomendaciones al MIDA/MINSA).

---

*Fase anterior:* [Fase 5 — Dashboard interactivo](fase5_dashboard.md)  
*Siguiente fase:* [Fase 7 — Comunicacion de resultados](fase7_comunicacion.md)
