// Helpers compartidos del dashboard analytics (glosario + tablas en español)
window.Glossary = { columns: {}, metrics: {} };

async function loadGlossary() {
  if (Object.keys(window.Glossary.columns).length) return window.Glossary;
  try {
    const r = await fetch("/api/analytics/glossary");
    window.Glossary = await r.json();
  } catch (e) { console.error("glossary", e); }
  return window.Glossary;
}

function colLabel(col) {
  const g = window.Glossary.columns[col];
  return g ? g.es : col;
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Tabla de datos con encabezados legibles en español (tooltip = descripción)
function renderDataTable(el, columns, rows) {
  const g = window.Glossary.columns || {};
  const head = columns.map((c) => {
    const info = g[c] || {};
    const t = info.desc ? ` title="${esc(info.desc)}"` : "";
    return `<th${t}>${esc(info.es || c)}<span class="col-code">${esc(c)}</span></th>`;
  }).join("");
  const body = rows.map((row) => {
    const tds = columns.map((c) => {
      let v = row[c];
      if (v === null || v === undefined || v === "") v = "—";
      const cens = (c === "standard_relation" && v !== "=") ? ' class="cens"' : "";
      return `<td${cens}>${esc(v)}</td>`;
    }).join("");
    return `<tr>${tds}</tr>`;
  }).join("");
  el.innerHTML = `<div class="table-scroll"><table class="data-table">`
    + `<thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

// Tabla-glosario desplegable que explica cada columna en español
function renderGlossary(el, columns, title) {
  const g = window.Glossary.columns || {};
  const rows = columns.map((c) => {
    const info = g[c] || {};
    return `<tr><td class="mono">${esc(c)}</td><td><strong>${esc(info.es || c)}</strong></td>`
      + `<td>${esc(info.desc || "")}</td><td class="mono muted">${esc(info.ej || "")}</td></tr>`;
  }).join("");
  el.innerHTML = `<details class="glossary"><summary>${esc(title || "Diccionario de columnas")} — clic para desplegar</summary>`
    + `<div class="table-scroll"><table class="data-table">`
    + `<thead><tr><th>Columna (código)</th><th>Nombre</th><th>Qué significa</th><th>Ejemplo</th></tr></thead>`
    + `<tbody>${rows}</tbody></table></div></details>`;
}

// Explica una lista de métricas (usa el bloque metrics del glosario)
function renderMetricGlossary(el, keys, title) {
  const m = window.Glossary.metrics || {};
  const rows = keys.map((k) => {
    const info = m[k] || {};
    return `<tr><td><strong>${esc(info.es || k)}</strong></td><td>${esc(info.desc || "")}</td></tr>`;
  }).join("");
  el.innerHTML = `<details class="glossary"><summary>${esc(title || "Qué significa cada métrica")} — clic para desplegar</summary>`
    + `<div class="table-scroll"><table class="data-table">`
    + `<thead><tr><th>Métrica</th><th>Qué significa</th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
}

function buildComboLabel(item, getLabel) {
  if (typeof getLabel === "function") return getLabel(item);
  if (typeof item === "string") return item;
  return item.label || item.compound_name || item.name || item.value || "";
}

function setupComboBox(root, items, opts = {}) {
  if (!root) return null;
  const {
    placeholder = "Buscar...",
    getLabel = null,
    getValue = null,
    getMeta = null,
    onSelect = null,
    emptyText = "Sin coincidencias",
    limit = 100,
  } = opts;

  root.classList.add("combo");
  root.innerHTML = `
    <div class="combo-shell">
      <input type="text" class="combo-input" placeholder="${esc(placeholder)}" autocomplete="off">
      <button type="button" class="combo-toggle" aria-label="Mostrar opciones">▾</button>
    </div>
    <div class="combo-panel hidden"></div>
  `;

  const input = root.querySelector(".combo-input");
  const toggle = root.querySelector(".combo-toggle");
  const panel = root.querySelector(".combo-panel");
  let currentItems = Array.isArray(items) ? items.slice() : [];
  let filtered = currentItems.slice();
  let selected = null;

  function valueOf(item) {
    if (typeof getValue === "function") return getValue(item);
    if (typeof item === "string") return item;
    return item.value || item.compound_name || item.name || item.label || "";
  }

  function render(list) {
    filtered = list.slice(0, limit);
    if (!filtered.length) {
      panel.innerHTML = `<div class="combo-empty">${esc(emptyText)}</div>`;
      return;
    }
    panel.innerHTML = filtered.map((item, idx) => {
      const label = buildComboLabel(item, getLabel);
      const value = valueOf(item);
      const meta = typeof getMeta === "function" ? getMeta(item) : "";
      return `<button type="button" class="combo-option" data-idx="${idx}" data-value="${esc(value)}">
        <span class="combo-option-main">${esc(label)}</span>
        ${meta ? `<span class="combo-option-meta">${meta}</span>` : ""}
      </button>`;
    }).join("");
  }

  function open() {
    panel.classList.remove("hidden");
    root.classList.add("open");
  }

  function close() {
    panel.classList.add("hidden");
    root.classList.remove("open");
  }

  function choose(item) {
    selected = item;
    input.value = valueOf(item);
    close();
    if (typeof onSelect === "function") onSelect(item);
  }

  function filter(query) {
    const q = String(query || "").trim().toLowerCase();
    if (!q) {
      render(currentItems);
      return;
    }
    render(currentItems.filter((item) => {
      const label = buildComboLabel(item, getLabel).toLowerCase();
      const value = valueOf(item).toLowerCase();
      const meta = typeof getMeta === "function"
        ? String(getMeta(item)).replace(/<[^>]+>/g, "").toLowerCase()
        : "";
      return label.includes(q) || value.includes(q) || meta.includes(q);
    }));
  }

  input.addEventListener("focus", () => {
    filter(input.value);
    open();
  });
  input.addEventListener("input", () => {
    filter(input.value);
    open();
  });
  toggle.addEventListener("click", () => {
    if (panel.classList.contains("hidden")) {
      filter(input.value);
      open();
    } else {
      close();
    }
  });
  panel.addEventListener("click", (e) => {
    const btn = e.target.closest(".combo-option");
    if (!btn) return;
    const item = filtered[Number(btn.dataset.idx)];
    if (item) choose(item);
  });
  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) close();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });

  render(currentItems);

  return {
    input,
    panel,
    getValue: () => input.value.trim(),
    getSelected: () => selected,
    setItems(nextItems) {
      currentItems = Array.isArray(nextItems) ? nextItems.slice() : [];
      filter(input.value);
    },
    setValue(value) {
      input.value = value || "";
      filter(input.value);
    },
    open,
    close,
  };
}
