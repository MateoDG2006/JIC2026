/* ============================================================================
   presentacion.js — Deck de diapositivas del Proyecto de Análisis de Datos.
   Navegación por teclado/click + render perezoso de gráficos Plotly contra
   las APIs FastAPI existentes (/api/analytics/...).
   ============================================================================ */

// ---- Estilo común de gráficos (paleta oscura del dashboard) ----------------
const L = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: "#e8edf4", size: 11 },
  margin: { l: 48, r: 16, t: 34, b: 40 },
  legend: { font: { size: 9 } },
};
const CFG = { responsive: true, displayModeBar: false };
const FAMILY_COLORS = {
  Organophosphates: "#3b82f6",
  Pyrethroids: "#22c55e",
  Herbicides: "#f59e0b",
  Carbamates: "#a855f7",
  Triazines: "#ef4444",
  Azole_fungicides: "#14b8a6",
  mixed: "#8b9cb3",
};

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`No se pudo cargar ${url} (ejecuta: make prepare-dashboard)`);
  return res.json();
}

function fail(id, msg) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<p class="hint" style="padding:1rem">${msg}</p>`;
}

// ============================================================================
//  Renderizadores por diapositiva (cada uno se ejecuta una sola vez)
// ============================================================================

// --- Slide 4: embudo del corpus + compuestos por familia -------------------
async function initFunnel() {
  try {
    const stats = await getJSON("/api/analytics/families/stats");
    const fam = stats.n_by_family || {};
    const entries = Object.entries(fam).sort((a, b) => b[1] - a[1]);
    Plotly.newPlot(
      "plot-funnel",
      [{
        type: "bar",
        orientation: "h",
        y: entries.map((e) => e[0]),
        x: entries.map((e) => e[1]),
        marker: { color: entries.map((e) => FAMILY_COLORS[e[0]] || "#3b82f6") },
        text: entries.map((e) => e[1]),
        textposition: "auto",
      }],
      { ...L, title: "Compuestos estructurales por familia química", margin: { l: 130, r: 16, t: 34, b: 30 } },
      CFG
    );
  } catch (e) { fail("plot-funnel", e.message); }
}

// --- Slide 5: EDA reactivo (histograma, box, correlación, dispersión) ------
let edaReady = false;
async function initEda() {
  if (edaReady) return;
  edaReady = true;
  try {
    const meta = await getJSON("/api/analytics/chembl/meta");
    const varSel = document.getElementById("eda-variable");
    meta.numeric_cols.forEach((c) => {
      const o = document.createElement("option");
      o.value = c; o.textContent = c;
      if (c === "pchembl_median_binding") o.selected = true;
      varSel.appendChild(o);
    });
    const famSel = document.getElementById("eda-family");
    meta.families.forEach((f) => {
      const o = document.createElement("option");
      o.value = f; o.textContent = f;
      famSel.appendChild(o);
    });
    document.getElementById("eda-mw-min").value = Math.round(meta.mw_default[0]);
    document.getElementById("eda-mw-max").value = Math.round(meta.mw_default[1]);

    const refresh = () => renderEda();
    document.getElementById("eda-refresh").addEventListener("click", refresh);
    varSel.addEventListener("change", refresh);
    famSel.addEventListener("change", refresh);
    await renderEda();
  } catch (e) {
    fail("chart-hist", e.message);
  }
}

async function renderEda() {
  const variable = document.getElementById("eda-variable").value;
  const family = document.getElementById("eda-family").value;
  const mwMin = document.getElementById("eda-mw-min").value;
  const mwMax = document.getElementById("eda-mw-max").value;
  const params = new URLSearchParams({ variable, family });
  if (mwMin) params.set("mw_min", mwMin);
  if (mwMax) params.set("mw_max", mwMax);

  const [data, corr] = await Promise.all([
    getJSON(`/api/analytics/chembl/data?${params}`),
    getJSON("/api/analytics/chembl/correlation"),
  ]);

  Plotly.newPlot("chart-hist",
    [{ x: data.histogram, type: "histogram", marker: { color: "#40916c" } }],
    { ...L, title: `Distribución de ${variable} (n=${data.count})` }, CFG);

  Plotly.newPlot("chart-box",
    [{ x: data.boxplot.family, y: data.boxplot.values, type: "box", marker: { color: "#3b82f6" } }],
    { ...L, title: `${variable} por familia`, showlegend: false }, CFG);

  Plotly.newPlot("chart-corr",
    [{ z: corr.matrix, x: corr.columns, y: corr.columns, type: "heatmap", colorscale: "RdBu", zmid: 0 }],
    { ...L, title: "Correlación de Pearson" }, CFG);

  const s = data.scatter || [];
  Plotly.newPlot("chart-scatter",
    [{
      x: s.map((r) => r.mw_freebase), y: s.map((r) => r.alogp),
      text: s.map((r) => r.compound_name || ""), mode: "markers", type: "scatter",
      marker: { color: "#22c55e", opacity: 0.65 },
    }],
    { ...L, title: "MW vs LogP", xaxis: { title: "MW" }, yaxis: { title: "LogP" } }, CFG);
}

// --- Slide 6: heatmap de correlación grande --------------------------------
async function initCorrBig() {
  try {
    const corr = await getJSON("/api/analytics/chembl/correlation");
    Plotly.newPlot("plot-corr-big",
      [{
        z: corr.matrix, x: corr.columns, y: corr.columns, type: "heatmap",
        colorscale: "RdBu", zmid: 0, zmin: -1, zmax: 1,
        text: corr.matrix.map((r) => r.map((v) => v.toFixed(2))),
        texttemplate: "%{text}", textfont: { size: 9 },
        colorbar: { title: "r" },
      }],
      { ...L, title: "Matriz de correlación de Pearson entre descriptores", margin: { l: 110, r: 16, t: 34, b: 90 } },
      CFG);
  } catch (e) { fail("plot-corr-big", e.message); }
}

// --- Slide 7: Kruskal-Wallis (tamaño de efecto por descriptor) -------------
async function initKruskal() {
  try {
    const stats = await getJSON("/api/analytics/families/stats");
    const tests = (stats.kruskal_tests || []).slice().sort((a, b) => b.epsilon2 - a.epsilon2);
    Plotly.newPlot("plot-kruskal",
      [{
        type: "bar",
        x: tests.map((t) => t.value_col),
        y: tests.map((t) => t.epsilon2),
        marker: { color: tests.map((t) => (t.p_adjusted < 0.05 ? "#22c55e" : "#8b9cb3")) },
        text: tests.map((t) => t.epsilon2.toFixed(3)),
        textposition: "auto",
      }],
      {
        ...L,
        title: "Tamaño de efecto ε² por descriptor (Kruskal–Wallis)",
        yaxis: { title: "ε²" },
        xaxis: { tickangle: 35 },
        margin: { l: 48, r: 16, t: 34, b: 90 },
      },
      CFG);
  } catch (e) { fail("plot-kruskal", e.message); }
}

// --- Slide 8: dispersión PCA coloreada por familia -------------------------
async function initPca() {
  try {
    const data = await getJSON("/api/analytics/clusters/pca");
    const pts = data.points || [];
    const byFam = {};
    pts.forEach((p) => {
      (byFam[p.family] = byFam[p.family] || { x: [], y: [], t: [] });
      byFam[p.family].x.push(p.pc1);
      byFam[p.family].y.push(p.pc2);
      byFam[p.family].t.push(p.compound_name || p.chembl_id);
    });
    const traces = Object.entries(byFam).map(([fam, d]) => ({
      x: d.x, y: d.y, text: d.t, name: fam, mode: "markers", type: "scatter",
      marker: { color: FAMILY_COLORS[fam] || "#8b9cb3", size: 7, opacity: 0.75 },
    }));
    Plotly.newPlot("plot-pca", traces,
      {
        ...L,
        title: "PCA de descriptores — coloreado por familia (78.2% var.)",
        xaxis: { title: "PC1 (46.5%)" }, yaxis: { title: "PC2 (31.7%)" },
        showlegend: true, legend: { font: { size: 9 }, orientation: "h", y: -0.2 },
        margin: { l: 48, r: 16, t: 34, b: 60 },
      },
      CFG);
  } catch (e) { fail("plot-pca", e.message); }
}

// --- Slide 9: baseline honesto vs con fuga (hallazgo central) ---------------
const SPLIT_LABELS = {
  filas_KFold_CON_FUGA: "Por filas (con fuga)",
  filas_GroupKFold_HONESTO: "Por grupos (honesto)",
  compuesto: "Por compuesto",
};
async function initBaseline() {
  try {
    const data = await getJSON("/api/analytics/baseline/honest");
    const rows = data.rows || [];
    if (!rows.length) throw new Error(data.note || "Sin datos de baseline.");
    const labels = rows.map((r) => SPLIT_LABELS[r.split] || r.split);
    const means = rows.map((r) => r.r2_cv_mean);
    const errPlus = rows.map((r) => Math.max(0, r.r2_ci95_high - r.r2_cv_mean));
    const errMinus = rows.map((r) => Math.max(0, r.r2_cv_mean - r.r2_ci95_low));
    Plotly.newPlot("plot-baseline",
      [{
        type: "bar",
        x: labels,
        y: means,
        marker: { color: means.map((v) => (v >= 0 ? "#22c55e" : "#ef4444")) },
        text: means.map((v) => v.toFixed(3)),
        textposition: "outside",
        error_y: { type: "data", symmetric: false, array: errPlus, arrayminus: errMinus, color: "#e8edf4" },
      }],
      {
        ...L,
        title: "R² del Random Forest por esquema de validación (IC 95% bootstrap)",
        yaxis: { title: "R²", zeroline: true, zerolinecolor: "#8b9cb3", zerolinewidth: 2 },
        shapes: [{ type: "line", x0: -0.5, x1: labels.length - 0.5, y0: 0, y1: 0, line: { color: "#8b9cb3", dash: "dot" } }],
        margin: { l: 48, r: 16, t: 34, b: 60 },
      },
      CFG);
  } catch (e) { fail("plot-baseline", e.message); }
}

// Mapa índice de diapositiva -> inicializador (0-based)
// Orden: 0 portada · 1 equipo · 2 stack · 3 pregunta · 4-12 conceptos · 13-17 fases · 18 pipeline · 19-23 resultados
const SLIDE_INIT = {
  18: initFunnel,     // Pipeline — embudo corpus
  19: initEda,        // EDA interactivo
  20: initCorrBig,    // Correlación
  21: initKruskal,    // Diferencias entre familias (Kruskal)
  22: initPca,        // PCA / clustering
  23: initBaseline,   // Hallazgo central — baseline
};

/** Reinicia animaciones CSS del pipeline al entrar en una diapositiva de fase. */
function replayPipelineAnimations(slide) {
  if (!slide.classList.contains("slide-phase")) return;
  slide.querySelectorAll(".pipe-node").forEach((el) => {
    el.style.animation = "none";
    void el.offsetWidth;
    el.style.animation = "";
  });
}

// ============================================================================
//  Motor de navegación del deck
// ============================================================================
(function () {
  const slides = Array.from(document.querySelectorAll(".slide"));
  const total = slides.length;
  const initDone = new Set();
  let current = 0;

  const progress = document.getElementById("deck-progress");
  const counter = document.getElementById("deck-counter");
  const dotsWrap = document.getElementById("deck-dots");

  slides.forEach((_, i) => {
    const b = document.createElement("button");
    b.setAttribute("aria-label", `Ir a la diapositiva ${i + 1}`);
    b.addEventListener("click", () => go(i));
    dotsWrap.appendChild(b);
  });
  const dots = Array.from(dotsWrap.children);

  function resizePlots(slide) {
    slide.querySelectorAll(".plot, [id^='chart-']").forEach((el) => {
      if (el.data) { try { Plotly.Plots.resize(el); } catch (_) {} }
    });
  }

  function go(idx) {
    idx = Math.max(0, Math.min(total - 1, idx));
    if (typeof window.closeAllPhaseDetails === "function") {
      window.closeAllPhaseDetails();
    }
    slides[current].classList.remove("active");
    dots[current].classList.remove("active");
    current = idx;
    slides[current].classList.add("active");
    dots[current].classList.add("active");
    counter.textContent = `${current + 1} / ${total}`;
    progress.style.width = `${((current + 1) / total) * 100}%`;

    replayPipelineAnimations(slides[current]);

    if (SLIDE_INIT[current] && !initDone.has(current)) {
      initDone.add(current);
      Promise.resolve(SLIDE_INIT[current]()).then(() => resizePlots(slides[current]));
    } else {
      // dejar que la transición de layout termine antes de redimensionar
      setTimeout(() => resizePlots(slides[current]), 420);
    }
    if (location.hash !== `#${current + 1}`) {
      history.replaceState(null, "", `#${current + 1}`);
    }
  }

  document.getElementById("nav-prev").addEventListener("click", () => go(current - 1));
  document.getElementById("nav-next").addEventListener("click", () => go(current + 1));

  document.addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "select" || tag === "textarea") return;
    if (e.key === "Escape") {
      if (window.isPipeModalOpen?.()) {
        e.preventDefault();
        window.closeAllPhaseDetails?.();
        return;
      }
    }
    if (window.isPipeModalOpen?.()) {
      if (["ArrowRight", "PageDown", " ", "ArrowLeft", "PageUp"].includes(e.key)) return;
    }
    if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); go(current + 1); }
    else if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); go(current - 1); }
    else if (e.key === "Home") { e.preventDefault(); go(0); }
    else if (e.key === "End") { e.preventDefault(); go(total - 1); }
    else if (e.key.toLowerCase() === "f") {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
      else document.exitFullscreen?.();
    }
  });

  window.addEventListener("resize", () => resizePlots(slides[current]));

  // Arranque (respeta el hash #n si viene en la URL)
  if (typeof window.initPipePhases === "function") window.initPipePhases();
  const start = parseInt((location.hash || "").replace("#", ""), 10);
  go(Number.isFinite(start) && start >= 1 ? start - 1 : 0);
})();
