/**
 * Dashboard — tags, toasts, filtros corpus y previews 3D lazy.
 */
document.addEventListener("DOMContentLoaded", async () => {
    const corpusRoot = document.getElementById("corpus-by-family");
    const filterText = document.getElementById("filter-text");
    const countEl = document.getElementById("corpus-count");
    const tagBar = document.getElementById("tag-bar");
    const btnExpandAll = document.getElementById("btn-expand-all");
    const btnCollapseAll = document.getElementById("btn-collapse-all");

    function setFamilyOpen(block, open) {
        if (block && "open" in block) {
            block.open = open;
        }
    }

    function getTagState() {
        const midaOnly = Boolean(
            tagBar?.querySelector('.filter-tag[data-tag="mida"][aria-pressed="true"]')
        );
        const families = [
            ...document.querySelectorAll(
                '.filter-tag[data-tag="family"][aria-pressed="true"]'
            ),
        ].map((t) => t.dataset.family);
        return { midaOnly, families };
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
            const { midaOnly, families } = getTagState();
            const text = (filterText?.value || "").toLowerCase();
            const filtering = Boolean(midaOnly || families.length || text);
            let visible = 0;

            corpusRoot.querySelectorAll(".corpus-family-block").forEach((block) => {
                const blockFamily = block.dataset.family || "";
                let blockVisible = 0;

                block.querySelectorAll(".corpus-card").forEach((card) => {
                    const matchFamily =
                        !families.length || families.includes(card.dataset.family);
                    const matchMida = !midaOnly || card.dataset.mida === "true";
                    const haystack = `${card.dataset.name || ""} ${card.dataset.formula || ""}`;
                    const matchText = !text || haystack.includes(text);
                    const show = matchFamily && matchMida && matchText;
                    card.style.display = show ? "" : "none";
                    if (show) blockVisible += 1;
                });

                const familyAllowed =
                    !families.length || families.includes(blockFamily);
                const showBlock = blockVisible > 0 && familyAllowed;
                block.style.display = showBlock ? "" : "none";
                visible += blockVisible;

                if (showBlock && filtering) {
                    setFamilyOpen(block, true);
                }
            });

            if (countEl) countEl.textContent = String(visible);
        }

        tagBar?.querySelectorAll(".filter-tag").forEach((tag) => {
            tag.addEventListener("click", () => {
                const on = tag.getAttribute("aria-pressed") === "true";
                tag.setAttribute("aria-pressed", on ? "false" : "true");
                tag.classList.toggle("on", !on);
                applyFilters();
            });
        });

        filterText?.addEventListener("input", applyFilters);

        initCorpusMolPreviews(corpusRoot);
    }

    // Model status as side toast on every visit / refresh
    try {
        const res = await fetch("/api/status");
        const status = await res.json();

        if (status.model_available) {
            window.GnnToxToast?.showToast(
                `Modelo GIN disponible (${status.device}). Seleccioná un compuesto para predecir en vivo.`,
                "ok",
                5200
            );
        } else {
            window.GnnToxToast?.showToast(
                "Modelo no disponible. Ejecuta: make train-gin",
                "warn",
                7000
            );
        }
    } catch {
        window.GnnToxToast?.showToast(
            "No se pudo verificar el estado del modelo.",
            "warn",
            5000
        );
    }
});

function cssColorToHex(raw) {
    const s = (raw || "").trim();
    if (s.startsWith("#")) {
        return s.length === 4
            ? `#${s[1]}${s[1]}${s[2]}${s[2]}${s[3]}${s[3]}`
            : s.slice(0, 7);
    }
    const m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (m) {
        const hex = (n) => Number(n).toString(16).padStart(2, "0");
        return `#${hex(m[1])}${hex(m[2])}${hex(m[3])}`;
    }
    return "#0a0e14";
}

function initCorpusMolPreviews(root) {
    const lib = window.$3Dmol || window["3Dmol"];
    const nodes = [...root.querySelectorAll(".corpus-mol-preview[data-smiles]")];
    if (!nodes.length) return;

    async function mount(el) {
        if (el.dataset.mounted === "1") return;
        el.dataset.mounted = "1";
        const smiles = el.dataset.smiles;
        if (!smiles) {
            el.classList.add("error");
            el.innerHTML = `<span class="corpus-mol-loading">Sin SMILES</span>`;
            return;
        }
        if (!lib || typeof lib.createViewer !== "function") {
            el.classList.add("error");
            el.innerHTML = `<span class="corpus-mol-loading">3D no disponible</span>`;
            return;
        }
        try {
            const res = await fetch(
                `/api/mol3d?smiles=${encodeURIComponent(smiles)}`
            );
            if (!res.ok) throw new Error("mol3d " + res.status);
            const data = await res.json();
            const block = data.sdf || data.mol_block;
            if (!block) throw new Error("sin estructura");

            const bg = cssColorToHex(
                getComputedStyle(document.documentElement).getPropertyValue(
                    "--viewer-bg"
                )
            );
            el.innerHTML = "";
            el.classList.add("ready");
            const viewer = lib.createViewer(el, {
                backgroundColor: bg,
                antialias: true,
                disableFog: true,
                nomouse: true,
            });
            viewer.addModel(block, data.sdf ? "sdf" : "mol");
            viewer.setStyle(
                {},
                {
                    stick: { colorscheme: "Jmol", radius: 0.16 },
                    sphere: { colorscheme: "Jmol", scale: 0.28 },
                }
            );
            viewer.zoomTo();
            viewer.zoom(1.05, 0);
            viewer.render();
            el._viewer = viewer;

            const ro = new ResizeObserver(() => {
                try {
                    viewer.resize();
                    viewer.render();
                } catch (_) {}
            });
            ro.observe(el);
        } catch (err) {
            console.warn("corpus mol preview", err);
            el.classList.add("error");
            el.classList.remove("ready");
            el.innerHTML = `<span class="corpus-mol-loading">Sin preview</span>`;
        }
    }

    const io = new IntersectionObserver(
        (entries) => {
            entries.forEach((en) => {
                if (en.isIntersecting) {
                    mount(en.target);
                    io.unobserve(en.target);
                }
            });
        },
        { rootMargin: "120px 0px", threshold: 0.05 }
    );

    root.querySelectorAll(".corpus-family-block").forEach((block) => {
        block.addEventListener("toggle", () => {
            if (!block.open) return;
            block
                .querySelectorAll(".corpus-mol-preview:not([data-mounted='1'])")
                .forEach((el) => {
                    if (el.closest(".corpus-card")?.style.display === "none") return;
                    io.observe(el);
                });
        });
    });

    nodes.forEach((el) => {
        const card = el.closest(".corpus-card");
        const details = el.closest("details");
        if (details && !details.open) return;
        if (card && card.style.display === "none") return;
        io.observe(el);
    });

    document.addEventListener("gnntox-theme", () => {
        const bg = cssColorToHex(
            getComputedStyle(document.documentElement).getPropertyValue(
                "--viewer-bg"
            )
        );
        root.querySelectorAll(".corpus-mol-preview").forEach((el) => {
            if (!el._viewer) return;
            try {
                el._viewer.setBackgroundColor(bg);
                el._viewer.render();
            } catch (_) {}
        });
    });
}
