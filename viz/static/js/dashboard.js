/**
 * Dashboard — filtros del corpus Panamá y acordeón por familia (<details>).
 */
document.addEventListener("DOMContentLoaded", async () => {
    const corpusRoot = document.getElementById("corpus-by-family");
    const filterFamily = document.getElementById("filter-family");
    const filterText = document.getElementById("filter-text");
    const filterMida = document.getElementById("filter-mida");
    const countEl = document.getElementById("corpus-count");
    const statusEl = document.getElementById("model-status");
    const btnExpandAll = document.getElementById("btn-expand-all");
    const btnCollapseAll = document.getElementById("btn-collapse-all");

    function setFamilyOpen(block, open) {
        if (block && "open" in block) {
            block.open = open;
        }
    }

    if (corpusRoot) {
        btnExpandAll?.addEventListener("click", () => {
            corpusRoot.querySelectorAll(".corpus-family-block").forEach((block) => {
                if (block.style.display !== "none") setFamilyOpen(block, true);
            });
        });

        btnCollapseAll?.addEventListener("click", () => {
            corpusRoot.querySelectorAll(".corpus-family-block").forEach((block) => {
                setFamilyOpen(block, false);
            });
        });

        function applyFilters() {
            const family = filterFamily?.value || "";
            const text = (filterText?.value || "").toLowerCase();
            const midaOnly = Boolean(filterMida?.checked);
            const filtering = Boolean(family || text || midaOnly);
            let visible = 0;

            corpusRoot.querySelectorAll(".corpus-family-block").forEach((block) => {
                const blockFamily = block.dataset.family || "";
                let blockVisible = 0;

                block.querySelectorAll(".corpus-card").forEach((card) => {
                    const matchFamily = !family || card.dataset.family === family;
                    const matchMida = !midaOnly || card.dataset.mida === "true";
                    const haystack = `${card.dataset.name || ""} ${card.dataset.formula || ""}`;
                    const matchText = !text || haystack.includes(text);
                    const show = matchFamily && matchMida && matchText;
                    card.style.display = show ? "" : "none";
                    if (show) blockVisible += 1;
                });

                const showBlock = blockVisible > 0 && (!family || blockFamily === family);
                block.style.display = showBlock ? "" : "none";
                visible += blockVisible;

                if (showBlock && filtering) {
                    setFamilyOpen(block, true);
                }
            });

            if (countEl) countEl.textContent = String(visible);
        }

        filterFamily?.addEventListener("change", applyFilters);
        filterText?.addEventListener("input", applyFilters);
        filterMida?.addEventListener("change", applyFilters);
    }

    if (statusEl) {
        try {
            const res = await fetch("/api/status");
            const status = await res.json();
            statusEl.hidden = false;

            if (status.model_available) {
                statusEl.className = "status-banner ok";
                statusEl.textContent =
                    `Modelo GIN disponible (${status.device}). Selecciona un compuesto del corpus para predecir en vivo.`;
            } else {
                statusEl.className = "status-banner warn";
                statusEl.textContent =
                    "Modelo no encontrado. Entrena el GIN con: make train-gin";
            }
        } catch {
            /* ignore */
        }
    }
});
