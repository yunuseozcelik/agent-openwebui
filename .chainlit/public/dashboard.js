(function () {
  function shouldHideComposer() {
    const text = (document.body && document.body.innerText) || "";
    return text.includes("Gateway / Portkey") && text.includes("Cost Dashboard");
  }

  function findComposerRoot() {
    const textarea = document.querySelector("textarea");
    if (!textarea) return null;
    return textarea.closest("form") || textarea.parentElement?.parentElement || textarea.parentElement;
  }

  function toggleComposer() {
    document.body.classList.toggle("gateway-dashboard-mode", shouldHideComposer());

    const composer = findComposerRoot();
    if (!composer) return;

    if (shouldHideComposer()) {
      composer.style.display = "none";
      composer.setAttribute("data-hidden-by-dashboard", "true");
      return;
    }

    if (composer.getAttribute("data-hidden-by-dashboard") === "true") {
      composer.style.display = "";
      composer.removeAttribute("data-hidden-by-dashboard");
    }
  }

  const observer = new MutationObserver(() => toggleComposer());
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.addEventListener("load", toggleComposer);
  setInterval(toggleComposer, 1000);
})();
