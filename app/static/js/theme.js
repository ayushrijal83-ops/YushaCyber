/* YushaCyber theme switcher — Dark / Light / Cyber.
   Persists to localStorage and applies to <html data-theme>. Loaded on every
   page so the choice follows the user across the whole app.
   The initial theme is applied by an inline script in <head> to avoid a flash;
   this file wires up the switcher buttons. */
(function () {
    "use strict";
    var THEMES = ["dark", "light", "cyber"];

    function current() {
        try { return localStorage.getItem("yc-theme") || "dark"; }
        catch (e) { return "dark"; }
    }
    function apply(theme) {
        if (THEMES.indexOf(theme) === -1) theme = "dark";
        document.documentElement.setAttribute("data-theme", theme);
        try { localStorage.setItem("yc-theme", theme); } catch (e) {}
        document.querySelectorAll("[data-theme-btn], .lp-theme__btn, .shell-theme__btn")
            .forEach(function (btn) {
                btn.classList.toggle("is-active", btn.getAttribute("data-theme") === theme);
            });
    }

    apply(current());

    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".lp-theme__btn, .shell-theme__btn, [data-theme-btn]");
        if (!btn) return;
        var theme = btn.getAttribute("data-theme");
        if (theme) apply(theme);
    });
})();
