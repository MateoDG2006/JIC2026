// ============================================================================
//  Dashboard SPA — router + vistas (Adquisición · Exploración · …)
// ============================================================================
const PLOT_LAYOUT = {
  paper_bgcolor: "#1a2332", plot_bgcolor: "#1a2332",
  font: { color: "#e8edf4", size: 12 }, margin: { l: 55, r: 20, t: 40, b: 55 },
};
const PLOT_CFG = { responsive: true, displayModeBar: false };

const VIEW_META = {
  adquisicion: ["Adquisición y extracción", "De 235 candidatos de PubChem a un corpus trazable de bioactividad"],
  limpieza: ["Limpieza y transformación", "Deduplicación, columnas con muchos NaN, censura e imputación"],
  exploracion: ["Exploración de datos", "Distribuciones, correlaciones y comparación de variables (nivel compuesto)"],
  multivariado: ["Análisis multivariado", "PCA, clustering y contraste de hipótesis por familia"],
  modelado: ["Modelado y predictor", "Métricas de cada modelo y predicción interactiva"],
};

const initialized = {};
let dbCompoundCombo = null;
let predCompoundCombo = null;

// ── Router ──────────────────────────────────────────────────────────────────
function showView(name) {
  document.querySelectorAll(".spa-navbtn").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  const view = document.querySelector(`.view[data-view="${name}"]`);
  if (!view) return;
  // reflow para reiniciar la animación fade
  view.classList.remove("active"); void view.offsetWidth; view.classList.add("active");
  const [title, sub] = VIEW_META[name] || [name, ""];
  document.getElementById("view-title").textContent = title;
  document.getElementById("view-sub").textContent = sub;
  if (!initialized[name]) { initialized[name] = true; (INIT[name] || (() => {}))(); }
  // Plotly necesita resize al mostrarse
  setTimeout(() => view.querySelectorAll(".js-plotly-plot").forEach((p) => Plotly.Plots.resize(p)), 60);
}

// ── Helpers estadísticos ──────────────────────────────────────────────────────
function pearson(xs, ys) {
  const pairs = xs.map((x, i) => [x, ys[i]]).filter(([a, b]) => a != null && b != null && isFinite(a) && isFinite(b));
  const n = pairs.length; if (n < 3) return NaN;
  const mx = pairs.reduce((s, p) => s + p[0], 0) / n, my = pairs.reduce((s, p) => s + p[1], 0) / n;
  let sxy = 0, sx = 0, sy = 0;
  pairs.forEach(([a, b]) => { sxy += (a - mx) * (b - my); sx += (a - mx) ** 2; sy += (b - my) ** 2; });
  return (sx && sy) ? sxy / Math.sqrt(sx * sy) : NaN;
}

