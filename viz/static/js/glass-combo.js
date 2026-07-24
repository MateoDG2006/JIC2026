/**
 * Enhance native <select> into glassmorphism comboboxes.
 * Max 5 visible items; scrollbar hidden.
 */
(function () {
  const ITEM_H = 2.35; // rem — keep in sync with CSS
  const MAX_VISIBLE = 5;

  function optionLabel(opt) {
    return (opt.textContent || opt.label || opt.value || "").trim();
  }

  function enhance(select) {
    if (!select || select.dataset.glassCombo === "1") return;
    select.dataset.glassCombo = "1";

    const wrap = document.createElement("div");
    wrap.className = "glass-combo";
    if (select.id) wrap.dataset.for = select.id;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "glass-combo-btn";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    if (select.id) btn.id = select.id + "-glass-btn";
    if (select.getAttribute("aria-label")) {
      btn.setAttribute("aria-label", select.getAttribute("aria-label"));
    }

    const valueEl = document.createElement("span");
    valueEl.className = "glass-combo-value";

    const chevron = document.createElement("i");
    chevron.setAttribute("data-lucide", "chevron-down");
    chevron.className = "glass-combo-chevron";
    chevron.setAttribute("aria-hidden", "true");

    btn.appendChild(valueEl);
    btn.appendChild(chevron);

    const list = document.createElement("ul");
    list.className = "glass-combo-list";
    list.setAttribute("role", "listbox");
    list.hidden = true;
    list.style.maxHeight = `calc(${MAX_VISIBLE} * ${ITEM_H}rem + .7rem)`;

    select.classList.add("glass-combo-native");
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    wrap.appendChild(btn);
    wrap.appendChild(list);

    function rebuildOptions() {
      list.innerHTML = "";
      [...select.options].forEach((opt, idx) => {
        const li = document.createElement("li");
        li.setAttribute("role", "option");
        li.tabIndex = -1;
        li.dataset.value = opt.value;
        li.dataset.index = String(idx);
        li.textContent = optionLabel(opt);
        if (opt.disabled) {
          li.setAttribute("aria-disabled", "true");
          li.classList.add("disabled");
        }
        li.addEventListener("click", (e) => {
          e.stopPropagation();
          if (opt.disabled) return;
          select.value = opt.value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
          syncFromSelect();
          close();
          btn.focus();
        });
        list.appendChild(li);
      });
      syncFromSelect();
    }

    function syncFromSelect() {
      const opt = select.options[select.selectedIndex];
      valueEl.textContent = opt ? optionLabel(opt) : "";
      list.querySelectorAll("[role=option]").forEach((li) => {
        const on = li.dataset.value === select.value;
        li.classList.toggle("on", on);
        li.setAttribute("aria-selected", on ? "true" : "false");
      });
    }

    function open() {
      document.querySelectorAll(".glass-combo.open").forEach((el) => {
        if (el !== wrap) el._glassClose?.();
      });
      wrap.classList.add("open");
      list.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      const cur =
        list.querySelector(".on") || list.querySelector("[role=option]");
      cur?.focus();
      cur?.scrollIntoView({ block: "nearest" });
    }

    function close() {
      wrap.classList.remove("open");
      list.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }

    wrap._glassClose = close;
    wrap._glassSync = syncFromSelect;

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (wrap.classList.contains("open")) close();
      else open();
    });

    btn.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });

    list.addEventListener("keydown", (e) => {
      const opts = [...list.querySelectorAll("[role=option]:not(.disabled)")];
      const i = opts.indexOf(document.activeElement);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        opts[Math.min(opts.length - 1, i + 1)]?.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        opts[Math.max(0, i - 1)]?.focus();
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        document.activeElement?.click();
      } else if (e.key === "Escape") {
        close();
        btn.focus();
      }
    });

    // Keep UI in sync when JS sets select.value
    const valueDesc = Object.getOwnPropertyDescriptor(
      HTMLSelectElement.prototype,
      "value"
    );
    if (valueDesc?.set && valueDesc?.get) {
      Object.defineProperty(select, "value", {
        configurable: true,
        enumerable: true,
        get() {
          return valueDesc.get.call(this);
        },
        set(v) {
          valueDesc.set.call(this, v);
          syncFromSelect();
        },
      });
    }

    const selectedDesc = Object.getOwnPropertyDescriptor(
      HTMLSelectElement.prototype,
      "selectedIndex"
    );
    if (selectedDesc?.set && selectedDesc?.get) {
      Object.defineProperty(select, "selectedIndex", {
        configurable: true,
        enumerable: true,
        get() {
          return selectedDesc.get.call(this);
        },
        set(v) {
          selectedDesc.set.call(this, v);
          syncFromSelect();
        },
      });
    }

    select.addEventListener("change", syncFromSelect);

    rebuildOptions();

    if (window.lucide) {
      try {
        lucide.createIcons({ nodes: [chevron] });
      } catch (_) {
        lucide.createIcons();
      }
    }
  }

  function enhanceAll(root) {
    (root || document)
      .querySelectorAll("select:not([data-glass-combo='1'])")
      .forEach(enhance);
  }

  document.addEventListener("click", (e) => {
    document.querySelectorAll(".glass-combo.open").forEach((el) => {
      if (!el.contains(e.target)) el._glassClose?.();
    });
  });

  function boot() {
    enhanceAll(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.GnnToxGlassCombo = { enhance, enhanceAll };
})();
