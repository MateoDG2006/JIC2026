/**
 * Buscador unificado: PubChem por nombre | SMILES.
 * Prefetch de 20 compuestos del corpus resueltos en PubChem.
 */
document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".search-tab");
    const panelPubchem = document.getElementById("tab-pubchem");
    const panelSmiles = document.getElementById("tab-smiles");
    const input = document.getElementById("pubchem-input");
    const smilesInput = document.getElementById("smiles-input");
    const form = document.getElementById("search-form");
    const actionBtn = document.getElementById("search-action-btn");
    const resultsEl = document.getElementById("pubchem-results");
    const labelEl = actionBtn?.querySelector(".btn-label");
    const icoWrap = actionBtn?.querySelector(".btn-ico-wrap");

    if (!tabs.length) return;

    let mode = "pubchem";
    let debounceTimer = null;
    let activeController = null;
    let randomCache = [];
    let randomReady = false;
    let randomLoading = null;

    const CACHE_KEY = "gnntox-pubchem-random-v3";
    const CACHE_TTL_MS = 60 * 60 * 1000;
    const RANDOM_LIMIT = 20;
    const RANDOM_URL = "/api/pubchem/random";

    function notify(message, variant = "warn") {
        if (window.GnnToxToast?.showToast) {
            window.GnnToxToast.showToast(message, variant, 5500);
        }
    }

    function setActionIcon(name) {
        if (!icoWrap) return;
        icoWrap.innerHTML = `<i data-lucide="${name}" class="btn-ico" aria-hidden="true"></i>`;
        if (window.lucide) {
            try {
                lucide.createIcons({ nodes: [icoWrap] });
            } catch (_) {
                lucide.createIcons();
            }
        }
    }

    function setMode(target) {
        mode = target;
        tabs.forEach((t) => {
            const isActive = t.dataset.tab === target;
            t.classList.toggle("active", isActive);
            t.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        if (panelPubchem) panelPubchem.hidden = target !== "pubchem";
        if (panelSmiles) panelSmiles.hidden = target !== "smiles";

        if (labelEl) labelEl.textContent = target === "smiles" ? "Analizar" : "Buscar";
        setActionIcon(target === "smiles" ? "flask-conical" : "search");

        if (target === "pubchem") {
            hideResults();
            input?.focus();
        } else {
            hideResults();
            smilesInput?.focus();
        }
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => setMode(tab.dataset.tab));
    });

    function hideResults() {
        if (!resultsEl) return;
        resultsEl.hidden = true;
        resultsEl.innerHTML = "";
    }

    function renderResults(results) {
        if (!resultsEl) return;
        if (!results.length) {
            resultsEl.innerHTML =
                '<div class="pubchem-empty">Sin resultados en PubChem</div>';
            resultsEl.hidden = false;
            return;
        }

        resultsEl.innerHTML = results
            .map((r) => {
                const mw =
                    r.molecular_weight != null
                        ? `${Number(r.molecular_weight).toFixed(2)} g/mol`
                        : "";
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

    function errorMessage(err, data) {
        const detail = data?.detail;
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) {
            return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
        }
        if (err?.message && !/^\d{3}\b/.test(err.message)) return err.message;
        return "No se pudo completar la búsqueda en PubChem.";
    }

    function readSessionCache() {
        try {
            const raw = sessionStorage.getItem(CACHE_KEY);
            if (!raw) return null;
            const data = JSON.parse(raw);
            if (!data || !Array.isArray(data.results) || !data.results.length) return null;
            if (Date.now() - (data.ts || 0) > CACHE_TTL_MS) return null;
            return data.results;
        } catch {
            return null;
        }
    }

    function writeSessionCache(results) {
        try {
            sessionStorage.setItem(
                CACHE_KEY,
                JSON.stringify({ ts: Date.now(), results })
            );
        } catch {
            /* ignore */
        }
    }

    async function ensureRandomCache() {
        if (randomReady && randomCache.length) return randomCache;
        if (randomLoading) return randomLoading;

        const fromSession = readSessionCache();
        if (fromSession?.length) {
            randomCache = fromSession.slice(0, RANDOM_LIMIT);
            randomReady = true;
            return randomCache;
        }

        randomLoading = (async () => {
            const res = await fetch(`${RANDOM_URL}?limit=${RANDOM_LIMIT}`);
            let data = {};
            try {
                data = await res.json();
            } catch {
                data = {};
            }
            if (res.status === 404) {
                throw new Error(
                    "Endpoint de sugerencias no disponible. Reiniciá el servidor (make viz)."
                );
            }
            if (!res.ok) {
                throw new Error(errorMessage(null, data));
            }
            randomCache = (data.results || []).slice(0, RANDOM_LIMIT);
            randomReady = randomCache.length > 0;
            if (randomReady) writeSessionCache(randomCache);
            return randomCache;
        })();

        try {
            return await randomLoading;
        } finally {
            randomLoading = null;
        }
    }

    function showRandomIfEmpty() {
        if (mode !== "pubchem" || !input) return;
        if (input.value.trim().length > 0) return;

        if (randomReady && randomCache.length) {
            renderResults(randomCache);
            return;
        }

        ensureRandomCache()
            .then((results) => {
                if (mode !== "pubchem") return;
                if (input.value.trim().length > 0) return;
                if (results?.length) renderResults(results);
            })
            .catch((err) => {
                if (mode !== "pubchem") return;
                notify(errorMessage(err), "warn");
            });
    }

    ensureRandomCache().catch((err) => {
        notify(errorMessage(err), "warn");
    });

    async function search(query) {
        if (!query || !resultsEl) return;
        if (activeController) activeController.abort();
        activeController = new AbortController();

        try {
            const res = await fetch(
                `/api/pubchem/search?q=${encodeURIComponent(query)}&limit=${RANDOM_LIMIT}`,
                { signal: activeController.signal }
            );
            let data = {};
            try {
                data = await res.json();
            } catch {
                data = {};
            }
            if (!res.ok) throw new Error(errorMessage(null, data));
            renderResults(data.results || []);
        } catch (err) {
            if (err.name === "AbortError") return;
            notify(errorMessage(err), "warn");
            hideResults();
        }
    }

    function runAction() {
        if (mode === "smiles") {
            const smi = (smilesInput?.value || "").trim();
            if (!smi) {
                smilesInput?.focus();
                return;
            }
            form?.requestSubmit?.() || form?.submit();
            return;
        }
        const query = (input?.value || "").trim();
        if (query.length < 1) {
            showRandomIfEmpty();
            input?.focus();
            return;
        }
        search(query);
    }

    actionBtn?.addEventListener("click", runAction);

    form?.addEventListener("submit", (e) => {
        const smi = (smilesInput?.value || "").trim();
        if (!smi) {
            e.preventDefault();
            smilesInput?.focus();
        }
    });

    input?.addEventListener("input", () => {
        if (mode !== "pubchem") return;
        const query = input.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 1) {
            showRandomIfEmpty();
            return;
        }

        debounceTimer = setTimeout(() => search(query), 350);
    });

    input?.addEventListener("focus", showRandomIfEmpty);
    input?.addEventListener("mouseenter", showRandomIfEmpty);

    input?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            runAction();
        }
        if (e.key === "Escape") hideResults();
    });

    smilesInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            runAction();
        }
    });

    document.addEventListener("click", (e) => {
        if (
            !e.target.closest(".pubchem-search-wrap") &&
            !e.target.closest("#search-action-btn")
        ) {
            hideResults();
        }
    });

    setMode("pubchem");
});
