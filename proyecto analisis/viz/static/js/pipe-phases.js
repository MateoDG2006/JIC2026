/* Pipeline interactivo — canvas disperso + popup con código */

const PIPE_ICONS = {
  database: `<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="8" ry="3" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`,
  link: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 007.1 0l2-2a5 5 0 00-7.1-7.1l-1.3 1.3M14 11a5 5 0 00-7.1 0l-2 2a5 5 0 007.1 7.1l1.3-1.3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  docker: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="10" width="18" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M7 10V7h2v3M11 10V7h2v3M15 10V7h2v3M7 14h10" stroke="currentColor" stroke-width="1.6"/></svg>`,
  script: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6l-4 6 4 6M16 6l4 6-4 6M14 4l-4 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  file: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4h7l5 5v11a1 1 0 01-1 1H7a1 1 0 01-1-1V5a1 1 0 011-1z" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M14 4v5h5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`,
  missing: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 8h8M8 12h5M8 16h8" stroke="currentColor" stroke-width="1.6" stroke-dasharray="3 2" opacity="0.5"/></svg>`,
  filter: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16l-6 7v6l-4 2v-8L4 5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`,
  impute: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="5" width="14" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M9 12h6M12 9v6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  stats: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V9M10 19V5M15 19v-7M20 19V3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  chart: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="12" width="4" height="8" fill="currentColor" opacity="0.5"/><rect x="10" y="8" width="4" height="12" fill="currentColor" opacity="0.7"/><rect x="16" y="4" width="4" height="16" fill="currentColor"/></svg>`,
  heatmap: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="5" height="5" fill="#3b82f6"/><rect x="10" y="4" width="5" height="5" fill="#22c55e"/><rect x="16" y="4" width="5" height="5" fill="#ef4444"/><rect x="4" y="10" width="5" height="5" fill="#f59e0b"/><rect x="10" y="10" width="5" height="5" fill="#3b82f6"/><rect x="16" y="10" width="5" height="5" fill="#a855f7"/><rect x="4" y="16" width="5" height="5" fill="#14b8a6"/><rect x="10" y="16" width="5" height="5" fill="#ef4444"/><rect x="16" y="16" width="5" height="5" fill="#22c55e"/></svg>`,
  target: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="3" fill="currentColor"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" stroke-width="1.6"/></svg>`,
  cluster: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="10" r="3" fill="#3b82f6"/><circle cx="16" cy="8" r="3" fill="#22c55e"/><circle cx="14" cy="16" r="3" fill="#f59e0b"/></svg>`,
  test: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  ml: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="8" width="6" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="9" y="4" width="6" height="14" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="15" y="10" width="6" height="8" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`,
  api: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h16v8H4z" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 12h2M14 12h2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  browser: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3 9h18" stroke="currentColor" stroke-width="1.6"/></svg>`,
  cloud: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18h10a4 4 0 000-8 5.5 5.5 0 00-10.6-1.2A3.5 3.5 0 007 18z" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`,
  globe: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`,
  fork: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v6M12 14v6M12 10c0-2 4-2 4-4s-2-4-4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
};

const PIPE_VISUALS = {
  funnel: `<svg class="pipe-visual-svg" viewBox="0 0 200 80" aria-hidden="true"><path d="M10 10h180l-30 25H40L10 10z" fill="rgba(59,130,246,0.25)" stroke="#3b82f6"/><path d="M40 35h120l-20 25H60L40 35z" fill="rgba(59,130,246,0.35)" stroke="#3b82f6"/><path d="M60 60h80l-10 10H70L60 60z" fill="rgba(34,197,94,0.35)" stroke="#22c55e"/></svg>`,
  tables: `<svg class="pipe-visual-svg" viewBox="0 0 200 70" aria-hidden="true"><rect x="10" y="10" width="80" height="50" rx="4" fill="none" stroke="#a855f7"/><path d="M10 25h80M30 10v50" stroke="#a855f7" opacity="0.6"/><rect x="110" y="10" width="80" height="50" rx="4" fill="none" stroke="#22c55e"/><path d="M110 25h80M130 10v50" stroke="#22c55e" opacity="0.6"/></svg>`,
  charts: `<svg class="pipe-visual-svg" viewBox="0 0 200 70" aria-hidden="true"><rect x="15" y="35" width="12" height="30" fill="#40916c"/><rect x="35" y="25" width="12" height="40" fill="#3b82f6"/><rect x="55" y="40" width="12" height="25" fill="#40916c"/><rect x="90" y="20" width="90" height="45" rx="3" fill="none" stroke="#a855f7"/><rect x="95" y="25" width="15" height="15" fill="#ef4444"/><rect x="115" y="25" width="15" height="15" fill="#3b82f6"/><rect x="135" y="25" width="15" height="15" fill="#22c55e"/></svg>`,
  tree: `<svg class="pipe-visual-svg" viewBox="0 0 200 80" aria-hidden="true"><circle cx="100" cy="12" r="8" fill="#3b82f6"/><path d="M100 20v15M100 35H40M100 35H160" stroke="#8b9cb3"/><circle cx="40" cy="55" r="8" fill="#f59e0b"/><circle cx="100" cy="55" r="8" fill="#a855f7"/><circle cx="160" cy="55" r="8" fill="#ef4444"/></svg>`,
  deploy: `<svg class="pipe-visual-svg" viewBox="0 0 200 70" aria-hidden="true"><rect x="10" y="25" width="40" height="30" rx="4" fill="none" stroke="#06b6d4"/><path d="M60 40h30l-8-8 8-8" fill="none" stroke="#8b9cb3"/><path d="M100 40h30" stroke="#8b9cb3" stroke-dasharray="4 3"/><rect x="140" y="20" width="50" height="40" rx="4" fill="rgba(34,197,94,0.15)" stroke="#22c55e"/><path d="M155 35h20M155 42h14" stroke="#22c55e"/></svg>`,
};

/** Ilustraciones locales (SVG inline vía fetch + caché) */
const PIPE_ILLUS = (name) => `/static/img/pipe/${name}.svg`;
const _pipeSvgCache = new Map();

async function hydratePipeIllustrations(root) {
  if (!root) return;
  const slots = root.querySelectorAll("[data-illus]");
  await Promise.all(
    [...slots].map(async (slot) => {
      const key = slot.dataset.illus;
      if (!key) return;
      try {
        if (!_pipeSvgCache.has(key)) {
          const res = await fetch(PIPE_ILLUS(key));
          if (!res.ok) throw new Error(`SVG ${key}: ${res.status}`);
          _pipeSvgCache.set(key, await res.text());
        }
        slot.innerHTML = _pipeSvgCache.get(key);
        slot.classList.add("is-loaded");
      } catch {
        slot.classList.add("is-fallback");
      }
    })
  );
}

function prefetchPipeIllustrations() {
  const keys = new Set(
    Object.values(PIPE_ENRICHMENT)
      .map((e) => e.illus)
      .filter(Boolean)
  );
  keys.forEach((key) => {
    if (_pipeSvgCache.has(key)) return;
    fetch(PIPE_ILLUS(key))
      .then((r) => (r.ok ? r.text() : Promise.reject()))
      .then((svg) => _pipeSvgCache.set(key, svg))
      .catch(() => {});
  });
}

/** Posiciones legacy — reemplazadas por computeSequentialPositions */
const PIPE_SCATTER = {};

/** Conceptos, procesos e imágenes de referencia por paso / overview */
const PIPE_ENRICHMENT = {
  "overview-1": {
    illus: "molecule",
    imageCaption: "Estructura química (ejemplo) — identidad molecular vía SMILES/CID",
    concepts: [
      { term: "Trazabilidad", def: "Cada dato debe poder rastrearse hasta su fuente primaria (PubChem, ChEMBL) para auditoría regulatoria." },
      { term: "Corpus", def: "Conjunto curado de compuestos relevantes para Panamá, no una descarga masiva sin filtro." },
      { term: "pchembl_value", def: "Potencia normalizada en escala logarítmica (−log10 de concentración molar), comparable entre ensayos." },
    ],
    process: [
      "Construir lista de CIDs desde MIDA + clasificación PubChem HID 72.",
      "Resolver SMILES canónico y emparejar con ChEMBL ID.",
      "Consultar actividades vía servidor Docker local.",
      "Aplicar filtros QC y exportar CSV trazable.",
    ],
  },
  "f1-1": {
    illus: "pubchem",
    imageCaption: "PubChem — base abierta del NIH (NIH/NLM)",
    concepts: [
      { term: "CID", def: "Compound Identifier de PubChem: entero único por estructura química registrada." },
      { term: "HID 72", def: "Nodo 'Pesticides' en el árbol de clasificación PubChem; agrupa compuestos agroquímicos." },
      { term: "SMILES", def: "Notación lineal de la estructura molecular; base para match estructural en ChEMBL." },
      { term: "MIDA", def: "Ministerio de Desarrollo Agropecuario de Panamá — fuente de ingredientes activos registrados." },
    ],
    process: [
      "Obtener nombres de ingredientes activos del registro MIDA.",
      "Consultar PubChem PUG REST por nombre → CID + SMILES.",
      "Complementar con CIDs del árbol HID 72 (familias químicas).",
      "Validar SMILES con RDKit y deduplicar por CID.",
      "Exportar pubchem_panama_cids.csv con metadatos de fuente.",
    ],
  },
  "f1-2": {
    illus: "molecule",
    imageCaption: "Clorpirifos — plaguicida organofosforado del corpus panameño",
    concepts: [
      { term: "chembl_id", def: "Identificador único de molécula en ChEMBL (CHEMBL…); clave foránea de actividades." },
      { term: "Match estructural", def: "Emparejamiento por SMILES canónico exacto, no por nombre comercial (puede haber sinónimos)." },
      { term: "molregno", def: "ID numérico interno de ChEMBL vinculado a chembl_id." },
    ],
    process: [
      "Canonicalizar SMILES con RDKit.",
      "Consultar molecule_dictionary en ChEMBL v37.",
      "Registrar hits, misses y motivo de descarte.",
      "Generar tabla compuesto ↔ chembl_id para extracción.",
    ],
  },
  "f1-3": {
    illus: "docker",
    imageCaption: "Docker — contenedor con ChEMBL SQLite (~30 GB) fuera del repo",
    concepts: [
      { term: "Contenedor", def: "Entorno aislado con la BD y el servidor; reproducible en cualquier máquina con Docker." },
      { term: "Volumen persistente", def: "Almacenamiento que sobrevive al reinicio del contenedor (jic2026_chembl_db)." },
      { term: "chembl-server", def: "API HTTP que expone consultas SQL sin copiar la base al proyecto." },
    ],
    process: [
      "Descargar dump SQLite ChEMBL v37 (una vez).",
      "Montar volumen Docker e inicializar imagen chembl-init.",
      "Levantar uvicorn en puerto 8765.",
      "Verificar GET /status antes de extraer.",
    ],
  },
  "f1-4": {
    illus: "assay",
    imageCaption: "Curva dosis-respuesta — base del cálculo de IC50 / pchembl",
    concepts: [
      { term: "standard_type", def: "Tipo de medida bioquímica (IC50, Ki, Kd…); solo tipos comparables se conservan." },
      { term: "data_validity_comment", def: "Anotación ChEMBL sobre calidad del dato; valores dudosos se excluyen." },
      { term: "IC50", def: "Concentración que inhibe el 50% de la actividad; menor IC50 = mayor potencia." },
    ],
    process: [
      "Por cada chembl_id, consultar actividades asociadas.",
      "Filtrar por standard_type permitidos en config.",
      "Descartar registros con flags de validez negativos.",
      "Calcular o importar pchembl_value.",
      "Adjuntar descriptores RDKit por compuesto.",
    ],
  },
  "f1-5": {
    illus: "database",
    imageCaption: "Tabla relacional — una fila por medición bioquímica",
    concepts: [
      { term: "Granularidad fila", def: "Cada fila = una medición en un ensayo concreto (compuesto × target × tipo)." },
      { term: "Descriptor RDKit", def: "Propiedad calculada de la estructura (mw, alogp, psa…) — constante por compuesto." },
      { term: "Target", def: "Proteína o diana biológica del ensayo (target_chembl_id)." },
    ],
    process: [
      "Concatenar resultados de todos los compuestos resueltos.",
      "Aplicar funnel de calidad documentado en notebook.",
      "Exportar CSV con 33 columnas y metadatos de extracción.",
      "Validar conteos: 171 compuestos, 9 752 mediciones.",
    ],
  },
  "overview-2": {
    illus: "database",
    imageCaption: "Transformación de tabla ancha y repetida → tablas analíticas",
    concepts: [
      { term: "Missingness", def: "Patrón de valores faltantes; debe visualizarse antes de imputar (requisito curso)." },
      { term: "Unidad de análisis", def: "Decisión crítica: ¿fila de medición o compuesto? Define validez estadística." },
      { term: "Imputación", def: "Sustitución de NaN por estimación; aquí mediana por familia química." },
    ],
    process: ["Diagnosticar NaN → filtrar columnas sparse → imputar → agregar → bifurcar en 3 CSV."],
  },
  "f2-1": {
    illus: "database",
    imageCaption: "Pandas DataFrame — estructura del CSV crudo de Fase 1",
    concepts: [
      { term: "Duplicación estructural", def: "Descriptores idénticos repetidos en cada fila del mismo SMILES." },
      { term: "Inflación de n", def: "Usar 9 752 filas para correlacionar mw infla artificialmente el tamaño muestral." },
    ],
    process: ["Cargar CSV crudo.", "Explorar shape y cardinalidad por SMILES.", "Documentar por qué se cambia la unidad de análisis."],
  },
  "f2-2": {
    illus: "missing",
    imageCaption: "Heatmap de valores — analogía visual al diagnóstico missingno",
    concepts: [
      { term: "MCAR/MAR/MNAR", def: "Tipos de mecanismo de faltantes: aleatorio, dependiente de observados, o del valor missing." },
      { term: "UpSetPlot", def: "Visualiza intersecciones de columnas con NaN simultáneos (más legible que Venn con muchas variables)." },
      { term: "missingno", def: "Librería Python para matriz, barras y heatmap de missingness." },
    ],
    process: ["Generar msno.matrix() y msno.bar().", "Construir UpSetPlot de intersecciones.", "Documentar decisiones antes de imputar.", "Exportar figuras a outputs/chembl/figures/."],
  },
  "f2-3": {
    illus: "funnel",
    imageCaption: "Embudo de filtrado — cada regla reduce filas/columnas",
    concepts: [
      { term: "Duplicado potencial", def: "Registros ChEMBL con misma molécula, target y tipo; se deduplica conservando el de mayor calidad." },
      { term: "Columna sparse", def: "Variable con >250 NaN (umbral syllabus) — poca información, se elimina." },
      { term: "Binding vs organism", def: "Ensayos a nivel proteína vs organismo completo; no mezclar sin documentar." },
    ],
    process: ["filter_potential_duplicates().", "Eliminar columnas con >250 NaN.", "Separar endpoints por tipo de ensayo.", "Registrar conteos en cada paso del funnel."],
  },
  "f2-4": {
    illus: "impute",
    imageCaption: "Imputación — rellenar NaN con estimación justificada",
    concepts: [
      { term: "Mediana por grupo", def: "Robusta a outliers; apropiada cuando familias químicas tienen rangos distintos." },
      { term: "Fallback global", def: "Si una familia tiene pocos casos, se usa mediana de todo el corpus." },
      { term: "Moda", def: "Para categóricas: valor más frecuente, o 'Unknown' si no hay consenso." },
    ],
    process: ["Identificar columnas numéricas vs categóricas.", "Imputar numéricas por mediana de family.", "Fallback mediana global.", "Documentar conteos pre/post en notebook."],
  },
  "f2-5": {
    illus: "split",
    imageCaption: "Normalización — separar medición y compuesto",
    concepts: [
      { term: "activities_clean", def: "Nivel medición: promiscuidad, perfiles por target." },
      { term: "compounds_all", def: "147 compuestos con descriptores estructurales." },
      { term: "compounds_features", def: "89 compuestos con pchembl_median_binding agregado." },
    ],
    process: ["Agregar descriptores a nivel SMILES.", "Calcular mediana de pchembl por compuesto (solo binding).", "Exportar 3 CSV a data/processed/."],
  },
  "overview-3": {
    illus: "histogram",
    imageCaption: "EDA — explorar distribuciones antes de modelar",
    concepts: [
      { term: "EDA", def: "Exploratory Data Analysis: entender datos sin inferencia formal todavía." },
      { term: "Pearson vs Spearman", def: "Lineal vs monótona; Spearman es robusto a outliers y relaciones no lineales." },
    ],
    process: ["Cargar compounds_features (147 filas).", "Estadísticos → distribuciones → correlaciones → promiscuidad → exportar figuras."],
  },
  "f3-1": {
    illus: "molecule",
    imageCaption: "RDKit — descriptores moleculares calculados del SMILES",
    concepts: [
      { term: "mw", def: "Peso molecular (Da) — tamaño del compuesto." },
      { term: "alogp", def: "Logaritmo de la partición octanol/agua — lipofilia." },
      { term: "psa", def: "Polar Surface Area — capacidad de cruzar membranas." },
      { term: "Rule of 5", def: "Heurística de Lipinski para biodisponibilidad oral (referencia en descriptores)." },
    ],
    process: ["Verificar 147 filas únicas por SMILES.", "Revisar rangos de descriptores.", "Confirmar campo family para agrupaciones."],
  },
  "f3-2": {
    illus: "histogram",
    imageCaption: "Distribución de frecuencias — base de estadísticos descriptivos",
    concepts: [
      { term: "Media vs mediana", def: "Media sensible a outliers; mediana representa el valor central robusto." },
      { term: "IQR", def: "Rango intercuartílico (Q3−Q1) — dispersión del 50% central." },
      { term: "Sesgo", def: "Asimetría de la distribución; detectable en histogramas." },
    ],
    process: ["describe() global y por familia.", "Comparar μ y mediana por descriptor.", "Identificar variables con colas pesadas."],
  },
  "f3-3": {
    illus: "boxplot",
    imageCaption: "Boxplot — comparación de distribuciones por familia química",
    concepts: [
      { term: "Boxplot", def: "Muestra mediana, IQR y outliers; ideal para comparar grupos categóricos." },
      { term: "Outlier", def: "Valor extremo respecto al IQR; no implica error, pero debe investigarse." },
      { term: "Familia química", def: "Agrupación (organofosforado, triazina…) que puede explicar diferencias de alogp, psa, etc." },
    ],
    process: ["Histogramas por descriptor.", "Boxplots agrupados por family.", "Anotar familias con mayor dispersión.", "Exportar PNG para informe y dashboard."],
  },
  "f3-4": {
    illus: "correlation",
    imageCaption: "Tipos de correlación — Pearson captura solo relaciones lineales",
    concepts: [
      { term: "Colinealidad", def: "Dos predictores muy correlacionados; problemático para regresión/RF." },
      { term: "Pearson (r)", def: "Correlación lineal entre −1 y 1." },
      { term: "Spearman (ρ)", def: "Correlación de rangos; detecta monotonicidad sin linealidad." },
    ],
    process: ["Calcular matriz Pearson.", "Calcular matriz Spearman.", "Identificar pares |r|>0.7.", "Exportar JSON para dashboard."],
  },
  "f3-5": {
    illus: "target",
    imageCaption: "Diana biológica (target) — unión proteína-ligando",
    concepts: [
      { term: "Promiscuidad", def: "Número de targets distintos a los que se une un compuesto; alto = polifarmacológico." },
      { term: "Potencia vs promiscuidad", def: "pchembl mide qué tan fuerte; promiscuidad mide cuántas dianas afecta." },
    ],
    process: ["Usar activities_clean (nivel medición).", "Contar targets únicos por SMILES.", "Rankear compuestos más promiscuos.", "Documentar mezcla de standard_type."],
  },
  "f3-6": {
    illus: "plotly",
    imageCaption: "Artefactos exportados alimentan gráficos del dashboard",
    concepts: [
      { term: "Artefacto", def: "Salida reproducible (PNG, JSON) generada por el notebook." },
      { term: "P1 / P2", def: "Preguntas de investigación del informe respondidas con estas figuras." },
    ],
    process: ["Consolidar figuras en outputs/chembl/figures/.", "Generar JSON de correlación.", "Narrar hallazgos en informe IEEE."],
  },
  "overview-4": {
    illus: "pca",
    imageCaption: "PCA — reducir dimensionalidad preservando varianza",
    concepts: [
      { term: "Multivariado", def: "Análisis simultáneo de varias variables; detecta estructura conjunta." },
      { term: "Data leakage", def: "Información del test en train; infla métricas si compuestos se repiten en ambos." },
    ],
    process: ["Escalar features → PCA/K-means → Kruskal–Wallis → RF baseline con 3 splits → exportar JSON."],
  },
  "f4-1": {
    illus: "histogram",
    imageCaption: "StandardScaler — normalizar media 0 y varianza 1",
    concepts: [
      { term: "StandardScaler", def: "Resta media y divide por σ; necesario para PCA y distancias euclidianas." },
      { term: "Varianza nula", def: "Columna constante (num_ro5_violations=0) — se excluye del análisis." },
    ],
    process: ["Seleccionar 7 descriptores.", "Excluir columnas sin varianza.", "Aplicar StandardScaler.", "Guardar matriz para 3 ramas."],
  },
  "f4-2": {
    illus: "pca",
    imageCaption: "Clustering — agrupar compuestos por similitud de descriptores",
    concepts: [
      { term: "PCA", def: "Componentes principales = combinaciones lineales que maximizan varianza explicada." },
      { term: "K-means", def: "Particiona en k grupos minimizando distancia intra-cluster." },
      { term: "Silueta", def: "Métrica de cohesión/separación de clusters (−1 a 1)." },
      { term: "ARI", def: "Adjusted Rand Index — concordancia entre clusters y familias químicas." },
    ],
    process: ["PCA con 2 componentes.", "Evaluar varianza explicada.", "K-means k=2.", "Calcular silueta y ARI vs family.", "Exportar clustering_summary.json."],
  },
  "f4-3": {
    illus: "ml-tree",
    imageCaption: "Contraste de hipótesis — ¿difieren familias en alogp, psa…?",
    concepts: [
      { term: "Kruskal–Wallis", def: "Test no paramétrico: ¿≥3 grupos difieren en distribución?" },
      { term: "FDR (Benjamini–Hochberg)", def: "Corrección por comparaciones múltiples; controla falsos positivos." },
      { term: "ε² (epsilon cuadrado)", def: "Tamaño del efecto; cuánta varianza explica la familia química." },
    ],
    process: ["Por cada descriptor, Kruskal–Wallis por family.", "Aplicar corrección FDR.", "Post-hoc Dunn si significativo.", "Exportar stats_tests.csv."],
  },
  "f4-4": {
    illus: "ml-tree",
    imageCaption: "Random Forest — ensemble de árboles de decisión",
    concepts: [
      { term: "Random Forest", def: "Muchos árboles entrenados en bootstrap; promedia predicciones." },
      { term: "GroupKFold", def: "CV que mantiene compuestos enteros en train o test — evita leakage." },
      { term: "R² negativo", def: "Modelo peor que predecir la media; señal de no generalización." },
    ],
    process: ["Entrenar RF con Morgan/descriptores.", "Split 1: filas aleatorias (fuga).", "Split 2: por scaffold groups.", "Split 3: GroupKFold por SMILES.", "Comparar R² en baseline_honest_metrics.csv."],
  },
  "f4-5": {
    illus: "api",
    imageCaption: "JSON — formato de intercambio para el dashboard",
    concepts: [
      { term: "Artefacto precomputado", def: "Resultado calculado offline; el dashboard solo sirve, no recalcula." },
      { term: "Límite QSAR", def: "Con 147 compuestos y 7 descriptores, RF no supera baseline naive." },
    ],
    process: ["Exportar PCA, clustering, stats, baseline.", "Copiar a outputs/chembl/results/.", "Validar con verify_flow_b.py."],
  },
  "overview-5": {
    illus: "dashboard",
    imageCaption: "Dashboard interactivo — entregable 2 del curso",
    concepts: [
      { term: "Full-stack ligero", def: "FastAPI sirve JSON; Plotly.js renderiza en el navegador." },
      { term: "Bundle estático", def: "Artefactos empaquetados para despliegue sin BD ChEMBL." },
    ],
    process: ["prepare_dashboard.py → FastAPI → Plotly UI → deploy Render → URLs públicas."],
  },
  "f5-1": {
    illus: "database",
    imageCaption: "Bundle de CSV + JSON generados en Fases 2–4",
    concepts: [
      { term: "Manifest", def: "Índice de artefactos con checksums MD5 para invalidar caché." },
      { term: "Separación compute/serve", def: "Cálculo pesado local; producción solo lee archivos." },
    ],
    process: ["Recopilar outputs de Fases 2–4.", "Verificar integridad de CSV/JSON.", "Organizar en outputs/dashboard/."],
  },
  "f5-2": {
    illus: "build",
    imageCaption: "Script de build — transforma CSV en JSON para Plotly",
    concepts: [
      { term: "ETL ligero", def: "Extract (CSV) → Transform (agregaciones) → Load (JSON estático)." },
      { term: "Idempotencia", def: "Re-ejecutar prepare_dashboard produce el mismo bundle dado los mismos inputs." },
    ],
    process: ["Leer compounds_*.csv y resultados JSON.", "Generar correlation, pca_clusters, family_stats.", "Escribir manifest.json.", "Copiar CSVs para Render."],
  },
  "f5-3": {
    illus: "api",
    imageCaption: "FastAPI — backend Python con rutas /api/analytics",
    concepts: [
      { term: "REST API", def: "Endpoints HTTP que devuelven JSON; el frontend consume con fetch()." },
      { term: "Caché MD5", def: "Si el archivo no cambió, se reutiliza respuesta en memoria." },
      { term: "resolve_path", def: "Busca artefactos en processed → dashboard → bundle." },
    ],
    process: ["Definir rutas en analytics.py.", "Implementar resolve_path en config.py.", "Cachear por checksum.", "Exponer /health para Render."],
  },
  "f5-4": {
    illus: "plotly",
    imageCaption: "Plotly.js — gráficos interactivos en el navegador",
    concepts: [
      { term: "Plotly.js", def: "Librería JS para gráficos interactivos (zoom, hover, filtros)." },
      { term: "Controlador interactivo", def: "UI (select, slider) que dispara re-fetch o re-render del gráfico." },
      { term: "Jinja2", def: "Motor de templates Python que sirve HTML con rutas estáticas." },
    ],
    process: ["Template eda.html carga JS.", "Fetch a /api/analytics/chembl/*.", "Plotly.newPlot con datos JSON.", "Controles de variable, familia y MW."],
  },
  "f5-5": {
    illus: "cloud",
    imageCaption: "Despliegue en la nube — Render Web Service",
    concepts: [
      { term: "PaaS", def: "Platform as a Service: Render gestiona servidor, HTTPS y redeploy." },
      { term: "PORT dinámico", def: "Variable de entorno $PORT asignada por la plataforma." },
      { term: "CI/CD", def: "git push dispara rebuild automático del contenedor." },
    ],
    process: ["Configurar Dockerfile con bundle.", "Definir start command uvicorn.", "Conectar repo GitHub.", "Verificar /health tras deploy."],
  },
  "f5-6": {
    illus: "browser",
    imageCaption: "URLs públicas para evaluación del curso",
    concepts: [
      { term: "/dashboard", def: "Vista interactiva principal con ≥4 gráficas y controles." },
      { term: "/presentacion", def: "Este deck de slides del pipeline del proyecto." },
      { term: "Entregable 2", def: "Dashboard web accesible + video explicativo (syllabus)." },
    ],
    process: ["Publicar URL en informe IEEE.", "Grabar video recorriendo /dashboard.", "Incluir enlace en README del repo."],
  },
};

function enrichDetail(detail, { stepId, phaseId, isOverview }) {
  const key = isOverview ? `overview-${phaseId}` : stepId;
  const extra = PIPE_ENRICHMENT[key];
  if (!extra) return detail;
  return {
    ...detail,
    illus: extra.illus || detail.illus,
    imageCaption: extra.imageCaption || detail.imageCaption,
    concepts: extra.concepts || detail.concepts,
    process: extra.process || detail.process,
  };
}

const PIPE_PHASES = {
  1: {
    overview: {
      icon: "database",
      title: "Desglose completo — Fase 1: Adquisición",
      summary: "Pipeline reproducible desde PubChem hasta un CSV trazable de bioactividad ChEMBL para plaguicidas registrados en Panamá.",
      bullets: [
        "Entrada verificable: 235 CIDs (MIDA + árbol HID72 de PubChem Classification).",
        "Salida: 9 752 mediciones con diana, target, pchembl y 8 descriptores RDKit.",
        "Infraestructura local: ChEMBL v37 en Docker (~30 GB) consultado vía HTTP.",
      ],
      io: { input: "pubchem_panama_cids.csv", output: "chembl_panama_bioactivity.csv" },
      metrics: [{ label: "Entrada", value: "235 CIDs" }, { label: "Salida", value: "9 752 med." }, { label: "Compuestos", value: "171" }],
      visual: "funnel",
      sections: [
        { title: "¿Por qué esta fase?", body: "Sin trazabilidad primaria (PubChem + ChEMBL) no se puede citar la fuente en el informe IEEE ni auditar los filtros de calidad." },
        { title: "Rol responsable", body: "Ingeniero de Datos — construye el pipeline de extracción y documenta cada filtro en fase1_adquisicion.ipynb." },
      ],
      code: [{ title: "Comando principal", lang: "bash", code: "make chembl-extract\n# o: python scripts/fase1/extract_chembl.py" }],
    },
    steps: [
      { id: "f1-1", type: "source", icon: "database", tag: "Fuente", title: "PubChem MIDA", stat: "235 CIDs", detail: { title: "Corpus panameño (PubChem)", summary: "Lista de ingredientes activos del MIDA enriquecida con el árbol de clasificación HID 72 (Pesticides).", bullets: ["235 candidatos iniciales resueltos por nombre o CID.", "Familias: organofosforados, piretroides, triazinas, azoles, etc.", "Cada fila incluye CID, SMILES, fuente y familia química."], visual: "funnel", artifact: "data/raw/pubchem_panama_cids.csv", io: { input: "API PubChem REST", output: "pubchem_panama_cids.csv" }, metrics: [{ label: "CIDs", value: "235" }, { label: "Familias", value: "7+" }, { label: "Fuente", value: "MIDA" }], sections: [{ title: "Qué hace", body: "Descarga CIDs desde búsqueda por nombre (lista MIDA) y desde nodos del árbol de clasificación PubChem HID 72." }, { title: "Validación", body: "SMILES canónico con RDKit; se descartan estructuras inválidas antes de consultar ChEMBL." }], code: [{ title: "Consulta por nombre (PubChem PUG REST)", lang: "python", code: 'url = f"{BASE}/compound/name/{name}/property/CanonicalSMILES,IUPACName/JSON"\nresp = requests.get(url, timeout=30)\ncid = resp.json()["PropertyTable"]["Properties"][0]["CID"]' }] } },
      { id: "f1-2", type: "process", icon: "link", tag: "Match", title: "ChEMBL ID", stat: "171 resueltos", detail: { title: "Resolución SMILES → chembl_id", summary: "Cada SMILES canónico se empareja al registro molecular único en ChEMBL.", bullets: ["171 de 235 candidatos obtienen chembl_id.", "Descartados: SMILES inválidos, sin registro o duplicados estructurales.", "Garantiza trazabilidad compuesto ↔ estructura ↔ actividades."], artifact: "scripts/fase1/extract_chembl.py", io: { input: "SMILES canónico", output: "chembl_id + molregno" }, sections: [{ title: "Criterio de match", body: "Búsqueda exacta por SMILES canónico en la tabla molecule_dictionary de ChEMBL v37." }, { title: "Pérdida esperada", body: "No todos los plaguicidas agro están ensayados en ChEMBL; los no resueltos se documentan en el funnel del notebook." }], code: [{ title: "Resolución en el script", lang: "python", code: '# GET /molecule?smiles={canonical_smiles}\n# → molecule_chembl_id usado en consultas de actividad' }] } },
      { id: "f1-3", type: "infra", icon: "docker", tag: "Infra", title: "Docker ChEMBL", stat: "v37 · :8765", detail: { title: "Servidor chembl-server local", summary: "Base SQLite de ChEMBL montada en volumen Docker; el host Python consulta vía HTTP sin copiar 30 GB al repo.", bullets: ["Imagen: docker/Dockerfile.server + chembl-init.", "Volumen persistente: jic2026_chembl_db.", "Endpoint: http://localhost:8765"], artifact: "make setup-chembl", io: { input: "chembl_37_sqlite.tar.gz", output: "API HTTP :8765" }, sections: [{ title: "¿Por qué Docker?", body: "ChEMBL completo no cabe en git ni en Render; solo se usa en extracción local." }, { title: "Healthcheck", body: "GET /status confirma que la BD está montada antes de lanzar extract_chembl.py." }], code: [{ title: "Levantar servidor", lang: "bash", code: "make setup-chembl    # descarga + volumen\nmake chembl-server   # uvicorn en :8765" }] } },
      { id: "f1-4", type: "process", icon: "script", tag: "Extract", title: "Extracción", stat: "Filtros QC", detail: { title: "extract_chembl.py — consulta y normalización", summary: "Descarga actividades, calcula pchembl_value y aplica filtros de calidad definidos en config.", bullets: ["Solo standard_type permitidos (IC50, Ki, EC50, …).", "Excluye registros con data_validity_comment sospechoso.", "Normaliza unidades y relaciones (=, <, >) a pchembl."], artifact: "config/chembl/standard_types.json", io: { input: "chembl_id list", output: "filas de actividad crudas" }, sections: [{ title: "Filtros de calidad", body: "Se eliminan tipos no comparables (p.ej. % inhibition sin concentración) y actividades sin valor numérico." }, { title: "pchembl", body: "Transformación logarítmica estándar de ChEMBL para comparar potencias entre ensayos." }], code: [{ title: "Tipos estándar permitidos", lang: "json", code: '["IC50", "Ki", "Kd", "EC50", "Potency", "Inhibition"]\n# config/chembl/standard_types.json' }, { title: "Cálculo pchembl", lang: "python", code: "# pchembl_value = -log10(molar IC50)\n# relation='>' imputa límite inferior documentado" }] } },
      { id: "f1-5", type: "output", icon: "file", tag: "Salida", title: "CSV crudo", stat: "9 752 med.", detail: { title: "chembl_panama_bioactivity.csv", summary: "Tabla relacional lista para limpieza en Fase 2 — una fila por medición.", bullets: ["171 compuestos únicos con al menos una actividad.", "9 752 filas tras filtros QC (múltiples dianas por compuesto).", "Columnas: target, assay, standard_type, pchembl_value, descriptores RDKit."], visual: "funnel", artifact: "data/raw/chembl_panama_bioactivity.csv", io: { input: "actividades filtradas", output: "33 columnas × 9 752 filas" }, sections: [{ title: "Granularidad", body: "Una fila = una medición en un ensayo. El mismo compuesto aparece muchas veces (distintas dianas)." }, { title: "Siguiente paso", body: "Fase 2 agrega a nivel compuesto y separa activities_clean vs compounds_*." }], code: [{ title: "Columnas clave", lang: "text", code: "molecule_chembl_id | target_chembl_id | standard_type\npchembl_value | canonical_smiles | mw | alogp | psa ..." }] } },
    ],
  },
  2: {
    overview: {
      icon: "missing",
      title: "Desglose completo — Fase 2: Limpieza",
      summary: "Transformar filas repetidas en tablas analíticas coherentes con diagnóstico explícito de missingness.",
      bullets: ["Missingno + UpSetPlot antes de imputar (requisito del curso).", "Imputación numérica por mediana de familia química.", "Salida: 147 compuestos estructurales · 89 con pchembl medianado."],
      io: { input: "chembl_panama_bioactivity.csv", output: "activities_clean + compounds_*" },
      visual: "tables",
      sections: [{ title: "Problema central", body: "Analizar 9 752 filas duplica información estructural; la unidad correcta para EDA es el compuesto (147 filas)." }],
      code: [{ title: "Pipeline", lang: "bash", code: "jupyter notebooks/fase2_limpieza.ipynb\n# o: python -m analisis_proyecto.preprocessing.pipeline" }],
    },
    steps: [
      { id: "f2-1", type: "source", icon: "file", tag: "Entrada", title: "CSV Fase 1", stat: "33 cols", detail: { title: "Dataset crudo sin agregar", summary: "3 608+ filas únicas de medición con descriptores RDKit repetidos en cada fila del mismo compuesto.", bullets: ["Un compuesto puede repetirse decenas de veces (una por ensayo).", "8 descriptores RDKit idénticos por molécula en cada fila.", "Motiva el cambio de unidad de análisis a nivel compuesto."], artifact: "data/raw/chembl_panama_bioactivity.csv", io: { input: "Fase 1 output", output: "DataFrame sin agregar" }, sections: [{ title: "Duplicación estructural", body: "mw, alogp, psa… son constantes por SMILES; repetirlos infla artificialmente n en correlaciones." }], code: [{ title: "Detectar repetición", lang: "python", code: "df.groupby('canonical_smiles').size().describe()\n# max ~200 filas por mismo SMILES" }] } },
      { id: "f2-2", type: "viz", icon: "missing", tag: "Diagnóstico", title: "Missingno", stat: "UpSetPlot", detail: { title: "Patrones de valores faltantes", summary: "Visualización obligatoria antes de imputar — documenta qué columnas faltan y en qué combinaciones.", bullets: ["missingno: matriz, barras y heatmap de NaN.", "UpSetPlot: intersecciones de columnas faltantes simultáneas.", "Decisiones de drop/impute justificadas en el notebook."], visual: "charts", artifact: "outputs/chembl/figures/missingno_*.png", sections: [{ title: "Entregable curso", body: "El syllabus exige al menos una visualización de missingness antes de cualquier imputación." }], code: [{ title: "Missingno en notebook", lang: "python", code: "import missingno as msno\nmsno.matrix(df)\nmsno.bar(df)\n# UpSetPlot con upsetplot.from_contents(...)" }] } },
      { id: "f2-3", type: "process", icon: "filter", tag: "Filtrar", title: "Dedup + drop", stat: ">250 NaN", detail: { title: "Reglas de limpieza estructural", summary: "Elimina duplicados potenciales de ensayo y columnas con más de 250 NaN.", bullets: ["filter_potential_duplicates() antes de agregar.", "Drop columnas sparse (>250 NaN según syllabus).", "Separa endpoints binding vs organism-level para análisis posterior."], artifact: "src/analisis_proyecto/preprocessing/pipeline.py", sections: [{ title: "Duplicados de ensayo", body: "Misma molécula + mismo target + mismo tipo puede aparecer por curation ChEMBL; se conserva la medición de mayor confianza." }], code: [{ title: "Filtro de columnas", lang: "python", code: "MAX_NAN = 250\ncols_drop = df.columns[df.isna().sum() > MAX_NAN]\ndf = df.drop(columns=cols_drop)" }] } },
      { id: "f2-4", type: "process", icon: "impute", tag: "Imputar", title: "Mediana", stat: "Por familia", detail: { title: "Imputación numérica justificada", summary: "Mediana por familia química (campo family); fallback a mediana global si la familia tiene pocos casos.", bullets: ["Numéricas: mediana por familia → mediana global.", "Categóricas: moda o categoría 'Unknown'.", "Estrategia documentada con conteos antes/después."], artifact: "notebooks/fase2_limpieza.ipynb", sections: [{ title: "Justificación", body: "Organofosforados y triazinas tienen rangos distintos de alogp; imputar globalmente sesgaría comparaciones." }], code: [{ title: "Imputación por grupo", lang: "python", code: "for col in numeric_cols:\n    df[col] = df.groupby('family')[col].transform(\n        lambda s: s.fillna(s.median())\n    )\ndf[col] = df[col].fillna(df[col].median())" }] } },
      { id: "f2-5", type: "output", icon: "fork", tag: "Salidas", title: "3 tablas", stat: "2 niveles", detail: { title: "Bifurcación analítica", summary: "Dos granularidades: medición (promiscuidad) y compuesto (EDA/modelado).", bullets: ["activities_clean.csv — 9 752 filas de medición.", "compounds_all.csv — 147 compuestos con descriptores.", "compounds_features.csv — 89 con pchembl_median_binding."], visual: "tables", artifact: "data/processed/", io: { input: "tabla limpia", output: "3 CSV en processed/" }, sections: [{ title: "Cuándo usar cada tabla", body: "activities_clean → dianas y promiscuidad. compounds_* → histogramas, PCA, RF baseline." }], code: [{ title: "Agregación compuesto", lang: "python", code: "compounds = df.groupby('canonical_smiles').agg({\n    'mw': 'first', 'family': 'first',\n    'pchembl_value': 'median'  # solo binding\n}).reset_index()" }] } },
    ],
  },
  3: {
    overview: {
      icon: "chart",
      title: "Desglose completo — Fase 3: EDA",
      summary: "Caracterizar el corpus a nivel compuesto — sin modelos supervisados todavía.",
      bullets: ["147 filas para fisicoquímica (nunca 9 752).", "Pearson + Spearman: dos matrices de correlación.", "Responde preguntas P1, P2 y perfil de dianas del informe."],
      visual: "charts",
      code: [{ title: "Notebook", lang: "bash", code: "jupyter notebooks/fase3_eda.ipynb" }],
    },
    steps: [
      { id: "f3-1", type: "source", icon: "file", tag: "Entrada", title: "Compuestos", stat: "147 filas", detail: { title: "compounds_features.csv", summary: "Una fila = un compuesto con descriptores agregados y familia química.", bullets: ["mw, alogp, psa, hba, hbd, aromatic_rings, rotatable_bonds.", "pchembl_median_binding cuando hay ensayos binding.", "Campo family para agrupaciones en gráficos."], artifact: "data/processed/compounds_features.csv", code: [{ title: "Esquema", lang: "text", code: "canonical_smiles | family | mw | alogp | psa\nhba | hbd | aromatic_rings | rtb | pchembl_median_binding" }] } },
      { id: "f3-2", type: "process", icon: "stats", tag: "Stats", title: "Tendencia", stat: "μ · σ · IQR", detail: { title: "Medidas de tendencia central y dispersión", summary: "Estadísticos descriptivos por descriptor a nivel compuesto.", bullets: ["Media, mediana, desviación estándar, IQR.", "Comparación entre las 7 familias químicas.", "Base numérica para boxplots del dashboard."], artifact: "notebooks/fase3_eda.ipynb", code: [{ title: "Resumen por variable", lang: "python", code: "df[DESCRIPTORS].describe().T\n# + describe() agrupado por family" }] } },
      { id: "f3-3", type: "viz", icon: "chart", tag: "Distrib.", title: "Hist + Box", stat: "Por familia", detail: { title: "Visualización por categorías", summary: "Histogramas globales y boxplots agrupados por familia — requisito del dashboard.", bullets: ["7 familias en el corpus panameño.", "Detecta colas pesadas y outliers por familia.", "Exporta PNG anotados a outputs/chembl/figures/."], visual: "charts", artifact: "family_boxplots_annotated.png", code: [{ title: "Boxplot agrupado", lang: "python", code: "sns.boxplot(data=df, x='family', y='alogp')\nplt.xticks(rotation=45)\nplt.savefig('outputs/chembl/figures/family_boxplots_annotated.png')" }] } },
      { id: "f3-4", type: "viz", icon: "heatmap", tag: "Correl.", title: "P + S", stat: "2 matrices", detail: { title: "Correlación dual Pearson / Spearman", summary: "Pearson captura relaciones lineales; Spearman relaciones monótonas no lineales.", bullets: ["psa–hbd ≈ 0.81 (polaridad / enlaces H).", "alogp–hbd ≈ −0.57 (lipofilia vs polaridad).", "Informa colinealidad antes del modelado Fase 4."], visual: "charts", artifact: "correlation_pearson.json", code: [{ title: "Ambas matrices", lang: "python", code: "pearson = df[DESCRIPTORS].corr(method='pearson')\nspearman = df[DESCRIPTORS].corr(method='spearman')" }] } },
      { id: "f3-5", type: "process", icon: "target", tag: "Dianas", title: "Promiscuidad", stat: "1 015 targets", detail: { title: "Perfil de bioactividad por medición", summary: "Análisis legítimo solo a nivel activities_clean — cuenta dianas distintas por compuesto.", bullets: ["Identifica compuestos más promiscuos (más targets).", "Mezcla de standard_type documentada explícitamente.", "No confundir promiscuidad con potencia (pchembl)."], artifact: "activities_clean.csv", code: [{ title: "Conteo de dianas", lang: "python", code: "promisc = act.groupby('canonical_smiles')['target_chembl_id'].nunique()\npromisc.sort_values(ascending=False).head(10)" }] } },
      { id: "f3-6", type: "output", icon: "file", tag: "Salida", title: "Figuras", stat: "P1 · P2", detail: { title: "Artefactos EDA exportados", summary: "Figuras estáticas + JSON que alimentan prepare_dashboard.py.", bullets: ["outputs/chembl/figures/*.png", "Hallazgos narrados en informe IEEE.", "correlation_pearson.json → dashboard /dashboard."], visual: "charts", artifact: "outputs/chembl/figures/", code: [{ title: "Preparar dashboard", lang: "bash", code: "python scripts/fase5/prepare_dashboard.py" }] } },
    ],
  },
  4: {
    overview: {
      icon: "cluster",
      title: "Desglose completo — Fase 4: Modelado",
      summary: "PCA + clustering, contrastes de hipótesis y baseline RF con validación honesta por compuesto.",
      bullets: ["147 × 7 descriptores escalados (StandardScaler).", "Kruskal–Wallis + corrección Benjamini–Hochberg.", "RF: comparación filas (fuga) vs split por compuesto."],
      visual: "tree",
      code: [{ title: "Notebook", lang: "bash", code: "jupyter notebooks/fase4_modelado.ipynb" }],
    },
    steps: [
      { id: "f4-1", type: "source", icon: "file", tag: "Entrada", title: "147 × 7", stat: "Scaled", detail: { title: "Matriz de features escalada", summary: "StandardScaler sobre 7 descriptores; excluye num_ro5_violations (varianza nula).", bullets: ["Unidad de análisis: compuesto, no fila de medición.", "Entrada común para PCA, K-means y RF.", "Split honesto agrupa por canonical_smiles."], artifact: "compounds_all.csv", code: [{ title: "Escalado", lang: "python", code: "FEATURES = ['mw','alogp','psa','hba','hbd','aromatic_rings','rtb']\nX = StandardScaler().fit_transform(df[FEATURES])" }] } },
      { id: "f4-2", type: "process", icon: "cluster", tag: "P3", title: "PCA + K-means", stat: "ARI 0.018", detail: { title: "Agrupamiento exploratorio (P3)", summary: "78.2% varianza en 2 componentes; clusters no replican familias químicas.", bullets: ["Silueta = 0.36 con k=2.", "ARI vs family ≈ 0.018 → solapamiento estructural.", "Exporta clustering_summary.json al dashboard."], visual: "tree", artifact: "clustering_summary.json", code: [{ title: "PCA + K-means", lang: "python", code: "pca = PCA(n_components=2).fit_transform(X)\nlabels = KMeans(n_clusters=2, random_state=42).fit_predict(X)\nari = adjusted_rand_score(df['family'], labels)" }] } },
      { id: "f4-3", type: "process", icon: "test", tag: "P4", title: "Kruskal", stat: "6/7 sig.", detail: { title: "Kruskal–Wallis por familia (P4)", summary: "¿Las familias difieren en distribución de descriptores?", bullets: ["Corrección Benjamini–Hochberg (FDR).", "ε² máximo en alogp (0.203) — efecto moderado.", "Post-hoc Dunn cuando FDR < 0.05."], visual: "tree", artifact: "stats_tests.csv", code: [{ title: "Test no paramétrico", lang: "python", code: "from scipy.stats import kruskal\nH, p = kruskal(*[g['alogp'] for _, g in df.groupby('family')])\n# + multipletests(pvals, method='fdr_bh')" }] } },
      { id: "f4-4", type: "process", icon: "ml", tag: "P6", title: "RF baseline", stat: "3 CV splits", detail: { title: "Random Forest — validación honesta (P6)", summary: "Mismo modelo, tres esquemas de split para demostrar data leakage.", bullets: ["Split por filas (fuga): R² ≈ +0.44 — optimista.", "Split por grupos de scaffold: R² ≈ −0.23.", "Split por compuesto: R² ≈ −0.52 — estimación honesta."], visual: "tree", artifact: "baseline_honest_metrics.csv", metrics: [{ label: "Filas (fuga)", value: "R² +0.44" }, { label: "Grupos", value: "R² −0.23" }, { label: "Compuesto", value: "R² −0.52" }], sections: [{ title: "Lección clave", body: "Con solo 147 compuestos y 7 descriptores, RF no generaliza; motiva el proyecto GNN en el repo principal." }], code: [{ title: "GroupKFold por compuesto", lang: "python", code: "from sklearn.model_selection import GroupKFold\ngkf = GroupKFold(n_splits=3)\nfor train, test in gkf.split(X, y, groups=df['canonical_smiles']):\n    rf.fit(X[train], y[train])\n    r2 = rf.score(X[test], y[test])" }] } },
      { id: "f4-5", type: "output", icon: "file", tag: "Salida", title: "JSON + CSV", stat: "→ Fase 5", detail: { title: "Resultados exportados", summary: "Artefactos consumidos por dashboard y esta presentación.", bullets: ["pca_scatter.png, dendrograma, silueta.", "baseline_honest.json en /api/analytics.", "Documenta límite de QSAR clásico con descriptores."], visual: "tree", artifact: "outputs/chembl/results/", code: [{ title: "Verificar flujo B", lang: "bash", code: "python scripts/fase4/verify_flow_b.py" }] } },
    ],
  },
  5: {
    overview: {
      icon: "cloud",
      title: "Desglose completo — Fase 5: Dashboard",
      summary: "Publicar artefactos precomputados como aplicación web interactiva (entregable 2 del curso).",
      bullets: ["≥4 gráficas Plotly + ≥2 controladores (variable, familia, MW).", "Sin ChEMBL en producción — solo JSON/CSV en bundle.", "Despliegue continuo en Render vía git push."],
      visual: "deploy",
      code: [{ title: "Build + servir local", lang: "bash", code: "make analisis-prepare-dashboard-bundle\nmake analisis-viz   # http://localhost:8000" }],
    },
    steps: [
      { id: "f5-1", type: "source", icon: "file", tag: "Entradas", title: "CSVs + JSON", stat: "Fases 2–4", detail: { title: "Fuentes del build estático", summary: "Todo lo generado localmente por el pipeline; el servidor no recalcula estadísticas.", bullets: ["compounds_*.csv, activities_clean.csv.", "clustering_summary, stats_tests, baseline.", "Figuras PNG opcionales en bundle."], artifact: "outputs/dashboard/", code: [{ title: "Estructura bundle", lang: "text", code: "outputs/dashboard/\n  compounds_all.csv\n  correlation_pearson.json\n  clustering_summary.json\n  baseline_honest.json" }] } },
      { id: "f5-2", type: "process", icon: "script", tag: "Build", title: "prepare_dash", stat: "JSON bundle", detail: { title: "prepare_dashboard.py", summary: "Genera JSON estáticos para Plotly y copia CSVs necesarios para Render.", bullets: ["correlation, pca_clusters, family_stats.", "manifest.json con checksums.", "Copia CSVs a outputs/dashboard/."], visual: "deploy", artifact: "scripts/fase5/prepare_dashboard.py", code: [{ title: "Ejecutar build", lang: "bash", code: "python scripts/fase5/prepare_dashboard.py\n# Makefile: make analisis-prepare-dashboard-bundle" }] } },
      { id: "f5-3", type: "infra", icon: "api", tag: "Backend", title: "FastAPI", stat: "Cache MD5", detail: { title: "API analytics con caché", summary: "Sirve artefactos JSON/CSV con invalidación por checksum MD5 del archivo.", bullets: ["Rutas: /api/analytics/chembl/*", "/health para healthcheck de Render.", "resolve_path: processed → dashboard → bundle."], artifact: "viz/routes/analytics.py", code: [{ title: "Resolución de rutas", lang: "python", code: "# viz/config.py\n# 1. data/processed/\n# 2. outputs/dashboard/\n# 3. outputs/dashboard/bundle/" }] } },
      { id: "f5-4", type: "viz", icon: "browser", tag: "Frontend", title: "Plotly.js", stat: "4+ gráficos", detail: { title: "UI interactiva Jinja2 + JS", summary: "Templates server-side; gráficos client-side con Plotly CDN.", bullets: ["/dashboard — selector variable, familia, rango MW.", "/presentacion — este deck de slides.", "Controles reactivos sin recargar página."], visual: "charts", artifact: "viz/static/js/dashboard.js", code: [{ title: "Fetch + render", lang: "javascript", code: "const res = await fetch('/api/analytics/chembl/correlation');\nconst data = await res.json();\nPlotly.newPlot('chart-correlation', data.data, data.layout);" }] } },
      { id: "f5-5", type: "infra", icon: "cloud", tag: "Deploy", title: "Render", stat: "uvicorn", detail: { title: "Publicación HTTPS en Render", summary: "Web service Python con PORT dinámico asignado por la plataforma.", bullets: ["git push → rebuild automático.", "Dockerfile incluye outputs/dashboard/.", "Sin volumen ChEMBL en producción."], visual: "deploy", artifact: "render.com", code: [{ title: "Comando start (Render)", lang: "bash", code: "uvicorn viz.main:app --host 0.0.0.0 --port $PORT" }] } },
      { id: "f5-6", type: "output", icon: "globe", tag: "Live", title: "URLs", stat: "/dashboard", detail: { title: "Dashboard público en producción", summary: "URLs para evaluación del curso y video explicativo del proyecto.", bullets: ["/dashboard — exploración interactiva.", "/presentacion — slides del pipeline.", "Enlace en informe IEEE y README."], visual: "deploy", artifact: "/health", code: [{ title: "Healthcheck", lang: "bash", code: "curl https://tu-app.onrender.com/health\n# → {\"status\": \"ok\"}" }] } },
    ],
  },
};

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Serpentina secuencial + jitter estable por fase (orden 1→N legible) */
function seededRandom(seed) {
  let s = Math.max(1, seed | 0);
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

/** Flujo horizontal: X fijo secuencial, solo Y aleatorio dentro de zona segura */
const PIPE_SAFE = { left: 10, right: 10, top: 38, bottom: 38 };

function computeSequentialPositions(count, phaseId) {
  const rand = seededRandom(phaseId * 7919 + count * 131);
  const xSpan = 100 - PIPE_SAFE.left - PIPE_SAFE.right;
  const yMin = PIPE_SAFE.top;
  const yMax = 100 - PIPE_SAFE.bottom;
  const positions = [];

  for (let i = 0; i < count; i += 1) {
    const x =
      count === 1
        ? PIPE_SAFE.left + xSpan / 2
        : PIPE_SAFE.left + (i / (count - 1)) * xSpan;
    const y = yMin + rand() * (yMax - yMin);

    positions.push({ x, y, r: 0, step: i + 1 });
  }
  return positions;
}

function renderSequentialConnectors(positions, phaseId) {
  if (positions.length < 2) return "";
  const uid = `pipe-${phaseId}`;
  const inset = 2;
  const paths = positions.slice(0, -1).map((a, i) => {
    const b = positions[i + 1];
    const midY = (a.y + b.y) / 2;
    const d = `M ${a.x} ${a.y} C ${a.x + inset} ${a.y}, ${b.x - inset} ${b.y}, ${b.x} ${b.y}`;
    const dAlt = `M ${a.x} ${a.y} L ${a.x} ${midY} L ${b.x} ${midY} L ${b.x} ${b.y}`;
    return `<path class="pipe-flow-path" d="${dAlt}" marker-end="url(#${uid}-arrow)" data-d="${i}"/>
            <circle class="pipe-flow-dot" r="0.55" data-d="${i}">
              <animateMotion dur="2.4s" repeatCount="indefinite" begin="${i * 0.35}s" path="${dAlt}"/>
            </circle>`;
  });
  return `<svg class="pipe-scatter-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <marker id="${uid}-arrow" markerWidth="4" markerHeight="4" refX="3.2" refY="2" orient="auto">
        <path d="M0,0 L4,2 L0,4 Z" fill="rgba(96,165,250,0.85)"/>
      </marker>
    </defs>
    ${paths.join("")}
  </svg>`;
}

function renderPipeStep(step, index, pos) {
  const icon = PIPE_ICONS[step.icon] || PIPE_ICONS.file;
  const hint = step.detail?.summary || "";
  const stepNum = pos.step ?? index + 1;
  return `
    <div class="pipe-flow-slot" style="--y:${pos.y}%">
      <button type="button" class="pipe-node pipe-node--card pipe-node--flow pipe-node--${step.type}"
              style="--d:${index}"
              data-step-id="${step.id}" data-step-order="${stepNum}" aria-expanded="false"
              aria-label="Paso ${stepNum}: ${step.title}. ${step.stat}. Clic para desglose">
        <span class="node-step-badge" aria-hidden="true">${stepNum}</span>
        <span class="node-icon">${icon}</span>
        <span class="node-tag">${step.tag}</span>
        <strong class="node-title">${step.title}</strong>
        ${hint ? `<span class="node-hint">${hint}</span>` : ""}
        <span class="node-stat">${step.stat}</span>
      </button>
    </div>`;
}

function mountPhaseDiagram(phaseId) {
  const mount = document.querySelector(`[data-phase-mount="${phaseId}"]`);
  if (!mount || mount.dataset.mounted) return;
  const phase = PIPE_PHASES[phaseId];
  if (!phase) return;

  const positions = computeSequentialPositions(phase.steps.length, Number(phaseId));
  const parts = phase.steps.map((step, i) => renderPipeStep(step, i, positions[i]));

  mount.innerHTML = `
    <div class="pipe-diagram-flow pipe-diagram-flow--horizontal">
      <div class="pipe-safe-zone" aria-hidden="true"></div>
      ${renderSequentialConnectors(positions, phaseId)}
      <div class="pipe-flow-track">${parts.join("")}</div>
    </div>`;
  mount.dataset.mounted = "1";
}

function findStep(phaseId, stepId) {
  return PIPE_PHASES[phaseId]?.steps.find((s) => s.id === stepId);
}

function renderIoChips(io) {
  if (!io) return "";
  const parts = [];
  if (io.input) parts.push(`<span class="pipe-io pipe-io--in"><em>Entrada</em> ${io.input}</span>`);
  if (io.output) parts.push(`<span class="pipe-io pipe-io--out"><em>Salida</em> ${io.output}</span>`);
  return parts.length ? `<div class="pipe-io-row">${parts.join("")}</div>` : "";
}

function renderCodeBlocks(blocks) {
  if (!blocks?.length) return "";
  return blocks
    .map(
      (b) => `
    <div class="pipe-code-block">
      <div class="pipe-code-header">
        <span class="pipe-code-lang">${b.lang || "code"}</span>
        <span class="pipe-code-title">${b.title}</span>
      </div>
      <pre class="pipe-code-pre"><code>${escapeHtml(b.code)}</code></pre>
    </div>`
    )
    .join("");
}

function renderMetricCards(metrics) {
  if (!metrics?.length) return "";
  return `<div class="pipe-metrics-row">${metrics
    .map(
      (m) => `
      <div class="pipe-metric-card">
        <span class="pipe-metric-value">${m.value}</span>
        <span class="pipe-metric-label">${m.label}</span>
      </div>`
    )
    .join("")}</div>`;
}

function renderConcepts(concepts) {
  if (!concepts?.length) return "";
  return `<div class="pipe-slide-card pipe-slide-card--concepts">
    <h4 class="pipe-block-title">Conceptos importantes</h4>
    <dl class="pipe-concept-list">
      ${concepts.map((c) => `<dt>${c.term}</dt><dd>${c.def}</dd>`).join("")}
    </dl>
  </div>`;
}

function renderProcessSteps(steps) {
  if (!steps?.length) return "";
  return `<div class="pipe-slide-card pipe-slide-card--process">
    <h4 class="pipe-block-title">Proceso</h4>
    <ol class="pipe-process-list">${steps.map((s) => `<li>${s}</li>`).join("")}</ol>
  </div>`;
}

function renderVisualPanel(detail) {
  const parts = [];
  if (detail.illus) {
    const cap = detail.imageCaption || "Referencia visual del paso";
    const label = escapeHtml(detail.title || "Ilustración del paso");
    parts.push(`
      <figure class="pipe-slide-media">
        <div class="pipe-slide-illus" data-illus="${detail.illus}" role="img" aria-label="${label}"></div>
        <figcaption>${cap}</figcaption>
      </figure>`);
  }
  if (detail.visual && PIPE_VISUALS[detail.visual]) {
    parts.push(`<div class="pipe-slide-diagram">${PIPE_VISUALS[detail.visual]}</div>`);
  }
  if (!parts.length) return "";
  return `<div class="pipe-slide-card pipe-slide-card--media">${parts.join("")}</div>`;
}

function renderDetailContent(detail, step, meta = {}) {
  const metrics = renderMetricCards(
    detail.metrics ||
      (meta.stat ? [{ label: "Indicador", value: meta.stat }] : [])
  );
  const artifact = detail.artifact
    ? `<div class="pipe-slide-card pipe-slide-card--artifact">
        <h4 class="pipe-block-title">Artefacto</h4>
        <code>${detail.artifact}</code>
      </div>`
    : "";
  const bullets = (detail.bullets || []).map((b) => `<li>${b}</li>`).join("");
  const bulletsBlock = bullets
    ? `<div class="pipe-slide-card">
        <h4 class="pipe-block-title">Puntos clave</h4>
        <ul class="pipe-detail-list">${bullets}</ul>
      </div>`
    : "";
  const sectionsBlock = (detail.sections || [])
    .map(
      (s) => `
      <div class="pipe-slide-card">
        <h4 class="pipe-section-title">${s.title}</h4>
        <p class="pipe-section-body">${s.body}</p>
      </div>`
    )
    .join("");
  const codeBlock = detail.code?.length
    ? `<div class="pipe-slide-card pipe-slide-card--code">${renderCodeBlocks(detail.code)}</div>`
    : "";
  const stepBadge = meta.stepOrder
    ? `<span class="pipe-slide-step">Paso ${meta.stepOrder}</span>`
    : `<span class="pipe-slide-step pipe-slide-step--overview">Resumen fase</span>`;

  return `
    <div class="pipe-detail-inner pipe-detail-slide">
      <header class="pipe-slide-header">
        <div class="pipe-slide-header-main">
          ${stepBadge}
          <div class="pipe-slide-title-row">
            <span class="node-icon pipe-detail-icon">${PIPE_ICONS[step.icon] || ""}</span>
            <div>
              <h3 id="pipe-modal-title">${detail.title}</h3>
              <p class="pipe-detail-summary">${detail.summary}</p>
            </div>
          </div>
          ${renderIoChips(detail.io)}
          ${metrics}
        </div>
      </header>
      <div class="pipe-slide-grid">
        <div class="pipe-slide-col pipe-slide-col--text">
          ${renderConcepts(detail.concepts)}
          ${renderProcessSteps(detail.process)}
          ${sectionsBlock}
          ${bulletsBlock}
        </div>
        <div class="pipe-slide-col pipe-slide-col--media">
          ${renderVisualPanel(detail)}
          ${codeBlock}
          ${artifact}
        </div>
      </div>
    </div>`;
}

let _modalPhaseId = null;
let _modalStepId = null;

function getModal() {
  return document.getElementById("pipe-modal");
}

function clearNodeSelection() {
  document.querySelectorAll(".pipe-node.is-selected").forEach((n) => {
    n.classList.remove("is-selected");
    n.setAttribute("aria-expanded", "false");
  });
}

function openPipeModal(phaseId, payload, stepEl) {
  const modal = getModal();
  const body = document.getElementById("pipe-modal-body");
  if (!modal || !body) return;

  clearNodeSelection();
  if (stepEl) {
    stepEl.classList.add("is-selected");
    stepEl.setAttribute("aria-expanded", "true");
    _modalStepId = stepEl.dataset.stepId;
  } else {
    _modalStepId = null;
  }
  _modalPhaseId = phaseId;

  const step = stepEl ? findStep(phaseId, stepEl.dataset.stepId) : null;
  let detail = payload || (step && step.detail);
  if (!detail) return;

  detail = enrichDetail(detail, {
    stepId: step?.id,
    phaseId,
    isOverview: !stepEl && !!payload,
  });

  const iconKey = step?.icon || payload?.icon || "file";
  const stepOrder = stepEl?.dataset.stepOrder ? Number(stepEl.dataset.stepOrder) : null;
  body.innerHTML = renderDetailContent(
    detail,
    { icon: iconKey },
    { stepOrder, stat: step?.stat }
  );
  hydratePipeIllustrations(body);

  modal.hidden = false;
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("pipe-modal-open");
  modal.querySelector(".pipe-modal-close")?.focus();
}

function closePipeModal() {
  const modal = getModal();
  if (!modal) return;

  modal.classList.remove("is-open");
  modal.hidden = true;
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("pipe-modal-open");
  document.getElementById("pipe-modal-body").innerHTML = "";
  clearNodeSelection();
  _modalPhaseId = null;
  _modalStepId = null;
}

function showPhaseDetail(phaseId, payload, stepEl) {
  const modal = getModal();
  if (modal?.classList.contains("is-open") && _modalPhaseId === phaseId) {
    if (stepEl && _modalStepId === stepEl.dataset.stepId) {
      closePipeModal();
      return;
    }
    if (!stepEl && !_modalStepId && payload) {
      closePipeModal();
      return;
    }
  }
  openPipeModal(phaseId, payload, stepEl);
}

function initPipePhases() {
  Object.keys(PIPE_PHASES).forEach((id) => mountPhaseDiagram(id));
  prefetchPipeIllustrations();

  const modal = getModal();
  modal?.querySelector(".pipe-modal-backdrop")?.addEventListener("click", closePipeModal);
  modal?.querySelector(".pipe-modal-close")?.addEventListener("click", closePipeModal);

  document.querySelectorAll(".slide-phase").forEach((slide) => {
    const phaseId = slide.dataset.phase;
    if (!phaseId) return;

    slide.querySelector(".phase-overview-btn")?.addEventListener("click", (e) => {
      e.stopPropagation();
      showPhaseDetail(phaseId, PIPE_PHASES[phaseId].overview, null);
    });

    slide.addEventListener("click", (e) => {
      const node = e.target.closest(".pipe-node");
      if (!node || !slide.contains(node)) return;
      e.stopPropagation();
      e.preventDefault();
      showPhaseDetail(phaseId, null, node);
    });
  });
}

window.initPipePhases = initPipePhases;
window.closeAllPhaseDetails = closePipeModal;
window.isPipeModalOpen = () => getModal()?.classList.contains("is-open");
