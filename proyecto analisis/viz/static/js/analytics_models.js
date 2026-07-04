const plotLayout = {
  paper_bgcolor: "#1a2332",
  plot_bgcolor: "#1a2332",
  font: { color: "#e8edf4" },
  margin: { l: 50, r: 20, t: 40, b: 50 },
};

let evalData = null;

async function loadEval() {
  const res = await fetch("/api/analytics/models/eval");
  if (!res.ok) throw new Error("Ejecute: make prepare-dashboard");
  evalData = await res.json();
}

function renderClassification(modelName) {
  const d = evalData.classification[modelName];
  Plotly.newPlot(
    "chart-confusion",
    [{
      z: d.confusion_matrix,
      x: d.labels,
      y: d.labels,
      type: "heatmap",
      colorscale: "Blues",
      text: d.confusion_matrix,
      texttemplate: "%{text}",
    }],
    { ...plotLayout, title: `Matriz de confusión — ${modelName}` },
    { responsive: true }
  );

  Plotly.newPlot(
    "chart-roc",
    [
      { x: d.roc.fpr, y: d.roc.tpr, mode: "lines", name: `AUC=${d.roc.auc.toFixed(3)}` },
      { x: [0, 1], y: [0, 1], mode: "lines", line: { dash: "dash" }, name: "Azar" },
    ],
    { ...plotLayout, title: `ROC — ${modelName}`, xaxis: { title: "FPR" }, yaxis: { title: "TPR" } },
    { responsive: true }
  );
}

function renderRegression(modelName) {
  const d = evalData.regression[modelName];
  const lims = [
    Math.min(...d.y_true, ...d.y_pred),
    Math.max(...d.y_true, ...d.y_pred),
  ];
  Plotly.newPlot(
    "chart-regression",
    [
      { x: d.y_true, y: d.y_pred, mode: "markers", marker: { color: "#40916c", opacity: 0.5 } },
      { x: lims, y: lims, mode: "lines", line: { dash: "dash" }, name: "Ideal" },
    ],
    {
      ...plotLayout,
      title: `Predicho vs real — ${modelName} (R²=${d.r2_test.toFixed(3)})`,
      xaxis: { title: "pChEMBL real" },
      yaxis: { title: "pChEMBL predicho" },
    },
    { responsive: true }
  );
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await loadEval();
    const clfSel = document.getElementById("clf-model");
    const regSel = document.getElementById("reg-model");

    renderClassification(clfSel.value);
    renderRegression(regSel.value);
    clfSel.addEventListener("change", () => renderClassification(clfSel.value));
    regSel.addEventListener("change", () => renderRegression(regSel.value));

    document.getElementById("predict-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const inputs = {};
      e.target.querySelectorAll("input[name]").forEach((el) => {
        inputs[el.name] = parseFloat(el.value) || 0;
      });
      const res = await fetch("/api/analytics/models/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inputs }),
      });
      const box = document.getElementById("predict-result");
      box.hidden = false;
      if (!res.ok) {
        box.textContent = "Error en predicción";
        return;
      }
      const data = await res.json();
      box.innerHTML = `<strong>pChEMBL predicho: ${data.pchembl}</strong><br>Potencia: ${data.level}`;
    });
  } catch (err) {
    document.querySelector(".container").insertAdjacentHTML(
      "beforeend",
      `<div class="empty-state card"><p>${err.message}</p></div>`
    );
  }
});
