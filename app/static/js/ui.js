/* ===========================================================================
   YushaCyber — shared UI behaviour (YC-022.0 Product Polish)

   Loaded on every page. Small, dependency-free, progressive-enhancement
   only — nothing here is required for a page to function.

   1. Form loading states — on submit, the submit button is disabled and
      shows a spinner so users can't double-submit and always get feedback.
   2. Flash auto-dismiss — success messages fade after a few seconds.
   3. Scroll-reveal — elements marked .ui-reveal fade in as they enter the
      viewport (skipped entirely under prefers-reduced-motion).
   =========================================================================== */
(function () {
    "use strict";

    /* ---- 1. Form loading states ------------------------------------- */
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.hasAttribute("data-no-loading")) return;
        if (e.defaultPrevented) return; /* JS-handled forms manage themselves */

        var buttons = form.querySelectorAll(
            'button[type="submit"], input[type="submit"], button:not([type])'
        );
        buttons.forEach(function (btn) {
            btn.classList.add("is-loading");
            btn.setAttribute("aria-busy", "true");
            /* Disable AFTER the click has been processed so the button's
               value still submits with the form. */
            window.setTimeout(function () { btn.disabled = true; }, 0);
        });

        /* Safety net: re-enable if the page didn't navigate (e.g. bfcache,
           validation failure handled client-side later). */
        window.setTimeout(function () {
            buttons.forEach(function (btn) {
                btn.disabled = false;
                btn.classList.remove("is-loading");
                btn.removeAttribute("aria-busy");
            });
        }, 12000);
    });

    /* Restore buttons when returning via back/forward cache. */
    window.addEventListener("pageshow", function () {
        document.querySelectorAll(".btn.is-loading, [aria-busy='true']").forEach(function (btn) {
            btn.disabled = false;
            btn.classList.remove("is-loading");
            btn.removeAttribute("aria-busy");
        });
    });

    /* ---- 2. Flash auto-dismiss --------------------------------------- */
    document.addEventListener("DOMContentLoaded", function () {
        var flashes = document.querySelectorAll(
            ".ui-flash--success, .dash-flash__item--success"
        );
        flashes.forEach(function (el) {
            window.setTimeout(function () {
                el.style.transition = "opacity 0.5s ease";
                el.style.opacity = "0";
                window.setTimeout(function () { el.remove(); }, 550);
            }, 4500);
        });
    });

    /* ---- 3. Scroll-reveal --------------------------------------------- */
    document.addEventListener("DOMContentLoaded", function () {
        var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        var items = document.querySelectorAll(".ui-reveal");
        if (!items.length) return;

        if (reduced || !("IntersectionObserver" in window)) {
            items.forEach(function (el) { el.classList.add("is-visible"); });
            return;
        }
        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        items.forEach(function (el) { obs.observe(el); });
    });
}());
