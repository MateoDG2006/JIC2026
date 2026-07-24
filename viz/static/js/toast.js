/**
 * Toast cards laterales — errores y avisos fuera de la UI principal.
 */
(function () {
  function ensureStack() {
    let stack = document.getElementById("toast-stack");
    if (stack) return stack;
    stack = document.createElement("div");
    stack.id = "toast-stack";
    stack.className = "toast-stack";
    stack.setAttribute("aria-live", "polite");
    stack.setAttribute("aria-relevant", "additions");
    document.body.appendChild(stack);
    return stack;
  }

  function showToast(message, variant = "warn", duration = 5500) {
    if (!message) return null;
    const stack = ensureStack();

    const toast = document.createElement("div");
    toast.className = `toast toast-${variant}`;
    toast.setAttribute("role", "status");

    const text = document.createElement("p");
    text.className = "toast-msg";
    text.textContent = String(message);

    const close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close";
    close.setAttribute("aria-label", "Cerrar");
    close.innerHTML = '<i data-lucide="x" aria-hidden="true"></i>';

    toast.appendChild(text);
    toast.appendChild(close);
    stack.appendChild(toast);

    if (window.lucide) {
      try {
        lucide.createIcons({ nodes: [close] });
      } catch (_) {
        lucide.createIcons();
      }
    }

    requestAnimationFrame(() => toast.classList.add("in"));

    let closed = false;
    function dismiss() {
      if (closed) return;
      closed = true;
      toast.classList.remove("in");
      toast.classList.add("out");
      setTimeout(() => toast.remove(), 280);
    }

    close.addEventListener("click", dismiss);
    if (duration > 0) setTimeout(dismiss, duration);
    return dismiss;
  }

  window.GnnToxToast = { showToast };
})();
