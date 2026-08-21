// Dark / Light mode toggle. Respects prefers-color-scheme by default
// (handled inline in <head> to avoid flash-of-wrong-theme), then persists
// the user's explicit choice in localStorage.
(function () {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
  });

  // Keep in sync if the OS-level preference changes and the user hasn't
  // made an explicit choice yet.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem("theme")) {
      document.documentElement.classList.toggle("dark", e.matches);
    }
  });
})();
