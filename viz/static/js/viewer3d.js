/**
 * Visor 3D con 3Dmol.js — colores XAI idénticos al SVG (YlOrRd vía backend).
 */
const MoleculeViewer3D = (function () {
    let viewer = null;
    let containerEl = null;
    let currentStyle = "stick";
    let lastStructure = null;
    let lastFormat = "sdf";
    let lastImportance = null;
    let lastColors = null;
    let atomCount = 0;

    const STYLES = ["stick", "sphere", "line"];
    const NEUTRAL = "#888888";

    function getLib() {
        return window.$3Dmol || window["3Dmol"] || null;
    }

    function isReady() {
        const lib = getLib();
        return Boolean(lib && typeof lib.createViewer === "function");
    }

    function hasCanvas() {
        return Boolean(containerEl?.querySelector("canvas"));
    }

    function isActive() {
        return Boolean(viewer && hasCanvas());
    }

    function parseAtomCount(structure) {
        if (!structure) return 0;
        for (const line of structure.split("\n")) {
            const m = line.match(/^\s*(\d+)\s+\d+/);
            if (m) return parseInt(m[1], 10);
        }
        return 0;
    }

    function showMessage(msg) {
        if (!containerEl) return;
        viewer = null;
        containerEl.innerHTML =
            `<div class="viewer-3d-placeholder">${msg}</div>`;
    }

    function init(containerId = "viewer-3d") {
        const lib = getLib();
        containerEl = document.getElementById(containerId);
        if (!containerEl) return false;

        if (!lib) {
            showMessage("3Dmol.js no cargó. Recarga la página (Ctrl+Shift+R).");
            return false;
        }

        containerEl.innerHTML = "";
        viewer = lib.createViewer(containerEl, {
            backgroundColor: "0x0a0e14",
        });

        if (!window._molViewerResizeBound) {
            window.addEventListener("resize", () => {
                if (!isActive()) return;
                viewer.resize();
                viewer.render();
            });
            window._molViewerResizeBound = true;
        }

        return true;
    }

    function ensureViewer(containerId = "viewer-3d") {
        if (!containerEl) {
            containerEl = document.getElementById(containerId);
        }
        if (!containerEl) return false;
        if (!isReady()) {
            showMessage("3Dmol.js no cargó. Recarga la página (Ctrl+Shift+R).");
            return false;
        }
        if (!isActive()) {
            viewer = null;
            return init(containerId);
        }
        return true;
    }

    function styleForColor(hex, importance) {
        const imp = Number(importance) || 0;
        if (currentStyle === "sphere") {
            return { sphere: { color: hex, scale: 0.22 + imp * 0.18 } };
        }
        if (currentStyle === "line") {
            return { line: { color: hex } };
        }
        return {
            stick: { color: hex, radius: 0.16 },
            sphere: { color: hex, scale: 0.2 + imp * 0.06 },
        };
    }

    /** Aplica colores hex por átomo (mismos que el SVG). */
    function applyAtomColors(hexColors, importance) {
        if (!ensureViewer()) return false;
        if (!hexColors || !hexColors.length) {
            return applyDefaultStyle();
        }

        lastColors = [...hexColors];
        lastImportance = importance ? [...importance] : null;

        const atoms = viewer.selectedAtoms({ model: 0 }) || [];
        const n = Math.min(hexColors.length, atoms.length || atomCount || hexColors.length);

        // Base neutra sin colorscheme por elemento (evita verde/púrpura por defecto)
        viewer.setStyle({}, {
            stick: { radius: 0.1, color: NEUTRAL },
            sphere: { scale: 0.15, color: NEUTRAL },
        });

        for (let i = 0; i < n; i++) {
            const hex = hexColors[i] || NEUTRAL;
            const imp = importance && importance[i] != null ? importance[i] : 0;
            const serial = atoms[i] ? atoms[i].serial : i + 1;
            viewer.setStyle({ serial }, styleForColor(hex, imp));
        }

        viewer.render();
        return true;
    }

    function applyDefaultStyle() {
        if (!ensureViewer()) return false;
        lastColors = null;
        lastImportance = null;
        viewer.setStyle({}, { stick: { colorscheme: "greenCarbon" } });
        viewer.render();
        return true;
    }

    function loadStructure(structure, format, importance, hexColors, containerId = "viewer-3d") {
        if (!structure) {
            showMessage("Sin estructura 3D disponible");
            return false;
        }
        if (!ensureViewer(containerId)) return false;

        lastStructure = structure;
        lastFormat = format || "sdf";
        atomCount = parseAtomCount(structure);

        try {
            viewer.removeAllModels();
            viewer.removeAllShapes();
            viewer.addModel(structure, lastFormat);

            if (hexColors && hexColors.length) {
                applyAtomColors(hexColors, importance);
            } else if (importance && importance.length) {
                return false;
            } else {
                applyDefaultStyle();
            }

            viewer.zoomTo();
            viewer.resize();
            viewer.render();
            return true;
        } catch (err) {
            console.error("[viewer3d]", err);
            showMessage("Error al cargar estructura 3D");
            return false;
        }
    }

    function highlightAtom(atomIdx) {
        if (!isActive() || !lastColors) return;
        applyAtomColors(lastColors, lastImportance);
        const atoms = viewer.selectedAtoms({ model: 0 }) || [];
        const serial = atoms[atomIdx] ? atoms[atomIdx].serial : atomIdx + 1;
        viewer.setStyle(
            { serial },
            { stick: { color: "#3b82f6", radius: 0.28 }, sphere: { color: "#3b82f6", scale: 0.42 } }
        );
        viewer.render();
    }

    function toggleStyle() {
        currentStyle = STYLES[(STYLES.indexOf(currentStyle) + 1) % STYLES.length];
        if (lastColors) {
            applyAtomColors(lastColors, lastImportance);
        } else {
            applyDefaultStyle();
        }
        return currentStyle;
    }

    function resetView() {
        if (!isActive()) return;
        viewer.zoomTo();
        viewer.render();
    }

    return {
        isReady,
        isActive,
        init,
        loadStructure,
        applyAtomColors,
        applyDefaultStyle,
        highlightAtom,
        toggleStyle,
        resetView,
    };
})();
