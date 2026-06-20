const plotLayout = {
  paper_bgcolor: "#1a2332",
  plot_bgcolor: "#1a2332",
  font: { color: "#e8edf4" },
  margin: { l: 120, r: 20, t: 40, b: 50 },
};

function showLoading(show) {
  const el = document.getElementById("loading-overlay");
  if (el) el.hidden = !show;
}

async function loadProfile() {
  const family = document.getElementById("tx-family").value;
  const alerta = document.getElementById("tx-alerta").value;
  const qs = new URLSearchParams({ family, alerta });
  const res = await fetch(`/api/analytics/toxicity/profile?${qs}`);
  if (!res.ok) throw new Error("Ejecute: make panama-predict");
  return res.json();
}

function renderHeatmap(payload) {
  const compounds = payload.compounds.map((c) => c.compuesto);
  const tasks = payload.tasks;
  const z = payload.compounds.map((c) => tasks.map((t) => c.tasks[t]));

  Plotly.newPlot(
    "chart-heatmap",
    [{
      z,
      x: tasks,
      y: compounds,
      type: "heatmap",
      colorscale: "YlOrRd",
    }],
    { ...plotLayout, title: "Heatmap toxicidad — 12 vías Tox21" },
    { responsive: true }
  );

  const sel = document.getElementById("tx-compound");
  const prev = sel.value;
  sel.innerHTML = "";
  payload.compounds.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.compuesto;
    opt.textContent = c.compuesto;
    sel.appendChild(opt);
  });
  if (prev && [...sel.options].some((o) => o.value === prev)) {
    sel.value = prev;
  }
}

async function loadXai() {
  const compound = document.getElementById("tx-compound").value;
  const method = document.getElementById("tx-method").value;
  const box = document.getElementById("xai-image");
  const meta = document.getElementById("xai-meta");
  if (!compound) {
    box.innerHTML = "<p class='hint'>Seleccione un compuesto</p>";
    return;
  }
  const qs = new URLSearchParams({ compound, method });
  const res = await fetch(`/api/analytics/toxicity/xai?${qs}`);
  if (!res.ok) {
    box.innerHTML = "<p class='hint'>SVG XAI no disponible</p>";
    meta.textContent = "";
    return;
  }
  const data = await res.json();
  meta.textContent = `${data.compound} | ${data.task} | prob_max=${data.prob_max.toFixed(3)} | ${data.alerta}`;
  box.innerHTML = `<img src="${data.url}" alt="XAI ${compound}" style="max-width:100%;max-height:420px" />`;
}

async function refreshAll() {
  showLoading(true);
  try {
    const payload = await loadProfile();
    renderHeatmap(payload);
    await loadXai();
  } finally {
    showLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  ["tx-family", "tx-alerta", "tx-method"].forEach((id) => {
    document.getElementById(id).addEventListener("change", refreshAll);
  });
  document.getElementById("tx-compound").addEventListener("change", loadXai);
  refreshAll().catch((err) => {
    document.getElementById("chart-heatmap").innerHTML =
      `<p class='hint'>${err.message}</p>`;
  });
});
