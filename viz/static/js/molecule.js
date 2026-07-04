/**
 * Página de molécula — predicciones, XAI interactivo, 3D + 2D.
 */
document.addEventListener("DOMContentLoaded", () => {
    const app = document.getElementById("molecule-app");
    if (!app) return;

    const TASKS = JSON.parse(app.dataset.tasks || "[]");
    const TASK_DESC = JSON.parse(app.dataset.taskDescriptions || "{}");
    const fromCorpus = app.dataset.fromCorpus === "true";
    const liveAnalysis = app.dataset.liveAnalysis === "true";
    const compoundId = app.dataset.compoundId;
    let smiles = app.dataset.smiles || "";
    const initialName = app.dataset.compoundName || "";
    const initialFamily = app.dataset.family || "";

    let state = {
        predictions: {},
        xai: { gradcam: {}, gnnexplainer: {} },
        xaiColors: { gradcam: {}, gnnexplainer: {} },
        atomSymbols: [],
        properties: null,
        molBlock: null,
        molFormat: "sdf",
        currentMethod: "gradcam",
        currentTask: null,
    };

    const els = {
        loading: document.getElementById("loading"),
        loadingMsg: document.getElementById("loading-msg"),
        error: document.getElementById("error-banner"),
        viewer3d: document.getElementById("viewer-3d"),
        viewer3dStatus: document.getElementById("viewer-3d-status"),
        predictionsChart: document.getElementById("predictions-chart"),
        taskSelect: document.getElementById("task-select"),
        btnRunXai: document.getElementById("btn-run-xai"),
        atomsSection: document.getElementById("atoms-section"),
        atomsTable: document.querySelector("#atoms-table tbody"),
        colGnnexp: document.getElementById("col-gnnexp"),
        propsSection: document.getElementById("props-section"),
        propsGrid: document.getElementById("props-grid"),
        viewer2d: document.getElementById("viewer-2d"),
        riskBadge: document.getElementById("risk-badge"),
        demoBanner: document.getElementById("demo-banner"),
        demoPredictionsNote: document.getElementById("demo-predictions-note"),
        compoundName: document.getElementById("compound-name"),
        breadcrumbName: document.getElementById("breadcrumb-name"),
        smilesDisplay: document.getElementById("smiles-display"),
    };

    function setViewer3dStatus(msg) {
        if (!els.viewer3dStatus) return;
        if (msg) {
            els.viewer3dStatus.textContent = msg;
            els.viewer3dStatus.hidden = false;
        } else {
            els.viewer3dStatus.hidden = true;
        }
    }

    if (!MoleculeViewer3D.isReady()) {
        showError("3Dmol.js no cargó. Recarga la página (Ctrl+Shift+R).");
    }

    document.getElementById("btn-reset-view")?.addEventListener("click", () => {
        MoleculeViewer3D.resetView();
    });

    document.getElementById("btn-toggle-style")?.addEventListener("click", (e) => {
        const style = MoleculeViewer3D.toggleStyle();
        e.target.textContent = `Estilo: ${style}`;
    });

    async function downloadStl(style, btnId, defaultLabel) {
        if (!smiles) {
            showError("No hay SMILES disponible para exportar.");
            return;
        }
        const btn = document.getElementById(btnId);
        const originalText = btn?.textContent;
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Generando…";
        }
        try {
            const compoundName =
                els.compoundName?.textContent?.trim() || "molecule";
            const url =
                `/api/stl?smiles=${encodeURIComponent(smiles)}` +
                `&name=${encodeURIComponent(compoundName)}` +
                `&style=${encodeURIComponent(style)}`;
            const res = await fetch(url);
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || "No se pudo generar el STL");
            }
            const blob = await res.blob();
            const filename =
                res.headers
                    .get("Content-Disposition")
                    ?.match(/filename="([^"]+)"/)?.[1] || "molecule.stl";
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.click();
            URL.revokeObjectURL(link.href);
        } catch (e) {
            showError(e.message);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText || defaultLabel;
            }
        }
    }

    document.getElementById("btn-download-stl")?.addEventListener("click", () => {
        downloadStl("ballstick", "btn-download-stl", "↓ STL 3D");
    });

    document.getElementById("btn-download-stl-flat")?.addEventListener("click", () => {
        downloadStl("flat_keychain", "btn-download-stl-flat", "↓ STL llavero");
    });

    document.querySelectorAll("[data-method]").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("[data-method]").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.currentMethod = btn.dataset.method;
            refreshXaiView();
        });
    });

    els.taskSelect?.addEventListener("change", () => {
        state.currentTask = els.taskSelect.value;
        highlightPredictionRow(state.currentTask);
        refreshXaiView();
    });

    els.btnRunXai?.addEventListener("click", () => runXai(state.currentMethod === "compare" ? "both" : state.currentMethod));

    els.predictionsChart?.addEventListener("click", (e) => {
        const row = e.target.closest(".pred-row");
        if (!row) return;
        const task = row.dataset.task;
        if (task && els.taskSelect) {
            els.taskSelect.value = task;
            state.currentTask = task;
            highlightPredictionRow(task);
            refreshXaiView();
        }
    });

    function showLoading(msg) {
        els.loadingMsg.textContent = msg || "Cargando…";
        els.loading.hidden = false;
    }

    function hideLoading() {
        els.loading.hidden = true;
    }

    function showError(msg) {
        els.error.textContent = msg;
        els.error.hidden = false;
    }

    function hideError() {
        els.error.hidden = true;
    }

    function riskLevel(maxProb) {
        if (maxProb > 0.7) return { label: "ALTO", cls: "risk-alto" };
        if (maxProb > 0.4) return { label: "MODERADO", cls: "risk-moderado" };
        return { label: "BAJO", cls: "risk-bajo" };
    }

    function renderPredictions(predictions) {
        if (!els.predictionsChart) return;
        els.predictionsChart.innerHTML = "";

        const sorted = TASKS.map((t) => ({ task: t, prob: predictions[t] ?? 0 }))
            .sort((a, b) => b.prob - a.prob);

        sorted.forEach(({ task, prob }) => {
            const row = document.createElement("div");
            row.className = "pred-row";
            row.dataset.task = task;
            row.title = TASK_DESC[task] || task;

            let barClass = "low";
            if (prob > 0.7) barClass = "high";
            else if (prob > 0.4) barClass = "mid";

            const desc = TASK_DESC[task] || "";
            row.innerHTML = `
                <span class="pred-name">
                    <span class="pred-code">${task}</span>
                    ${desc ? `<span class="pred-desc">${desc}</span>` : ""}
                </span>
                <div class="pred-bar-wrap"><div class="pred-bar ${barClass}" style="width:${(prob * 100).toFixed(1)}%"></div></div>
                <span class="pred-value">${(prob * 100).toFixed(0)}%</span>
            `;
            els.predictionsChart.appendChild(row);
        });

        const topTask = sorted[0]?.task;
        if (topTask && !state.currentTask) {
            state.currentTask = topTask;
            if (els.taskSelect) els.taskSelect.value = topTask;
        }
        highlightPredictionRow(state.currentTask);

        const maxProb = sorted[0]?.prob ?? 0;
        const risk = riskLevel(maxProb);
        if (els.riskBadge) {
            els.riskBadge.textContent = risk.label;
            els.riskBadge.className = `risk-badge ${risk.cls}`;
            els.riskBadge.hidden = false;
        }
    }

    function highlightPredictionRow(task) {
        els.predictionsChart?.querySelectorAll(".pred-row").forEach((r) => {
            r.classList.toggle("selected", r.dataset.task === task);
        });
    }

    function renderProperties(props) {
        if (!props || !els.propsGrid) return;
        els.propsSection.hidden = false;
        const fields = [
            ["Peso molecular", `${props.molecular_weight} g/mol`],
            ["Fórmula", props.formula],
            ["LogP", props.logp],
            ["TPSA", `${props.tpsa} Ų`],
            ["HBD / HBA", `${props.hbd} / ${props.hba}`],
            ["Átomos", props.num_atoms],
        ];
        els.propsGrid.innerHTML = fields
            .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`)
            .join("");
    }

    function getCurrentImportance() {
        const task = state.currentTask;
        if (!task) return null;

        if (state.currentMethod === "compare") {
            const gc = state.xai.gradcam[task];
            return gc || state.xai.gnnexplainer[task] || null;
        }
        if (state.currentMethod === "gnnexplainer") {
            return state.xai.gnnexplainer[task] || null;
        }
        return state.xai.gradcam[task] || null;
    }

    function getActiveXaiMethod() {
        if (state.currentMethod === "gnnexplainer") return "gnnexplainer";
        return "gradcam";
    }

    function getCurrentColors() {
        const task = state.currentTask;
        if (!task) return null;

        if (state.currentMethod === "compare") {
            return (
                state.xaiColors.gradcam[task] ||
                state.xaiColors.gnnexplainer[task] ||
                null
            );
        }
        return state.xaiColors[getActiveXaiMethod()][task] || null;
    }

    async function fetchXaiColors(importance) {
        if (!importance?.length) return null;
        try {
            const res = await fetch("/api/xai-colors", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ importance }),
            });
            if (!res.ok) return null;
            const data = await res.json();
            return data.atom_colors || null;
        } catch {
            return null;
        }
    }

    async function ensureCurrentColors() {
        const imp = getCurrentImportance();
        if (!imp) return null;

        let colors = getCurrentColors();
        if (colors) return colors;

        colors = await fetchXaiColors(imp);
        if (!colors) return null;

        const method = getActiveXaiMethod();
        if (!state.xaiColors[method]) state.xaiColors[method] = {};
        state.xaiColors[method][state.currentTask] = colors;
        return colors;
    }

    /** Sincroniza coloreado XAI en visor 3D + SVG 2D + tabla de átomos. */
    async function refreshXaiView() {
        const imp = getCurrentImportance();
        const colors = imp ? await ensureCurrentColors() : null;

        if (state.molBlock) {
            if (colors && imp) {
                MoleculeViewer3D.applyAtomColors(colors, imp);
            } else {
                MoleculeViewer3D.applyDefaultStyle();
            }
        }
        updateAtomsTable();
        await update2dSvg();
    }

    function updateAtomsTable() {
        const task = state.currentTask;
        if (!task || !state.atomSymbols.length) {
            els.atomsSection.hidden = true;
            return;
        }

        const gc = state.xai.gradcam[task];
        const ge = state.xai.gnnexplainer[task];
        const isCompare = state.currentMethod === "compare";

        if (!gc && !ge) {
            els.atomsSection.hidden = true;
            return;
        }

        els.atomsSection.hidden = false;
        els.colGnnexp.hidden = !isCompare;

        const imp = isCompare ? gc || ge : getCurrentImportance();
        if (!imp) return;

        const indices = [...imp.keys()].sort((a, b) => (imp[b] ?? 0) - (imp[a] ?? 0));

        els.atomsTable.innerHTML = indices
            .map((i) => {
                const sym = state.atomSymbols[i] || "?";
                const vGc = gc ? (gc[i] ?? 0).toFixed(3) : "—";
                const vGe = ge ? (ge[i] ?? 0).toFixed(3) : "—";
                const v = imp[i] ?? 0;
                return `<tr data-atom="${i}">
                    <td>${i}</td>
                    <td><strong>${sym}</strong></td>
                    <td>${isCompare ? vGc : (state.currentMethod === "gnnexplainer" ? vGe : vGc)}</td>
                    ${isCompare ? `<td>${vGe}</td>` : ""}
                    <td><div class="imp-bar"><div class="imp-bar-fill" style="width:${(v * 100).toFixed(0)}%"></div></div></td>
                </tr>`;
            })
            .join("");

        els.atomsTable.querySelectorAll("tr").forEach((row) => {
            row.addEventListener("mouseenter", () => {
                const idx = parseInt(row.dataset.atom, 10);
                MoleculeViewer3D.highlightAtom(idx);
            });
        });
    }

    async function update2dSvg() {
        const imp = getCurrentImportance();
        if (!imp || !smiles) {
            els.viewer2d.innerHTML = '<span style="color:#8b9cb3">Selecciona tarea y genera XAI</span>';
            return;
        }

        try {
            const res = await fetch("/api/svg", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    smiles,
                    importance: imp,
                    title: `${state.currentTask} — ${state.currentMethod}`,
                }),
            });
            if (!res.ok) throw new Error("Error generando SVG");
            const data = await res.json();
            els.viewer2d.innerHTML = data.svg;

            if (data.atom_colors && state.currentTask) {
                const method = getActiveXaiMethod();
                if (!state.xaiColors[method]) state.xaiColors[method] = {};
                state.xaiColors[method][state.currentTask] = data.atom_colors;
                if (state.molBlock) {
                    MoleculeViewer3D.applyAtomColors(data.atom_colors, imp);
                }
            }
        } catch {
            els.viewer2d.innerHTML = '<span style="color:#8b9cb3">SVG no disponible</span>';
        }
    }

    async function loadMol3d() {
        if (!smiles) {
            setViewer3dStatus("Sin SMILES — selecciona un compuesto del corpus");
            return;
        }

        setViewer3dStatus("Generando estructura 3D…");

        try {
            const res = await fetch(`/api/mol3d?smiles=${encodeURIComponent(smiles)}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "No se pudo generar estructura 3D");

            const structure = data.sdf || data.mol_block;
            const format = data.sdf ? "sdf" : "mol";
            state.molBlock = structure;
            state.molFormat = format;

            const imp = getCurrentImportance();
            const colors = imp ? await ensureCurrentColors() : null;

            const ok = MoleculeViewer3D.loadStructure(
                structure,
                format,
                imp,
                colors
            );
            setViewer3dStatus(null);
            if (!ok) throw new Error("3Dmol no pudo renderizar la molécula");
        } catch (e) {
            setViewer3dStatus(null);
            showError(e.message);
        }
    }

    async function runXai(method) {
        if (!smiles || !state.currentTask) return;
        hideError();

        const methods = method === "both" ? ["gradcam", "gnnexplainer"] : [method];

        for (const m of methods) {
            if (state.xai[m]?.[state.currentTask]) continue;

            showLoading(
                m === "gnnexplainer"
                    ? "GNNExplainer en ejecución (~30 s)…"
                    : "Calculando Grad-CAM…"
            );

            try {
                const res = await fetch("/api/explain", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ smiles, task: state.currentTask, method: m }),
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Error XAI");

                if (!state.xai[m]) state.xai[m] = {};
                state.xai[m][state.currentTask] = data.importance;
                if (data.atom_colors) {
                    if (!state.xaiColors[m]) state.xaiColors[m] = {};
                    state.xaiColors[m][state.currentTask] = data.atom_colors;
                }
                if (!state.atomSymbols.length) state.atomSymbols = data.atom_symbols;
            } catch (e) {
                showError(e.message);
            }
        }

        hideLoading();
        refreshXaiView();
    }

    function setDemoMode(isDemo) {
        if (els.demoBanner) els.demoBanner.hidden = !isDemo;
        if (els.demoPredictionsNote) els.demoPredictionsNote.hidden = !isDemo;
    }

    async function applyCorpusData(data) {
        smiles = data.smiles || smiles;
        state.predictions = data.predictions || {};
        state.xai = data.xai || { gradcam: {}, gnnexplainer: {} };
        state.xaiColors = data.xai_colors || { gradcam: {}, gnnexplainer: {} };
        state.atomSymbols = data.atom_symbols || [];
        state.properties = data.properties || null;
        state.molBlock = data.mol_block || null;

        setDemoMode(Boolean(data.demo));

        if (data.name) {
            els.compoundName.textContent = data.name;
            els.breadcrumbName.textContent = data.name;
        } else if (initialName) {
            els.compoundName.textContent = initialName;
            els.breadcrumbName.textContent = initialName;
        }
        if (smiles) els.smilesDisplay.textContent = smiles;

        renderProperties(state.properties);
        renderPredictions(state.predictions);

        const topTask = data.top_task || Object.entries(state.predictions).sort((a, b) => b[1] - a[1])[0]?.[0];
        if (topTask) {
            state.currentTask = topTask;
            if (els.taskSelect) els.taskSelect.value = topTask;
        }

        // Cargar 3D tras layout (clientWidth puede ser 0 en DOMContentLoaded)
        requestAnimationFrame(async () => {
            await loadMol3d();
            await refreshXaiView();
        });
    }

    async function loadLiveAnalysis() {
        if (!smiles) {
            showError("Ingresa un SMILES válido desde el dashboard.");
            return;
        }

        showLoading("Ejecutando predicción + XAI en vivo…");
        hideError();

        try {
            const res = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ smiles }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error en análisis");

            setDemoMode(false);
            await applyCorpusData(data);
        } catch (e) {
            showError(e.message);
            await loadMol3d();
            try {
                const propsRes = await fetch(`/api/properties?smiles=${encodeURIComponent(smiles)}`);
                if (propsRes.ok) {
                    const props = await propsRes.json();
                    renderProperties(props);
                }
            } catch { /* ignore */ }
        } finally {
            hideLoading();
        }
    }

    async function init() {
        if (initialName) {
            els.compoundName.textContent = initialName;
            els.breadcrumbName.textContent = initialName;
        }
        if (smiles) els.smilesDisplay.textContent = smiles;

        const corpusScript = document.getElementById("corpus-data");
        if (corpusScript && !liveAnalysis) {
            try {
                const data = JSON.parse(corpusScript.textContent);
                await applyCorpusData(data);
                return;
            } catch { /* fall through */ }
        }

        if (liveAnalysis && smiles) {
            await loadLiveAnalysis();
            return;
        }

        if (fromCorpus && compoundId && !liveAnalysis) {
            showLoading("Cargando compuesto del corpus…");
            try {
                const res = await fetch(`/api/corpus/${compoundId}`);
                if (res.ok) {
                    await applyCorpusData(await res.json());
                    hideLoading();
                    return;
                }
            } catch { /* ignore */ }
            hideLoading();
        }

        if (smiles) {
            await loadLiveAnalysis();
        }
    }

    init();
});