function solve(A, b) { // Gauss para sistema pequeño
  const n = b.length, M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    if (Math.abs(M[c][c]) < 1e-12) return null;
    for (let r = 0; r < n; r++) if (r !== c) { const f = M[r][c] / M[c][c]; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  return M.map((r, i) => r[n] / r[i][i] === undefined ? r[n] / M[i][i] : r[n] / M[i][i]);
}

function polyfit(xs, ys, deg) {
  const n = deg + 1, A = Array.from({ length: n }, () => new Array(n).fill(0)), b = new Array(n).fill(0);
  for (let i = 0; i < xs.length; i++) {
    const pows = []; for (let p = 0; p < 2 * deg + 1; p++) pows.push(p === 0 ? 1 : pows[p - 1] * xs[i]);
    for (let r = 0; r < n; r++) { for (let c = 0; c < n; c++) A[r][c] += pows[r + c]; b[r] += pows[r] * ys[i]; }
  }
  return solve(A, b); // coef [c0, c1, c2...]
}

function r2(ys, yhat) {
  const my = ys.reduce((s, v) => s + v, 0) / ys.length;
  let ssr = 0, sst = 0;
  ys.forEach((v, i) => { ssr += (v - yhat[i]) ** 2; sst += (v - my) ** 2; });
  return sst ? 1 - ssr / sst : NaN;
}

function cleanPairs(xs, ys) {
  const p = xs.map((x, i) => [x, ys[i]]).filter(([a, b]) => a != null && b != null && isFinite(a) && isFinite(b));
  return [p.map((q) => q[0]), p.map((q) => q[1])];
}

// ── Vista Adquisición ─────────────────────────────────────────────────────────
async function initAdquisicion() {
  await loadGlossary();
  let d;
  try { d = await (await fetch("/api/analytics/acquisition")).json(); } catch (e) { return; }
  const f = d.funnel || {}, res = d.resolution || {};
  const ok = (res.by_status && res.by_status.ok) || 0;
  const metrics = [
    [235, "Candidatos PubChem"], [ok, "Resueltos a ChEMBL"],
    [(d.n_measurements || 0).toLocaleString("es"), "Mediciones"],
    [f.raw_compounds ?? "—", "Compuestos estructurales"],
    [f.with_potency_binding_min_support ?? "—", "Con potencia útil"],
    [d.n_targets ?? "—", "Dianas distintas"],
  ];
  document.getElementById("acq-metrics").innerHTML = metrics
    .map(([v, l]) => `<div class="metric-tile"><div class="val">${v}</div><div class="lbl">${l}</div></div>`).join("");

  const steps = [["Candidatos PubChem", 235], ["Resueltos a ChEMBL", ok],
    ["Compuestos estructurales", f.raw_compounds || 0], ["Con potencia útil (≥3)", f.with_potency_binding_min_support || 0]];
  const mx = Math.max(...steps.map((s) => s[1]), 1);
  document.getElementById("acq-funnel").innerHTML = steps.map(([l, v]) =>
    `<div class="fb"><span class="fl">${l}</span><div class="track"><div class="bar" style="width:${Math.max(8, 100 * v / mx)}%">${v}</div></div></div>`).join("");
  if (f.dropped_no_quantitative != null)
    document.getElementById("acq-funnel-note").textContent =
      `Se pierden ${f.dropped_no_quantitative} compuestos sin potencia útil. ${f.selection_bias_note || ""}`;

  const METHOD_ES = { known_registry: "Registro curado (MIDA)", sqlite_smiles: "Por estructura (SMILES)",
    sqlite_pref_name: "Por nombre", sqlite_synonym: "Por sinónimo", not_found: "No encontrado en ChEMBL" };
  const bm = res.by_method || {}, tot = res.total || 1;
  document.getElementById("acq-resolution").innerHTML =
    `<div class="table-scroll"><table class="data-table"><thead><tr><th>Método</th><th>Compuestos</th><th>%</th></tr></thead><tbody>`
    + Object.entries(bm).sort((a, b) => b[1] - a[1]).map(([k, v]) =>
      `<tr><td>${METHOD_ES[k] || k}</td><td>${v}</td><td>${(100 * v / tot).toFixed(1)}%</td></tr>`).join("")
    + `</tbody></table></div>`;

  // Visor de BD real
  try {
    const list = (await (await fetch("/api/analytics/compounds-list")).json()).compounds || [];
    dbCompoundCombo = setupComboBox(document.getElementById("db-query-combo"), list.filter((c) => c.compound_name), {
      placeholder: "Ej: Atrazine o CHEMBL15063",
      getLabel: (item) => item.compound_name,
      getValue: (item) => item.compound_name,
      getMeta: (item) => {
        const bits = [];
        if (item.chembl_id) bits.push(`<span class="pill neutral">${esc(item.chembl_id)}</span>`);
        if (item.family) bits.push(`<span class="pill good">${esc(item.family)}</span>`);
        return bits.join("");
      },
    });
  } catch (e) {}
  const runSearch = async () => {
    const q = dbCompoundCombo ? dbCompoundCombo.getValue() : "";
    if (!q) return;
    const limitInput = document.getElementById("db-limit");
    const limit = Math.max(1, parseInt(limitInput?.value || "10", 10) || 10);
    if (limitInput) limitInput.value = String(limit);
    const r = await (await fetch(`/api/analytics/compound-search?q=${encodeURIComponent(q)}`)).json();
    const shown = Math.min(limit, (r.rows || []).length);
    document.getElementById("db-count").textContent = `${r.count} mediciones · mostrando ${shown}${r.truncated ? " de 500 cargadas" : ""}`;
    if (!r.rows.length) { document.getElementById("db-result").innerHTML = "<p>Sin resultados en la base real.</p>"; return; }
    renderDataTable(document.getElementById("db-result"), r.columns, r.rows.slice(0, limit));
    renderGlossary(document.getElementById("db-glossary"), r.columns.filter((c) => window.Glossary.columns[c]), "Diccionario de columnas");
  };
  document.getElementById("db-search").addEventListener("click", runSearch);
  document.getElementById("db-limit").addEventListener("change", runSearch);
  if (dbCompoundCombo) {
    dbCompoundCombo.input.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
    dbCompoundCombo.setValue("Atrazine");
  }
  runSearch();
}

// ── Vista Limpieza ───────────────────────────────────────────────────────────
async function initLimpieza() {
  await loadGlossary();
  let d;
  try { d = await (await fetch("/api/analytics/cleaning")).json(); } catch (e) { return; }
  const body = document.getElementById("clean-body");
  const dropped = d.dropped_columns || [];
  const censor = d.censoring || {};
  const censorRows = Object.entries(censor).filter(([k, v]) => typeof v !== "object" && v != null);

  body.innerHTML = `
    <div class="phase-intro">
      La limpieza elimina redundancias y columnas inviables, separa mediciones censuradas y deja un conjunto usable para EDA, clustering y modelado.
    </div>
    <div class="card">
      <h2>Resumen del proceso</h2>
      <div class="metric-row" id="clean-metrics"></div>
    </div>
    <div class="card">
      <h2>Columnas descartadas por faltantes</h2>
      <p class="muted">Se muestran las columnas que quedaron fuera del dataset limpio porque no sobrevivieron al umbral aplicado o no son útiles después de la depuración.</p>
      <div id="clean-dropped"></div>
    </div>
    <div class="card">
      <h2>Censura e imputación</h2>
      <div class="side-by-side">
        <div id="clean-censor-table"></div>
        <div class="fit-box" id="clean-notes"></div>
      </div>
    </div>
  `;

  const metrics = [
    [d.raw_rows ?? "—", "Filas crudas"],
    [d.clean_rows ?? "—", "Filas limpias"],
    [d.rows_removed_total ?? "—", "Filas removidas"],
    [d.dedup_removed ?? "—", "Duplicados potenciales"],
    [d.raw_cols ?? "—", "Columnas originales"],
    [d.clean_cols ?? "—", "Columnas finales"],
    [d.imputed ?? "—", "pChEMBL imputados"],
  ];
  document.getElementById("clean-metrics").innerHTML = metrics
    .map(([v, l]) => `<div class="metric-tile"><div class="val">${v}</div><div class="lbl">${l}</div></div>`)
    .join("");

  const droppedRows = dropped.length ? dropped.map((r) =>
    `<tr><td>${colLabel(r.column)}</td><td class="mono muted">${esc(r.column)}</td><td>${r.nan}</td><td>${r.pct}%</td></tr>`).join("")
    : `<tr><td colspan="4">No hubo columnas descartadas registradas.</td></tr>`;
  document.getElementById("clean-dropped").innerHTML = `
    <div class="table-scroll table-scroll-y">
      <table class="data-table">
        <thead><tr><th>Columna</th><th>Código</th><th>NaN</th><th>% faltante</th></tr></thead>
        <tbody>${droppedRows}</tbody>
      </table>
    </div>`;

  const censorTableRows = censorRows.length ? censorRows.map(([k, v]) =>
    `<tr><td>${esc(k)}</td><td>${typeof v === "number" ? v.toLocaleString("es") : esc(v)}</td></tr>`).join("")
    : `<tr><td colspan="2">No hay reporte de censura disponible.</td></tr>`;
  document.getElementById("clean-censor-table").innerHTML = `
    <div class="table-scroll">
      <table class="data-table">
        <thead><tr><th>Métrica</th><th>Valor</th></tr></thead>
        <tbody>${censorTableRows}</tbody>
      </table>
    </div>`;
  document.getElementById("clean-notes").innerHTML = `
    <p><span class="pill warn">Umbral NaN</span> Se trabajó con un corte de <strong>${d.threshold}</strong> faltantes para depurar columnas problemáticas.</p>
    <p><span class="pill neutral">Censura</span> Las relaciones distintas de <span class="mono">=</span> se separan de la potencia cuantitativa para no mezclar límites con medidas exactas.</p>
    <p><span class="pill good">Imputación</span> Hay <strong>${d.imputed}</strong> valores de pChEMBL recalculados desde el valor/unidad original cuando eso fue posible.</p>
  `;
}

// ── Vista Exploración ─────────────────────────────────────────────────────────
let EDA = null;
async function initExploracion() {
  await loadGlossary();
  EDA = await (await fetch("/api/analytics/dashboard/dataset")).json();
  const cols = EDA.numeric_cols;
  const opt = (c) => `<option value="${c}">${colLabel(c)}</option>`;
  document.getElementById("eda-variable").innerHTML = cols.map(opt).join("");
  document.getElementById("eda-variable").value = cols.includes("pchembl_median_binding") ? "pchembl_median_binding" : cols[0];
  document.getElementById("eda-family").innerHTML = `<option value="ALL">Todas</option>` + EDA.families.map((f) => `<option>${f}</option>`).join("");
  document.getElementById("xy-x").innerHTML = cols.map(opt).join("");
  document.getElementById("xy-y").innerHTML = cols.map(opt).join("");

  document.getElementById("eda-variable").addEventListener("change", renderDist);
  document.getElementById("eda-family").addEventListener("change", renderDist);
  document.getElementById("xy-x").addEventListener("change", renderXY);
  document.getElementById("xy-y").addEventListener("change", renderXY);

  renderDist();
  renderCorr();      // también fija el par más fuerte en XY
}

function edaRows() {
  const fam = document.getElementById("eda-family").value;
  return fam === "ALL" ? EDA.rows : EDA.rows.filter((r) => r.family === fam);
}

function renderDist() {
  const v = document.getElementById("eda-variable").value;
  const rows = edaRows();
  const vals = rows.map((r) => r[v]).filter((x) => x != null && isFinite(x));
  // Histograma con conteo sobre cada barra
  const n = 18, min = Math.min(...vals), max = Math.max(...vals);
  let centers, counts, width;
  if (min === max) { centers = [min]; counts = [vals.length]; width = 1; }
  else {
    width = (max - min) / n; counts = new Array(n).fill(0);
    vals.forEach((x) => { let i = Math.floor((x - min) / width); i = Math.max(0, Math.min(n - 1, i)); counts[i]++; });
    centers = counts.map((_, i) => min + width * (i + 0.5));
  }
  Plotly.newPlot("chart-hist", [{
    x: centers, y: counts, type: "bar", width: width * 0.92, marker: { color: "#40916c" },
    text: counts.map((c) => c || ""), textposition: "outside", textfont: { size: 10 },
    hovertemplate: `${colLabel(v)}: %{x:.2f}<br>%{y} compuestos<extra></extra>`,
  }], { ...PLOT_LAYOUT, title: `Distribución de ${colLabel(v)} (n=${vals.length})`,
    xaxis: { title: colLabel(v) }, yaxis: { title: "Nº de compuestos" } }, PLOT_CFG);

  // Boxplot por familia
  Plotly.newPlot("chart-box", [{
    x: rows.map((r) => r.family), y: rows.map((r) => r[v]), type: "box", marker: { color: "#3b82f6" }, boxpoints: "outliers",
  }], { ...PLOT_LAYOUT, title: `${colLabel(v)} por familia`, showlegend: false, yaxis: { title: colLabel(v) } }, PLOT_CFG);
}

function renderCorr() {
  const cols = EDA.numeric_cols;
  const M = cols.map((a) => cols.map((b) => {
    const r = pearson(EDA.rows.map((row) => row[a]), EDA.rows.map((row) => row[b]));
    return isFinite(r) ? +r.toFixed(2) : 0;
  }));
  const labels = cols.map(colLabel);
  Plotly.newPlot("chart-corr", [{
    z: M, x: labels, y: labels, type: "heatmap", colorscale: "RdBu", zmid: 0, zmin: -1, zmax: 1,
    text: M, texttemplate: "%{z:.2f}", textfont: { size: 9 },
    hovertemplate: "%{y} vs %{x}<br>r = %{z:.2f}<extra></extra>",
  }], { ...PLOT_LAYOUT, title: "Correlación de Pearson", margin: { l: 120, r: 20, t: 40, b: 120 },
    xaxis: { tickangle: -40 } }, PLOT_CFG);

  // Ranking de correlaciones más fuertes
  const pairs = [];
  for (let i = 0; i < cols.length; i++) for (let j = i + 1; j < cols.length; j++)
    pairs.push([cols[i], cols[j], M[i][j]]);
  pairs.sort((a, b) => Math.abs(b[2]) - Math.abs(a[2]));
  // Dropdown de correlaciones más fuertes (dentro de la comparación de variables)
  const sel = document.getElementById("corr-rank-select");
  sel.innerHTML = pairs.slice(0, 15).map(([a, b, r]) =>
    `<option value="${a}|${b}">${colLabel(a)} ↔ ${colLabel(b)}  (r=${r >= 0 ? "+" : ""}${r.toFixed(2)})</option>`).join("");
  sel.onchange = () => {
    const [a, b] = sel.value.split("|");
    document.getElementById("xy-x").value = a; document.getElementById("xy-y").value = b; renderXY();
  };
  if (pairs.length) {
    document.getElementById("xy-x").value = pairs[0][0];
    document.getElementById("xy-y").value = pairs[0][1];
    sel.value = `${pairs[0][0]}|${pairs[0][1]}`;
  }
  renderXY();
}

function renderXY() {
  const xv = document.getElementById("xy-x").value, yv = document.getElementById("xy-y").value;
  let [xs, ys] = cleanPairs(EDA.rows.map((r) => r[xv]), EDA.rows.map((r) => r[yv]));
  const traces = [{ x: xs, y: ys, mode: "markers", type: "scatter", name: "compuestos",
    marker: { color: "#22c55e", opacity: 0.6 } }];
  const fits = [];
  const xline = [...xs].sort((a, b) => a - b);
  // Lineal
  const c1 = polyfit(xs, ys, 1);
  if (c1) { const yh = xs.map((x) => c1[0] + c1[1] * x);
    traces.push({ x: xline, y: xline.map((x) => c1[0] + c1[1] * x), mode: "lines", name: "Lineal", line: { color: "#f59e0b" } });
    fits.push(["#f59e0b", "Lineal", `y = ${c1[1].toFixed(3)}·x ${c1[0] >= 0 ? "+" : "−"} ${Math.abs(c1[0]).toFixed(2)}`, r2(ys, yh)]); }
  // Cuadrática
  const c2 = polyfit(xs, ys, 2);
  if (c2) { const yh = xs.map((x) => c2[0] + c2[1] * x + c2[2] * x * x);
    traces.push({ x: xline, y: xline.map((x) => c2[0] + c2[1] * x + c2[2] * x * x), mode: "lines", name: "Cuadrática", line: { color: "#a855f7" } });
    fits.push(["#a855f7", "Cuadrática", `y = ${c2[2].toFixed(4)}·x² ${c2[1] >= 0 ? "+" : "−"} ${Math.abs(c2[1]).toFixed(3)}·x ${c2[0] >= 0 ? "+" : "−"} ${Math.abs(c2[0]).toFixed(2)}`, r2(ys, yh)]); }
  // Exponencial (solo y>0)
  const [ex, ey] = [[], []]; xs.forEach((x, i) => { if (ys[i] > 0) { ex.push(x); ey.push(Math.log(ys[i])); } });
  if (ex.length > 3) { const ce = polyfit(ex, ey, 1);
    if (ce) { const a = Math.exp(ce[0]), b = ce[1]; const yh = xs.map((x) => a * Math.exp(b * x));
      traces.push({ x: xline, y: xline.map((x) => a * Math.exp(b * x)), mode: "lines", name: "Exponencial", line: { color: "#ef4444", dash: "dot" } });
      fits.push(["#ef4444", "Exponencial", `y = ${a.toFixed(3)}·e^(${b.toFixed(3)}·x)`, r2(ys, yh)]); } }

  // R² sobre el gráfico, en el color de cada modelo
  const annotations = fits.map((ff, i) => ({
    xref: "paper", yref: "paper", x: 0.02, y: 0.98 - i * 0.075, xanchor: "left", yanchor: "top",
    text: `${ff[1]}: R² = ${isFinite(ff[3]) ? ff[3].toFixed(3) : "—"}`, showarrow: false,
    font: { color: ff[0], size: 12 }, bgcolor: "rgba(15,24,38,.65)", borderpad: 3,
  }));
  Plotly.newPlot("chart-xy", traces, { ...PLOT_LAYOUT, title: `${colLabel(xv)} vs ${colLabel(yv)}`,
    xaxis: { title: colLabel(xv) }, yaxis: { title: colLabel(yv) },
    legend: { orientation: "h", y: -0.25 }, annotations }, PLOT_CFG);

  const r = pearson(xs, ys);
  document.getElementById("xy-fits").innerHTML =
    `<p><strong>Pearson r = ${isFinite(r) ? r.toFixed(3) : "—"}</strong> (n=${xs.length})</p>`
    + `<p class="muted">Ecuaciones de cada modelo (R² también sobre el gráfico):</p>`
    + fits.sort((a, b) => b[3] - a[3]).map(([col, name, eq, rr]) =>
      `<div><span class="tag" style="background:${col}"></span><strong>${name}</strong> — R² = ${isFinite(rr) ? rr.toFixed(3) : "—"}<br><span class="mono muted">${eq}</span></div>`).join("");
}

// ── Vista Multivariado ─────────────────────────────────────────────────────────
async function initMultivariado() {
  await loadGlossary();
  let sweep, fam;
  try {
    [sweep, fam] = await Promise.all([
      fetch("/api/analytics/clusters/sweep").then((r) => r.json()),
      fetch("/api/analytics/families/stats").then((r) => r.json()),
    ]);
  } catch (e) { return; }
  const s = sweep.summary || {};
  const bestK = sweep.best_k || s.best_k || 2;
  const tiles = [
    [(100 * (s.pca_var_explained || 0)).toFixed(1) + "%", "Varianza en 2 componentes"],
    [(sweep.silhouette ? Math.max(...sweep.silhouette).toFixed(2) : (s.silhouette_best || 0).toFixed(2)), "Silueta (mejor k=" + bestK + ")"],
    [(s.ari_vs_family || 0).toFixed(3), "ARI clusters vs familia"],
  ];
  document.getElementById("mv-metrics").innerHTML = tiles
    .map(([v, l]) => `<div class="metric-tile"><div class="val">${v}</div><div class="lbl">${l}</div></div>`).join("");
  const kSel = document.getElementById("mv-k-select");
  kSel.innerHTML = (sweep.ks || []).map((k) => `<option value="${k}">${k} clusters</option>`).join("");
  kSel.value = String(bestK);
  const ev = sweep.explained_variance_ratio || [0, 0];
  const ks = sweep.ks || [];
  const inertia = sweep.inertia || [];
  const silhouettes = sweep.silhouette || [];

  function renderCurvePlots(selectedK) {
    const selectedIdx = ks.indexOf(selectedK);
    const bestIdx = ks.indexOf(bestK);

    Plotly.newPlot("chart-elbow", [
      { x: ks, y: inertia, mode: "lines+markers+text", type: "scatter", name: "Inercia",
        line: { color: "#3b82f6", width: 3 }, marker: { size: 9 },
        text: inertia.map((v) => v.toFixed(1)), textposition: "top center" },
      { x: [selectedK], y: [selectedIdx >= 0 ? inertia[selectedIdx] : null], mode: "markers", type: "scatter", name: "k seleccionado",
        marker: { color: "#f59e0b", size: 14, symbol: "diamond" } },
    ], { ...PLOT_LAYOUT, title: "Gráfica de codo (evaluación completa k=2..9)",
      xaxis: { title: "Número de clusters (k)" }, yaxis: { title: "Inercia" } }, PLOT_CFG);

    Plotly.newPlot("chart-knee", [
      { x: ks, y: silhouettes, mode: "lines+markers+text", type: "scatter", name: "Silueta",
        line: { color: "#22c55e", width: 3 }, marker: { size: 9 },
        text: silhouettes.map((v) => v.toFixed(2)), textposition: "top center" },
      { x: [bestK], y: [bestIdx >= 0 ? silhouettes[bestIdx] : null], mode: "markers", type: "scatter", name: "k recomendado",
        marker: { color: "#ef4444", size: 14, symbol: "star" } },
      { x: [selectedK], y: [selectedIdx >= 0 ? silhouettes[selectedIdx] : null], mode: "markers", type: "scatter", name: "k seleccionado",
        marker: { color: "#f59e0b", size: 13, symbol: "diamond" } },
    ], { ...PLOT_LAYOUT, title: "Gráfica de rodilla / eficiencia (evaluación completa k=2..9)",
      xaxis: { title: "Número de clusters (k)" }, yaxis: { title: "Silueta" } }, PLOT_CFG);
  }

  function renderSweepPlots(selectedK) {
    const pts = (sweep.points || []).map((p, idx) => ({ ...p, cluster: (sweep.labels?.[String(selectedK)] || [])[idx] }));
    const byC = {};
    pts.forEach((p) => { (byC[p.cluster] = byC[p.cluster] || []).push(p); });
    const traces = Object.entries(byC).map(([c, arr]) => ({
      x: arr.map((p) => p.pc1), y: arr.map((p) => p.pc2),
      text: arr.map((p) => `${p.compound_name} (${p.family})`),
      mode: "markers", type: "scatter", name: "Cluster " + c, marker: { size: 8, opacity: 0.74 },
      hovertemplate: "%{text}<br>PC1 %{x:.2f} · PC2 %{y:.2f}<extra></extra>",
    }));
    Plotly.newPlot("chart-pca", traces, { ...PLOT_LAYOUT, title: `K-means con 7 descriptores + proyección PCA (k=${selectedK})`,
      xaxis: { title: `PC1 (${(100 * ev[0]).toFixed(0)}%)` }, yaxis: { title: `PC2 (${(100 * ev[1]).toFixed(0)}%)` },
      legend: { orientation: "h", y: -0.2 } }, PLOT_CFG);
    renderCurvePlots(selectedK);
    const currentSil = silhouettes[ks.indexOf(selectedK)];
    document.getElementById("mv-k-note").innerHTML =
      `Clustering calculado sobre <strong>7 descriptores estandarizados</strong>. PCA se usa solo para visualizar en 2D. k recomendado: <strong>${bestK}</strong> · k visualizado: <strong>${selectedK}</strong> · silueta del k seleccionado: <strong>${currentSil != null ? currentSil.toFixed(2) : "—"}</strong>`;
  }

  kSel.addEventListener("change", () => renderSweepPlots(Number(kSel.value)));
  kSel.addEventListener("input", () => renderSweepPlots(Number(kSel.value)));
  renderSweepPlots(bestK);
  renderMetricGlossary(document.getElementById("mv-metric-gloss"),
    ["pca_var", "silhouette", "ari", "epsilon2", "p_adjusted"], "Qué significa cada métrica");

  const tests = (fam.kruskal_tests || []).slice().filter((t) => t.epsilon2 != null).sort((a, b) => b.epsilon2 - a.epsilon2);
  Plotly.newPlot("chart-kruskal", [{
    x: tests.map((t) => colLabel(t.value_col)), y: tests.map((t) => t.epsilon2), type: "bar",
    marker: { color: tests.map((t) => (t.p_adjusted != null && t.p_adjusted < 0.05 ? "#4a9e6d" : "#8a95a8")) },
    text: tests.map((t) => t.epsilon2.toFixed(3)), textposition: "outside", textfont: { size: 10 },
  }], { ...PLOT_LAYOUT, title: "Tamaño de efecto (ε²) por descriptor entre familias", yaxis: { title: "ε²" } }, PLOT_CFG);
  document.getElementById("mv-kruskal-table").innerHTML =
    `<div class="table-scroll"><table class="data-table"><thead><tr><th>Descriptor</th><th>ε² (efecto)</th><th>p ajustado</th><th>¿Significativo?</th></tr></thead><tbody>`
    + tests.map((t) => `<tr><td>${colLabel(t.value_col)}</td><td>${t.epsilon2.toFixed(3)}</td>`
      + `<td>${t.p_adjusted != null ? t.p_adjusted.toExponential(2) : "—"}</td>`
      + `<td>${t.p_adjusted != null && t.p_adjusted < 0.05 ? "Sí" : "No"}</td></tr>`).join("")
    + `</tbody></table></div>`;
}

// ── Vista Modelado ─────────────────────────────────────────────────────────────
let MODEL = null;
async function initModelado() {
  await loadGlossary();
  try {
    const [info, compounds, ds] = await Promise.all([
      fetch("/api/analytics/model/info").then((r) => r.json()),
      fetch("/api/analytics/model/compounds").then((r) => r.json()),
      fetch("/api/analytics/dashboard/dataset").then((r) => r.json()),
    ]);
    MODEL = { ...info, compounds: compounds.compounds || [], compoundFeatures: compounds.features || [], _rows: ds.rows || [] };
  } catch (e) { return; }
  const SPLIT_ES = {
    filas_KFold_CON_FUGA: ["Con fuga (por filas)", "bad"],
    filas_GroupKFold_HONESTO: ["Sin fuga (por grupos)", "warn"],
    compuesto: ["Por compuesto", "bad"],
  };
  const rows = (MODEL.metrics && MODEL.metrics.rows) || [];
  document.getElementById("model-metrics").innerHTML = rows.map((r) => {
    const [es, cls] = SPLIT_ES[r.split] || [r.split, ""];
    return `<div class="metric-tile"><div class="val ${cls}">${r.r2_cv_mean.toFixed(2)}</div>`
      + `<div class="lbl">R² — ${es}<small>n=${r.n}</small></div></div>`;
  }).join("");
  renderMetricGlossary(document.getElementById("model-metric-gloss"),
    ["r2", "leak", "honest", "compound"], "Cómo leer estas métricas");

  // Inputs de descriptores
  const feats = MODEL.features || [];
  document.getElementById("pred-inputs").innerHTML = feats.map((c) => {
    const rg = (MODEL.ranges && MODEL.ranges[c]) || [0, 1, 0];
    return `<label>${(MODEL.labels && MODEL.labels[c]) || c}`
      + `<input type="number" step="any" id="f-${c}" value="${(+rg[2]).toFixed(2)}" style="width:120px"></label>`;
  }).join("");
  predCompoundCombo = setupComboBox(document.getElementById("pred-compound-combo"), MODEL.compounds.filter((r) => r.compound_name), {
    placeholder: "Ej: Atrazine",
    getLabel: (item) => item.compound_name,
    getValue: (item) => item.compound_name,
    getMeta: (item) => {
      const p = item.has_potency
        ? `<span class="pill good">pChEMBL ${Number(item.pchembl_median_binding).toFixed(2)}</span>`
        : `<span class="pill warn">${esc(item.measurement_tag || "Sin medicion")}</span>`;
      const family = item.family ? `<span class="pill neutral">${esc(item.family)}</span>` : "";
      return `${p}${family}`;
    },
    onSelect: () => {},
  });

  document.getElementById("pred-fill").addEventListener("click", () => {
    const q = predCompoundCombo ? predCompoundCombo.getValue().toLowerCase() : "";
    const row = (MODEL._rows || []).find((r) => String(r.compound_name).toLowerCase() === q);
    if (!row) return;
    feats.forEach((c) => { if (row[c] != null) document.getElementById(`f-${c}`).value = row[c]; });
  });
  document.getElementById("pred-run").addEventListener("click", runPredict);
}

async function runPredict() {
  const feats = MODEL.features || [];
  const desc = {};
  feats.forEach((c) => { desc[c] = parseFloat(document.getElementById(`f-${c}`).value); });
  const r = await (await fetch("/api/analytics/model/predict", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(desc),
  })).json();
  const honest = ((MODEL.metrics && MODEL.metrics.rows) || []).find((x) => x.split === "compuesto");
  const r2c = honest ? honest.r2_cv_mean.toFixed(2) : "—";
  document.getElementById("pred-result").innerHTML =
    `<div class="pred-result"><div class="big ${r.activo ? "good" : ""}">pChEMBL ≈ ${r.prediction}</div>`
    + `<div>${r.activo ? "El modelo lo clasificaría como <strong>Activo</strong> (≥6)" : "Por debajo del umbral de actividad (6)"} `
    + `· incertidumbre del ensemble ±${r.tree_std}</div>`
    + `<div class="warn-box"><strong>Esta predicción NO es confiable.</strong> Evaluado honestamente por compuesto, el modelo tiene <strong>R² = ${r2c}</strong> (negativo = peor que predecir el promedio). Los descriptores globales no bastan para predecir potencia en compuestos no vistos — este es justamente el límite que motiva usar grafos moleculares (proyecto GNN).</div></div>`;
}

const INIT = { adquisicion: initAdquisicion, limpieza: initLimpieza, exploracion: initExploracion, multivariado: initMultivariado, modelado: initModelado };

// ── Arranque ──────────────────────────────────────────────────────────────────
document.querySelectorAll(".spa-navbtn").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));
showView("adquisicion");
