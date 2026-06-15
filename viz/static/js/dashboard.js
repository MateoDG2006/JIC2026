/**
 * Dashboard — filtros del corpus y estado del modelo.
 */
document.addEventListener("DOMContentLoaded", async () => {
    const grid = document.getElementById("corpus-grid");
    const filterRisk = document.getElementById("filter-risk");
    const filterFamily = document.getElementById("filter-family");
    const filterText = document.getElementById("filter-text");
    const statusEl = document.getElementById("model-status");

    if (grid) {
        const families = new Set();
        grid.querySelectorAll(".corpus-card").forEach((card) => {
            const f = card.dataset.family;
            if (f) families.add(f);
        });
        [...families].sort().forEach((f) => {
            const opt = document.createElement("option");
            opt.value = f;
            opt.textContent = f;
            filterFamily.appendChild(opt);
        });

        function applyFilters() {
            const risk = filterRisk?.value || "";
            const family = filterFamily?.value || "";
            const text = (filterText?.value || "").toLowerCase();

            grid.querySelectorAll(".corpus-card").forEach((card) => {
                const matchRisk = !risk || card.dataset.risk === risk;
                const matchFamily = !family || card.dataset.family === family;
                const matchText = !text || card.dataset.name.includes(text);
                card.style.display = matchRisk && matchFamily && matchText ? "" : "none";
            });
        }

        filterRisk?.addEventListener("change", applyFilters);
        filterFamily?.addEventListener("change", applyFilters);
        filterText?.addEventListener("input", applyFilters);
    }

    if (statusEl) {
        try {
            const res = await fetch("/api/status");
            const status = await res.json();
            statusEl.hidden = false;

            if (status.model_available) {
                statusEl.className = "status-banner ok";
                statusEl.textContent = `Modelo disponible (${status.device}). Inferencia en vivo habilitada.`;
            } else {
                statusEl.className = "status-banner warn";
                statusEl.textContent =
                    "Modelo no encontrado — solo corpus pre-computado. Ejecuta: make train-gin";
            }
        } catch {
            /* ignore */
        }
    }
});
