const plotLayout = {
  paper_bgcolor: "#1a2332",
  plot_bgcolor: "#1a2332",
  font: { color: "#e8edf4" },
  margin: { l: 0, r: 0, t: 40, b: 0 },
};

function showLoading(show) {
  const el = document.getElementById("loading-overlay");
  if (el) el.hidden = !show;
}

let geojson = null;

async function loadGeo() {
  if (geojson) return geojson;
  const res = await fetch("/api/analytics/geo");
  if (!res.ok) throw new Error("Ejecute: make download-geodata");
  geojson = await res.json();
  return geojson;
}

async function renderMap() {
  showLoading(true);
  try {
    const variable = document.getElementById("map-variable").value;
    const res = await fetch(`/api/analytics/geo/summary?variable=${variable}`);
    if (!res.ok) throw new Error("Error cargando resumen geográfico");
    const summary = await res.json();
    const geo = await loadGeo();

    const locations = summary.districts.map((d) => d.shapeName);
    const z = summary.districts.map((d) => d[variable] ?? 0);

    Plotly.newPlot(
      "chart-map",
      [{
        type: "choroplethmapbox",
        geojson: geo,
        locations,
        z,
        featureidkey: "properties.shapeName",
        colorscale: "Viridis",
        marker: { opacity: 0.75 },
        colorbar: { title: summary.label },
      }],
      {
        ...plotLayout,
        mapbox: { style: "carto-darkmatter", zoom: 6, center: { lat: 8.5, lon: -80 } },
        title: `Panamá — ${summary.label}`,
        height: 520,
      },
      { responsive: true }
    );

    Plotly.newPlot(
      "chart-bars",
      [{
        x: summary.provinces.map((p) => p.provincia),
        y: summary.provinces.map((p) => p[variable]),
        type: "bar",
        marker: { color: "#40916c" },
      }],
      {
        ...plotLayout,
        title: `Total por provincia — ${summary.label}`,
        xaxis: { tickangle: 45 },
        margin: { l: 50, r: 20, t: 40, b: 120 },
      },
      { responsive: true }
    );
  } finally {
    showLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("map-variable").addEventListener("change", () => {
    renderMap().catch((err) => {
      document.getElementById("chart-map").innerHTML = `<p class='hint'>${err.message}</p>`;
    });
  });
  renderMap().catch((err) => {
    document.getElementById("chart-map").innerHTML = `<p class='hint'>${err.message}</p>`;
  });
});
