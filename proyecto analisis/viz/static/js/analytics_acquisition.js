// Fase 1 — Adquisición: embudo, resolución y muestra de datos crudos
const METHOD_ES = {
  known_registry: "Registro curado (MIDA)",
  sqlite_smiles: "Por estructura (SMILES)",
  sqlite_pref_name: "Por nombre",
  sqlite_synonym: "Por sinónimo",
  not_found: "No encontrado en ChEMBL",
};

(async function () {
  await loadGlossary();
  let d;
  try {
    d = await (await fetch("/api/analytics/acquisition")).json();
  } catch (e) {
    document.getElementById("acq-metrics").innerHTML = "<p>Error cargando datos.</p>";
    return;
  }
  const f = d.funnel || {};
  const res = d.resolution || {};
  const okResolved = (res.by_status && res.by_status.ok) || 0;

  // ── Métricas ───────────────────────────────────────────────
  const metrics = [
    { v: 235, l: "Candidatos PubChem" },
    { v: okResolved, l: "Resueltos a ChEMBL" },
    { v: (d.n_measurements || 0).toLocaleString("es"), l: "Mediciones extraídas" },
    { v: f.raw_compounds ?? "—", l: "Compuestos estructurales" },
    { v: f.with_potency_binding_min_support ?? "—", l: "Con potencia útil" },
    { v: d.n_targets ?? "—", l: "Dianas distintas" },
  ];
  document.getElementById("acq-metrics").innerHTML = metrics
    .map((m) => `<div class="metric-tile"><div class="val">${m.v}</div><div class="lbl">${m.l}</div></div>`)
    .join("");

  // ── Embudo (barras) ────────────────────────────────────────
  const steps = [
    ["Candidatos PubChem", 235],
    ["Resueltos a ChEMBL", okResolved],
    ["Compuestos estructurales (descriptores)", f.raw_compounds || 0],
    ["Con potencia útil (≥3 mediciones de unión)", f.with_potency_binding_min_support || 0],
  ];
  const max = Math.max(...steps.map((s) => s[1]), 1);
  document.getElementById("acq-funnel").innerHTML = steps
    .map(([l, v]) => `<div class="fb"><span class="fl">${l}</span>`
      + `<div class="bar" style="width:${Math.max(6, (100 * v) / max)}%">${v}</div></div>`)
    .join("");
  if (f.dropped_no_quantitative != null) {
    document.getElementById("acq-funnel-note").textContent =
      `Se pierden ${f.dropped_no_quantitative} compuestos sin potencia cuantitativa útil. `
      + (f.selection_bias_note || "");
  }

  // ── Resolución (tabla) ─────────────────────────────────────
  const bm = res.by_method || {};
  const total = res.total || Object.values(bm).reduce((a, b) => a + b, 0) || 1;
  const rows = Object.entries(bm).sort((a, b) => b[1] - a[1]);
  const resHtml = `<div class="table-scroll"><table class="data-table">`
    + `<thead><tr><th>Método de resolución</th><th>Compuestos</th><th>% del total</th></tr></thead><tbody>`
    + rows.map(([k, v]) =>
        `<tr><td>${METHOD_ES[k] || k}</td><td>${v}</td><td>${((100 * v) / total).toFixed(1)}%</td></tr>`).join("")
    + `</tbody></table></div>`;
  document.getElementById("acq-resolution").innerHTML = resHtml;

  // ── Muestra de datos crudos + glosario ─────────────────────
  const s = d.sample || { columns: [], rows: [] };
  renderDataTable(document.getElementById("acq-sample"), s.columns, s.rows);
  renderGlossary(document.getElementById("acq-glossary"), s.columns, "Diccionario de columnas de la tabla");
})();
