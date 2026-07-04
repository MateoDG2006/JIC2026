/**
 * Buscador PubChem por nombre — autocomplete con preview de imagen.
 */
document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".search-tab");
    const panelPubchem = document.getElementById("tab-pubchem");
    const panelSmiles = document.getElementById("tab-smiles");
    const input = document.getElementById("pubchem-input");
    const resultsEl = document.getElementById("pubchem-results");
    const statusEl = document.getElementById("pubchem-status");

    if (!input || !resultsEl) return;

    let debounceTimer = null;
    let activeController = null;

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;
            tabs.forEach((t) => {
                const isActive = t.dataset.tab === target;
                t.classList.toggle("active", isActive);
                t.setAttribute("aria-selected", isActive ? "true" : "false");
            });
            if (panelPubchem) panelPubchem.hidden = target !== "pubchem";
            if (panelSmiles) panelSmiles.hidden = target !== "smiles";
        });
    });

    function setStatus(msg, isError = false) {
        if (!statusEl) return;
        if (!msg) {
            statusEl.hidden = true;
            return;
        }
        statusEl.hidden = false;
        statusEl.textContent = msg;
        statusEl.className = isError ? "pubchem-status error" : "pubchem-status";
    }

    function hideResults() {
        resultsEl.hidden = true;
        resultsEl.innerHTML = "";
    }

    function renderResults(results) {
        if (!results.length) {
            resultsEl.innerHTML = '<div class="pubchem-empty">Sin resultados en PubChem</div>';
            resultsEl.hidden = false;
            return;
        }

        resultsEl.innerHTML = results
            .map((r) => {
                const mw = r.molecular_weight != null ? `${Number(r.molecular_weight).toFixed(2)} g/mol` : "";
                const formula = r.formula || "";
                const meta = [formula, mw].filter(Boolean).join(" · ");
                const name = r.name || r.search_term || `CID ${r.cid}`;
                const smilesEnc = encodeURIComponent(r.smiles);
                return `
                <a href="/analyze?smiles=${smilesEnc}" class="pubchem-result-item">
                    <img
                        class="pubchem-thumb"
                        src="${r.image_url}"
                        alt="Estructura ${name}"
                        loading="lazy"
                        width="80"
                        height="80"
                    />
                    <div class="pubchem-result-body">
                        <span class="pubchem-result-name">${escapeHtml(name)}</span>
                        ${meta ? `<span class="pubchem-result-meta">${escapeHtml(meta)}</span>` : ""}
                        <span class="pubchem-result-cid">CID ${r.cid}</span>
                    </div>
                    <span class="pubchem-result-action">Analizar →</span>
                </a>`;
            })
            .join("");
        resultsEl.hidden = false;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    async function search(query) {
        if (activeController) activeController.abort();
        activeController = new AbortController();

        setStatus(query.length === 1 ? "Buscando 10 compuestos aleatorios en PubChem…" : "Buscando en PubChem…");

        try {
            const res = await fetch(
                `/api/pubchem/search?q=${encodeURIComponent(query)}&limit=10`,
                { signal: activeController.signal }
            );
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error en búsqueda");

            setStatus(null);
            renderResults(data.results || []);
        } catch (err) {
            if (err.name === "AbortError") return;
            setStatus(err.message || "No se pudo conectar con PubChem", true);
            hideResults();
        }
    }

    input.addEventListener("input", () => {
        const query = input.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 1) {
            hideResults();
            setStatus(null);
            return;
        }

        debounceTimer = setTimeout(() => search(query), 350);
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            hideResults();
            setStatus(null);
        }
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".pubchem-search-wrap")) {
            hideResults();
        }
    });
});
