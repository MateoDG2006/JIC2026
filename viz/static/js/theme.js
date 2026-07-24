/**
 * Shared light/dark theme toggle (same key as landing.js).
 */
(function () {
  const THEME_KEY = "gnntox-theme";

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (_) {}
    document.dispatchEvent(new CustomEvent("gnntox-theme", { detail: { theme } }));
  }

  let initial = "light";
  try {
    initial = localStorage.getItem(THEME_KEY) || "light";
  } catch (_) {}
  applyTheme(initial);

  function bind() {
    const btn = document.getElementById("themeBtn");
    if (!btn || btn.dataset.themeBound) return;
    btn.dataset.themeBound = "1";
    btn.addEventListener("click", () => {
      const next =
        document.documentElement.getAttribute("data-theme") === "dark"
          ? "light"
          : "dark";
      applyTheme(next);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  window.GnnToxTheme = { applyTheme, THEME_KEY };
})();
