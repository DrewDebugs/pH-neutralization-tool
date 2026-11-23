// Light/dark theme: follows the operating system unless the visitor picks one.
// Loaded in <head> so the page never flashes the wrong theme.
(function () {
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) { /* private mode */ }
  if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;

  function current() {
    const set = document.documentElement.dataset.theme;
    if (set) return set;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function toggle() {
    const next = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
    window.dispatchEvent(new Event("themechange"));
  }

  window.matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => window.dispatchEvent(new Event("themechange")));

  document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("theme-toggle");
    if (button) button.addEventListener("click", toggle);
  });
})();
