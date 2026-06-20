# Plan de Expansión: Integración de ChEMBL para Proyecto Final de Análisis de Datos

## 1. Diagnóstico: Repositorio Actual vs Requisitos del Curso

### Estado actual del repositorio

El repositorio JIC2026 tiene un pipeline completo de GNN + XAI para predicción de toxicidad:

- **5 fases completas:** datos, baselines, GNN-GIN, XAI, aplicación Panamá
- **Modelo entrenado:** GIN con AUC ~0.78 sobre Tox21 (12 tareas)
- **235 plaguicidas panameños** perfilados con predicciones + explicaciones XAI
- **Dashboard FastAPI** con visualización 3D de moléculas
- **179 explicaciones XAI** generadas (GNNExplainer + Grad-CAM)

### Requisitos del curso — estado de implementación (Jun 2026)

| Requisito | Estado |
|-----------|--------|
| Medidas de tendencia central, distribuciones, Missingno, UpSetPlot | ✅ Flujo B |
| Imputación (>250 NaN → eliminar) | ✅ Flujo B |
| Correlación Pearson + Spearman | ✅ Flujo B |
| Clasificación RF + SVM, Accuracy, Confusion Matrix | ✅ Flujo B |
| Regresión SVR + RF, R² train/test | ✅ Flujo B |
| Dashboard Dash-Plotly (≥4 gráficas, ≥2 controladores) | ✅ Flujo C — `dashboard/` |
| Predictor de regresión interactivo | ✅ Flujo C — Tab Modelos |
| Mapa interactivo Panamá (GeoPandas + INEC) | ✅ Flujo D — integrado en Flujo C Tab Mapa |
| Despliegue web (Render) | ✅ Config lista — `dashboard/render.yaml` |
| Artículo IEEE (max 7 páginas) | ⏳ Flujo E pendiente |
| Video explicativo (max 7 min) | ⏳ Pendiente |

### Requisitos del curso no cubiertos (detalle histórico)

El proyecto final de "Análisis de Datos y Toma de Decisiones" requiere un enfoque de **ciencia de datos clásica** que el repo actual no cumple:

| Requisito | Estado | Solución con ChEMBL |
|-----------|--------|---------------------|
| Medidas de tendencia central por columna | Faltante | ChEMBL tiene columnas numéricas ricas |
| Análisis de distribuciones | Parcial | ChEMBL: IC50, MW, LogP, etc. |
| UpSetPlot + Missingno para valores faltantes | Faltante | ChEMBL tiene NaN naturales en bioactividad |
| Imputación de datos (>250 NaN → eliminar) | Faltante | ChEMBL: muchas columnas con datos faltantes |
| Correlación (mín. 2 métodos) | Faltante | Pearson + Spearman sobre propiedades moleculares |
| Clasificación: 1 var categórica, 2 algoritmos | Parcial | Clasificar `activity_class` con SVM + KNN |
| Regresión: 1 var continua, 2 algoritmos | Faltante | Predecir `pchembl_value` con SVR + RF Regressor |
| Accuracy + Confusion Matrix | Parcial | Agregar métricas estándar |
| R² train/test para regresión | Faltante | Agregar para modelos de regresión |
| Dashboard Dash-Plotly | Faltante (es FastAPI) | Nuevo dashboard en Dash |
| Mín. 4 gráficas + 2 controladores | Faltante | Incluir en dashboard Dash |
| Predictor de regresión interactivo | Faltante | Input → predicción pChEMBL |
| Mapa interactivo Panamá (distritos, INEC) | Faltante | GeoPandas + datos sociodemográficos |
| Despliegue web público | Faltante | Render / Railway |
| Artículo IEEE (max 7 páginas) | Faltante | Redactar con plantilla IEEE |
| Video explicativo (max 7 min) | Faltante | Grabar demo del dashboard |

---

## 2. Estrategia: Por qué ChEMBL

