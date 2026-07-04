const plotLayout = {
  paper_bgcolor: "#1a2332",
  plot_bgcolor: "#1a2332",
  font: { color: "#e8edf4" },
  margin: { l: 50, r: 20, t: 40, b: 80 },
};

function showLoading(show) {
  const el = document.getElementById("loading-overlay");
  if (el) el.hidden = !show;
}

async function loadComparison() {
  const res = await fetch("/api/analytics/models/comparison");
  if (!res.ok) throw new Error("Ejecute: make prepare-dashboard");
  return res.json();
}

async function loadMetrics() {
  const res = await fetch("/api/analytics/metrics/summary");
  if (!res.ok) return [];
  return res.json();
}

function renderComparison(data) {
  const names = data.models.map((m) => m.name);
  const aucs = data.models.map((m) => m.mean_auc);
  const colors = names.map((n) => (n === "GIN" ? "#40916c" : "#3b82f6"));

  Plotly.newPlot(
    "chart-comparison",
    [{
      x: names,
      y: aucs,
      type: "bar",
      marker: { color: colors },
      text: aucs.map((v) => v.toFixed(3)),
      textposition: "auto",
    }],
    {
      ...plotLayout,
      title: "AUC-ROC promedio — baselines vs GIN",
      yaxis: { title: "AUC", range: [0, 1] },
      shapes: [{
        type: "line",
        x0: -0.5,
        x1: names.length - 0.5,
        y0: data.objective_auc || 0.82,
        y1: data.objective_auc || 0.82,
        line: { dash: "dash", color: "#ef4444" },
      }],
    },
    { responsive: true }
  );

  let note = data.note || "";
  if (data.cv_summary) {
    note += ` CV: ${data.cv_summary.mean_auc.toFixed(3)} ± ${data.cv_summary.std_auc.toFixed(3)} (${data.cv_summary.n_folds} folds).`;
  }
  document.getElementById("comparison-note").textContent = note;
}

function renderMetricsTable(rows) {
  const compound = rows.filter((r) => r.split === "compuesto");
  if (!compound.length) {
    document.getElementById("metrics-table").textContent = "Sin métricas por compuesto.";
    return;
  }
  let html = "<table class='atoms-table'><tr><th>Modelo</th><th>Tarea</th><th>Feature set</th><th>R² test</th><th>Accuracy</th></tr>";
  compound.forEach((r) => {
    html += `<tr><td>${r.modelo}</td><td>${r.tarea}</td><td>${r.feature_set}</td><td>${r.r2_test ?? "—"}</td><td>${r.accuracy_test ?? "—"}</td></tr>`;
  });
  html += "</table>";
  document.getElementById("metrics-table").innerHTML = html;
}

document.addEventListener("DOMContentLoaded", async () => {
  showLoading(true);
  try {
    const [cmp, metrics] = await Promise.all([loadComparison(), loadMetrics()]);
    renderComparison(cmp);
    renderMetricsTable(metrics);
  } catch (err) {
    document.getElementById("chart-comparison").innerHTML = `<p class='hint'>${err.message}</p>`;
  } finally {
    showLoading(false);
  }
});
