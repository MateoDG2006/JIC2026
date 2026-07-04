const plotLayout = {
  paper_bgcolor: "#1a2332",
  plot_bgcolor: "#1a2332",
  font: { color: "#e8edf4" },
  margin: { l: 50, r: 20, t: 40, b: 50 },
};

function showLoading(show) {
  const el = document.getElementById("loading-overlay");
  if (el) el.hidden = !show;
}

async function loadMeta() {
  const res = await fetch("/api/analytics/chembl/meta");
  if (!res.ok) throw new Error("No se pudo cargar metadata ChEMBL");
  return res.json();
}

async function loadData(params) {
  const qs = new URLSearchParams(params);
  const res = await fetch(`/api/analytics/chembl/data?${qs}`);
  if (!res.ok) throw new Error("Error cargando datos");
  return res.json();
}

async function loadCorrelation() {
  const res = await fetch("/api/analytics/chembl/correlation");
  if (!res.ok) throw new Error("Ejecute: make prepare-dashboard");
  return res.json();
}

function renderCharts(data, corr, variable) {
  Plotly.newPlot(
    "chart-hist",
    [{ x: data.histogram, type: "histogram", marker: { color: "#40916c" } }],
    { ...plotLayout, title: `Distribución de ${variable}` },
    { responsive: true }
  );

  Plotly.newPlot(
    "chart-box",
    [{ x: data.boxplot.family, y: data.boxplot.values, type: "box", marker: { color: "#3b82f6" } }],
    { ...plotLayout, title: `${variable} por familia`, showlegend: false },
    { responsive: true }
  );

  Plotly.newPlot(
    "chart-corr",
    [{
      z: corr.matrix,
      x: corr.columns,
      y: corr.columns,
      type: "heatmap",
      colorscale: "RdBu",
      zmid: 0,
    }],
    { ...plotLayout, title: "Correlación de Pearson" },
    { responsive: true }
  );

  const scatter = data.scatter || [];
  Plotly.newPlot(
    "chart-scatter",
    [{
      x: scatter.map((r) => r.mw_freebase),
      y: scatter.map((r) => r.alogp),
      text: scatter.map((r) => r.compound_name || ""),
      mode: "markers",
      type: "scatter",
      marker: { color: "#22c55e", opacity: 0.65 },
    }],
    { ...plotLayout, title: "MW vs LogP", xaxis: { title: "MW" }, yaxis: { title: "LogP" } },
    { responsive: true }
  );
}

async function refresh() {
  showLoading(true);
  try {
    const variable = document.getElementById("eda-variable").value;
    const family = document.getElementById("eda-family").value;
    const mwMin = document.getElementById("eda-mw-min").value;
    const mwMax = document.getElementById("eda-mw-max").value;
    const params = { variable, family };
    if (mwMin) params.mw_min = mwMin;
    if (mwMax) params.mw_max = mwMax;

    const [data, corr] = await Promise.all([loadData(params), loadCorrelation()]);
    renderCharts(data, corr, variable);
  } finally {
    showLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const meta = await loadMeta();
    const varSel = document.getElementById("eda-variable");
    meta.numeric_cols.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      if (c === "pchembl_median_binding") opt.selected = true;
      varSel.appendChild(opt);
    });
    const famSel = document.getElementById("eda-family");
    meta.families.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      famSel.appendChild(opt);
    });
    document.getElementById("eda-mw-min").value = Math.round(meta.mw_default[0]);
    document.getElementById("eda-mw-max").value = Math.round(meta.mw_default[1]);

    document.getElementById("eda-refresh").addEventListener("click", refresh);
    varSel.addEventListener("change", refresh);
    famSel.addEventListener("change", refresh);
    await refresh();
  } catch (err) {
    document.querySelector(".chart-grid").innerHTML =
      `<div class="empty-state card"><p>${err.message}</p></div>`;
  }
});