**ChEMBL** (https://www.ebi.ac.uk/chembl/) es la base de datos más grande de bioactividad de fármacos y compuestos químicos. Es ideal porque:

1. **Coherencia temática:** Bioactividad de compuestos químicos → misma línea que Tox21
2. **Datos tabulares ricos:** IC50, EC50, Ki, pChEMBL value, MW, LogP, PSA, HBD, HBA, etc.
3. **Variables categóricas:** tipo de actividad, tipo de diana, organismo, fase clínica
4. **Variables continuas:** pChEMBL value (potencia normalizada), propiedades moleculares
5. **Datos faltantes naturales:** no todos los compuestos tienen todas las mediciones
6. **Conexión con Panamá:** filtrando por targets relevantes para plaguicidas agrícolas
7. **Fuente verificable y citada:** EMBL-EBI, publicación en Nucleic Acids Research

### Dataset a construir

Descargar de ChEMBL todos los registros de bioactividad para los **20 ingredientes activos del MIDA** que ya tenemos en el corpus panameño. Esto genera un dataset tabular con:

- **~5,000-15,000 registros** de bioactividad
- **~25-30 columnas** entre propiedades moleculares y datos de ensayo
- **Variable categórica objetivo:** `activity_class` (Active/Inactive)
- **Variable continua objetivo:** `pchembl_value` (potencia logarítmica normalizada)

---

## 3. Flujos de Trabajo Recomendados

### Flujo A: Descarga y Preparación de Datos ChEMBL

```
PubChem CIDs (corpus panameño)
        ↓
ChEMBL API: buscar por nombre/SMILES
        ↓
Descargar bioactividad (IC50, EC50, Ki)
        ↓
Enriquecer con propiedades moleculares
  (MW, LogP, PSA, HBD, HBA, nRings, TPSA, etc.)
        ↓
Unificar en DataFrame tabular
        ↓
data/raw/chembl_panama_bioactivity.csv
```

**Script:** `scripts/analisis_proyecto/01_download_chembl.py`

```python
# Pseudocódigo del flujo
from chembl_webresource_client.new_client import new_client

PANAMA_PESTICIDES = [
    'Chlorpyrifos', 'Malathion', 'Atrazine', 'Glyphosate',
    'Cypermethrin', 'Paraquat', 'Tebuconazole', ...
]

molecule = new_client.molecule
activity = new_client.activity

for name in PANAMA_PESTICIDES:
    # Buscar molécula en ChEMBL
    results = molecule.filter(pref_name__iexact=name)
    chembl_id = results[0]['molecule_chembl_id']

    # Descargar bioactividad
    acts = activity.filter(
        molecule_chembl_id=chembl_id,
        standard_type__in=['IC50', 'EC50', 'Ki'],
        standard_units='nM'
    )

    # Enriquecer con propiedades moleculares
    props = molecule.get(chembl_id)
    # MW, ALogP, PSA, HBA, HBD, nRings, etc.
```

**Columnas resultantes del dataset:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `compound_name` | str | Nombre del plaguicida |
| `chembl_id` | str | ID ChEMBL del compuesto |
| `smiles` | str | SMILES canónico |
| `target_name` | str | Diana biológica del ensayo |
| `target_type` | cat | Tipo de diana (SINGLE PROTEIN, etc.) |
| `organism` | cat | Organismo del ensayo |
| `standard_type` | cat | Tipo de medición (IC50, EC50, Ki) |
| `standard_value` | float | Valor de bioactividad (nM) |
| `pchembl_value` | float | **Variable continua objetivo** (-log10 del valor) |
| `activity_class` | cat | **Variable categórica objetivo** (Active/Inactive) |
| `mw_freebase` | float | Peso molecular |
| `alogp` | float | LogP calculado |
| `psa` | float | Área de superficie polar |
| `hba` | int | Aceptores de puentes de hidrógeno |
| `hbd` | int | Donadores de puentes de hidrógeno |
| `num_ro5_violations` | int | Violaciones de la regla de Lipinski |
| `aromatic_rings` | int | Anillos aromáticos |
| `heavy_atoms` | int | Átomos pesados |
| `rtb` | int | Enlaces rotables |
| `molecular_species` | cat | Especie molecular (ACID, BASE, NEUTRAL, ZWITTERION) |
| `cx_logp` | float | LogP experimental |
| `cx_logd` | float | LogD a pH 7.4 |
| `assay_type` | cat | Tipo de ensayo (B=Binding, F=Functional, A=ADMET) |
| `bao_label` | cat | Formato del ensayo (cell-based, biochemical, etc.) |
| `family` | cat | Familia química (organophosphate, triazine, etc.) |
| `data_validity_comment` | str | Comentario de validez (tiene NaN) |

---

### Flujo B: Notebook de Procedimientos (Entregable 1)

```
chembl_panama_bioactivity.csv
        ↓
┌─── SECCIÓN 1: Análisis Preliminar ───────────────────────┐
│  - df.describe() por columnas numéricas                    │
│  - Media, mediana, moda, desviación estándar              │
│  - Distribuciones: histogramas de pchembl_value, MW, LogP │
│  - Boxplots por familia química                           │
│  - Conteo de categorías: activity_class, assay_type       │
└───────────────────────────────────────────────────────────┘
        ↓
┌─── SECCIÓN 2: Valores Faltantes ──────────────────────────┐
│  - missingno.matrix(df)                                    │
│  - missingno.bar(df)                                       │
│  - missingno.heatmap(df)                                   │
│  - UpSetPlot de patrones de NaN                           │
│  - Eliminar columnas con >250 NaN                         │
│  - Imputar resto: KNN Imputer / mediana por grupo         │
└───────────────────────────────────────────────────────────┘
        ↓
┌─── SECCIÓN 3: Correlación ────────────────────────────────┐
│  - Pearson: pchembl_value vs MW, LogP, PSA, HBA, HBD     │
│  - Spearman: ranking de correlaciones no lineales          │
│  - Heatmap de correlación completo                        │
│  - Scatter matrix de variables top                        │
└───────────────────────────────────────────────────────────┘
        ↓
┌─── SECCIÓN 4: Clasificación ──────────────────────────────┐
│  Variable objetivo: activity_class (Active/Inactive)       │
│  Features: MW, LogP, PSA, HBA, HBD, nRings, etc.         │
│                                                            │
│  Algoritmo 1: Random Forest Classifier                     │
│  Algoritmo 2: SVM (SVC con kernel RBF)                    │
│                                                            │
│  Métricas: Accuracy train/test, Confusion Matrix,         │
│            Classification Report, ROC Curve                │
└───────────────────────────────────────────────────────────┘
        ↓
┌─── SECCIÓN 5: Regresión ─────────────────────────────────┐
│  Variable objetivo: pchembl_value (potencia)              │
│  Features: MW, LogP, PSA, HBA, HBD, nRings, etc.         │
│                                                            │
│  Algoritmo 1: SVR (Support Vector Regression)             │
│  Algoritmo 2: Random Forest Regressor                     │
│                                                            │
│  Métricas: R² train/test, MAE, RMSE,                     │
│            Gráfica predicho vs real                        │
└───────────────────────────────────────────────────────────┘
```

**Notebook:** `notebooks/08_chembl_analisis_datos.ipynb`

---

### Flujo C: Dashboard Dash-Plotly (Entregable 2)

```
┌─────────────────────────────────────────────────────────────┐
│                    DASHBOARD DASH-PLOTLY                      │
│                                                              │
│  TAB 1: Exploración del Dataset                              │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Histograma   │  │ Boxplot por  │  ← Dropdown: variable   │
│  │ pChEMBL      │  │ familia      │  ← Dropdown: familia    │
│  └──────────────┘  └──────────────┘                         │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Heatmap      │  │ Scatter      │                         │
│  │ correlación  │  │ MW vs LogP   │  ← Slider: rango MW    │
│  └──────────────┘  └──────────────┘                         │
│                                                              │
│  TAB 2: Modelos Predictivos                                  │
│  ┌─────────────────────────────────┐                        │
│  │ PREDICTOR INTERACTIVO           │                        │
│  │ Input: MW, LogP, PSA, HBA, HBD │                        │
│  │ Output: pChEMBL predicho        │                        │
│  │ (usando mejor modelo regresión) │                        │
│  └─────────────────────────────────┘                        │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Conf Matrix  │  │ ROC Curves   │                         │
│  │ Clasificación│  │ RF vs SVM    │                         │
│  └──────────────┘  └──────────────┘                         │
│                                                              │
│  TAB 3: Perfil de Toxicidad (datos GNN existentes)           │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Heatmap Tox  │  │ XAI Molecule │                         │
│  │ 12 vías×20   │  │ Viewer       │                         │
│  └──────────────┘  └──────────────┘                         │
│                                                              │
│  TAB 4: Mapa Interactivo de Panamá                           │
│  ┌─────────────────────────────────┐                        │
│  │ Mapa distritos (GeoPandas)      │                        │
│  │ Color: variable sociodemográfica│  ← Dropdown: variable  │
│  │ Hover: datos del distrito       │                        │
│  └─────────────────────────────────┘                        │
│  ┌─────────────────────────────────┐                        │
│  │ Gráfica resumen del mapa       │                        │
│  │ (barras por provincia)          │                        │
│  └─────────────────────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Estructura de archivos del dashboard:**

```
dashboard/
├── app.py                    # Aplicación principal Dash
├── assets/
│   └── style.css             # Estilos personalizados
├── pages/
│   ├── exploracion.py        # Tab 1: EDA interactivo
│   ├── modelos.py            # Tab 2: Modelos + predictor
│   ├── toxicidad.py          # Tab 3: Perfil GNN (datos existentes)
│   └── mapa_panama.py        # Tab 4: Mapa GeoPandas
├── data/
│   ├── chembl_clean.csv      # Dataset limpio
│   ├── models/
│   │   ├── rf_classifier.pkl # RF entrenado
│   │   ├── svm_classifier.pkl
│   │   ├── svr_regressor.pkl
│   │   └── rf_regressor.pkl
│   ├── panama_distritos.geojson
│   └── inec_sociodemografico.csv
├── Procfile                  # Para despliegue
├── requirements.txt
└── render.yaml               # Config Render
```

---

### Flujo D: Mapa Interactivo de Panamá

```
geoboundaries.org → Descargar shapefile distritos Panamá
        ↓
INEC MAPI (inec.gob.pa/mapi/) → Descargar variable sociodemográfica
  Opciones recomendadas:
    - Población total por distrito
    - Superficie agrícola por distrito
    - Índice de pobreza multidimensional
        ↓
GeoPandas: merge shapefile + datos INEC
        ↓
Plotly Choropleth / Folium → mapa interactivo
        ↓
Integrar en dashboard Dash (Tab 4)
```

**Conexión temática con el proyecto:** El mapa puede mostrar datos de superficie agrícola por distrito, vinculándolo con la pregunta: "¿Dónde hay mayor exposición potencial a plaguicidas en Panamá?"

---

### Flujo E: Artículo IEEE (Entregable 3)

```
Estructura del artículo (max 7 páginas):

I.   INTRODUCCIÓN (0.75 pág)
     Pregunta: "¿Pueden los modelos computacionales basados en
     bioactividad molecular predecir el perfil de toxicidad de
     plaguicidas agrícolas usados en Panamá?"

II.  MATERIALES Y MÉTODOS (1.5 pág)
     A. Datasets: ChEMBL (bioactividad), Tox21 (toxicidad), INEC (geodatos)
     B. Herramientas: Python, scikit-learn, Dash-Plotly, GeoPandas, PyG
     C. Modelos: RF, SVM, SVR, RF Regressor + GNN-GIN (avanzado)
     D. Servidor: Render/Railway para dashboard

III. RESULTADOS (2.5 pág)
     A. EDA: distribuciones clave, correlaciones
     B. Clasificación: Accuracy, Confusion Matrix (RF vs SVM)
     C. Regresión: R², scatter predicho vs real (SVR vs RF)
     D. Dashboard: screenshots + enlace público
     E. Mapa: visualización distritos + resumen

IV.  CONCLUSIONES (1 pág)
     - Conclusión Ingeniero de Datos
     - Conclusión Analista de Datos
     - Conclusión Científico de Datos
     - Conclusión Ingeniero de ML

V.   REFERENCIAS (0.75 pág)
     Formato IEEE: ChEMBL, Tox21, RDKit, scikit-learn, GeoPandas, INEC
```

---

## 4. Distribución por Roles

| Rol | Responsable de | Entregables clave |
|-----|----------------|-------------------|
| **Estudiante 1: Ingeniero de Datos** | Descarga ChEMBL, limpieza, imputación, pipeline de datos, descarga geodatos INEC | Dataset limpio, pipeline reproducible |
| **Estudiante 2: Analista de Datos** | EDA completo, distribuciones, correlaciones, UpSetPlot, Missingno, visualizaciones | Secciones 1-3 del notebook |
| **Estudiante 3: Científico de Datos** | Modelos de clasificación y regresión, métricas, comparación de algoritmos | Secciones 4-5 del notebook, modelos .pkl |
| **Estudiante 4: Ingeniero de ML** | Dashboard Dash-Plotly, mapa GeoPandas, despliegue web, video | Dashboard desplegado, video |

---

## 5. Pregunta de Investigación Propuesta

> **"¿Es posible predecir la potencia biológica (pChEMBL value) y la clase de actividad de plaguicidas agrícolas usados en Panamá a partir de sus propiedades moleculares, y cuál es la distribución geográfica de la exposición potencial a estos compuestos?"**

Esta pregunta cubre:
- **Componente de regresión:** predecir pChEMBL value (continua)
- **Componente de clasificación:** predecir activity_class (categórica)
- **Componente geográfico:** mapa de Panamá con datos INEC
- **Componente avanzado (JIC):** predicción de toxicidad multitarea con GNN + XAI

---

## 6. Cronograma de Expansión

```
Semana 1 (Jun 15-21):
  ├── Descargar datos ChEMBL para plaguicidas panameños
  ├── Descargar geodatos de geoboundaries.org
  ├── Descargar datos INEC (MAPI)
  └── Comenzar notebook EDA

Semana 2 (Jun 22-28):
  ├── Completar notebook: EDA + valores faltantes + correlación
  ├── Entrenar modelos clasificación (RF + SVM)
  ├── Entrenar modelos regresión (SVR + RF Regressor)
  └── Comenzar dashboard Dash-Plotly

Semana 3 (Jun 29 - Jul 5):
  ├── Completar dashboard (4 tabs)
  ├── Integrar mapa GeoPandas
  ├── Desplegar en Render/Railway
  └── Comenzar artículo IEEE

Semana 4 (Jul 6-10):
  ├── Finalizar artículo IEEE
  ├── Grabar video explicativo
  ├── Revisión final de todos los entregables
  └── Entrega en Moodle
```

---

## 7. Dependencias a Instalar

```bash
# ChEMBL client
pip install chembl_webresource_client

# Dashboard
pip install dash dash-bootstrap-components

# Mapa interactivo
pip install geopandas folium

# Valores faltantes
pip install missingno upsetplot

# Ya instalados en el entorno actual
# scikit-learn, pandas, matplotlib, seaborn, plotly
```

---

## 8. Archivos Nuevos a Crear

```
JIC2026/
├── scripts/analisis_proyecto/
│   ├── 01_download_chembl.py          # Descarga datos ChEMBL
│   ├── 02_download_geodata.py         # Descarga geodatos Panamá
│   └── 03_prepare_dashboard_data.py   # Prepara datos para dashboard
│
├── notebooks/
│   └── 08_chembl_analisis_datos.ipynb  # NOTEBOOK PRINCIPAL (Entregable 1)
│
├── dashboard/
│   ├── app.py                          # Dashboard Dash-Plotly
│   ├── pages/                          # Páginas del dashboard
│   ├── data/                           # Datos y modelos para el dashboard
│   ├── assets/                         # CSS
│   ├── requirements.txt
│   ├── Procfile
│   └── render.yaml
│
├── data/raw/
│   ├── chembl_panama_bioactivity.csv   # Dataset ChEMBL descargado
│   ├── panama_distritos.geojson        # Shapefile distritos
│   └── inec_sociodemografico.csv       # Datos INEC
│
└── docs/
    └── articulo_ieee/
        ├── main.tex                    # Artículo LaTeX
        └── figures/                    # Figuras del artículo
```

---

## 9. Conclusión

El repositorio actual **no puede presentarse tal cual** para el proyecto final del curso porque le faltan 12 de 20 requisitos específicos (EDA clásico, UpSetPlot/Missingno, modelos de regresión con R², dashboard Dash-Plotly, mapa GeoPandas, despliegue web).

Sin embargo, **expandirlo con ChEMBL es la opción ideal** porque:

1. **Mantiene coherencia temática:** bioactividad de plaguicidas panameños
2. **Reutiliza el corpus existente:** los 20 ingredientes activos del MIDA
3. **Genera un dataset tabular rico:** con variables numéricas y categóricas naturales
4. **Permite cumplir todos los requisitos** sin inventar un dataset desconectado
5. **El componente GNN + XAI existente** se convierte en valor agregado (diferenciador)
6. **El bonus JIC (+15 pts)** ya está cubierto por la participación en la jornada

La expansión es modular: se agrega una capa de análisis clásico sobre el mismo dominio, sin modificar el pipeline GNN existente.
