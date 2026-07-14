/* ==========================================================================
   YushaCyber — dashboard.js
   Dashboard interactions. Vanilla JavaScript, no dependencies,
   no inline handlers. Small init functions bootstrapped at the bottom.
   ========================================================================== */

(function () {
    "use strict";

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    /* ----------------------------------------------------------------------
       Sidebar: off-canvas toggle on mobile
       ---------------------------------------------------------------------- */
    function initSidebar() {
        const sidebar = document.getElementById("sidebar");
        const toggle = document.getElementById("sidebar-toggle");
        const overlay = document.getElementById("sidebar-overlay");
        if (!sidebar || !toggle || !overlay) return;

        function setOpen(open) {
            sidebar.classList.toggle("sidebar--open", open);
            overlay.classList.toggle("sidebar-overlay--visible", open);
            overlay.hidden = false; // keep in DOM for the fade transition
            toggle.setAttribute("aria-expanded", String(open));
        }

        toggle.addEventListener("click", () => {
            setOpen(!sidebar.classList.contains("sidebar--open"));
        });

        overlay.addEventListener("click", () => setOpen(false));

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") setOpen(false);
        });
    }

    /* ----------------------------------------------------------------------
       Profile dropdown: toggle, outside click, Escape
       ---------------------------------------------------------------------- */
    function initProfileDropdown() {
        const button = document.getElementById("profile-toggle");
        const menu = document.getElementById("profile-menu");
        if (!button || !menu) return;

        function setOpen(open) {
            menu.hidden = !open;
            button.setAttribute("aria-expanded", String(open));
        }

        button.addEventListener("click", (event) => {
            event.stopPropagation();
            setOpen(menu.hidden);
        });

        document.addEventListener("click", (event) => {
            if (!menu.hidden && !menu.contains(event.target)) {
                setOpen(false);
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !menu.hidden) {
                setOpen(false);
                button.focus();
            }
        });
    }

    /* ----------------------------------------------------------------------
       Stat counters: count up when scrolled into view
       ---------------------------------------------------------------------- */
    function initCounters() {
        const counters = document.querySelectorAll(".stat-card__value[data-count]");
        if (!counters.length) return;

        function animate(element) {
            const target = parseInt(element.dataset.count, 10) || 0;

            if (prefersReducedMotion || target === 0) {
                element.textContent = target.toLocaleString();
                return;
            }

            const duration = 1100;
            const start = performance.now();

            function frame(now) {
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
                element.textContent = Math.round(target * eased).toLocaleString();
                if (progress < 1) requestAnimationFrame(frame);
            }

            requestAnimationFrame(frame);
        }

        const observer = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animate(entry.target);
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.5 }
        );

        counters.forEach((counter) => observer.observe(counter));
    }

    /* ----------------------------------------------------------------------
       Progress bars: animate width + percentage label on reveal
       ---------------------------------------------------------------------- */
    function initProgressBars() {
        const bars = document.querySelectorAll(".progress-bar__fill[data-progress]");
        if (!bars.length) return;

        function reveal(fill) {
            const percent = Math.max(0, Math.min(100,
                parseInt(fill.dataset.progress, 10) || 0));
            fill.style.width = percent + "%";

            // The percent label lives in a sibling head element. Different
            // layouts use different containers (.progress-row for the
            // learning-progress list, .banner__progress for the welcome
            // banner), so search from the nearest common ancestor rather
            // than assuming one class.
            const container =
                fill.closest(".progress-row") ||
                fill.closest(".banner__progress") ||
                fill.parentElement.parentElement;
            const label = container &&
                container.querySelector(".progress-row__percent");
            if (label) label.textContent = percent + "%";
        }

        // Reveal immediately (covers bars already in view, e.g. the banner
        // above the fold), then also observe for any that scroll into view.
        const observer = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        reveal(entry.target);
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.1 }
        );

        bars.forEach((bar) => {
            const rect = bar.getBoundingClientRect();
            const visible = rect.top < window.innerHeight && rect.bottom > 0;
            if (visible) {
                reveal(bar);          // already on screen — fill now
            } else {
                observer.observe(bar); // fill when scrolled into view
            }
        });
    }

    /* ----------------------------------------------------------------------
       Bootstrap
       ---------------------------------------------------------------------- */
    document.addEventListener("DOMContentLoaded", () => {
        initSidebar();
        initProfileDropdown();
        initCounters();
        initProgressBars();
    });
})();

/* ==========================================================================
   Global application shell (YC-011.C) — dropdowns, mobile menu, shortcuts.
   Self-contained; safe on pages where elements are absent.
   ========================================================================== */
(function () {
    "use strict";

    /* ---- Dropdowns (notifications + profile) ---- */
    var drops = [
        { btn: "notif-toggle",   menu: "notif-menu" },
        { btn: "profile-toggle", menu: "profile-menu" }
    ].map(function (d) {
        return { btn: document.getElementById(d.btn), menu: document.getElementById(d.menu) };
    }).filter(function (d) { return d.btn && d.menu; });

    function closeAll(except) {
        drops.forEach(function (d) {
            if (d === except) return;
            d.menu.hidden = true;
            d.btn.setAttribute("aria-expanded", "false");
        });
    }

    drops.forEach(function (d) {
        d.btn.addEventListener("click", function (e) {
            e.stopPropagation();
            var open = d.menu.hidden;
            closeAll(d);
            d.menu.hidden = !open;
            d.btn.setAttribute("aria-expanded", open ? "true" : "false");
        });
        d.menu.addEventListener("click", function (e) { e.stopPropagation(); });
    });

    document.addEventListener("click", function () { closeAll(null); });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeAll(null);
    });

    /* ---- Mobile slide-out ---- */
    var burger = document.getElementById("shell-burger");
    var mobile = document.getElementById("shell-mobile");
    var closeBtn = document.getElementById("shell-close");
    var backdrop = document.getElementById("shell-backdrop");

    function setMobile(open) {
        if (!mobile || !burger) return;
        mobile.hidden = !open;
        burger.setAttribute("aria-expanded", open ? "true" : "false");
        document.body.style.overflow = open ? "hidden" : "";
    }

    if (burger && mobile) {
        burger.addEventListener("click", function () { setMobile(mobile.hidden); });
        if (closeBtn) closeBtn.addEventListener("click", function () { setMobile(false); });
        if (backdrop) backdrop.addEventListener("click", function () { setMobile(false); });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") setMobile(false);
        });
    }

    /* ---- "/" focuses search ---- */
    document.addEventListener("keydown", function (e) {
        if (e.key !== "/") return;
        var tag = (document.activeElement && document.activeElement.tagName) || "";
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        var input = document.querySelector(".shell-search__input");
        if (input) { e.preventDefault(); input.focus(); }
    });
})();

/* ==========================================================================
   Theme switcher (app-wide) — Dark / Light / Cyber. Mirrors theme.js so the
   dashboard and every in-app page can switch themes without loading a second
   script. Applies the saved theme on load and persists changes.
   ========================================================================== */
(function () {
    "use strict";
    var THEMES = ["dark", "light", "cyber"];
    function current() {
        try { return localStorage.getItem("yc-theme") || "dark"; } catch (e) { return "dark"; }
    }
    function apply(theme) {
        if (THEMES.indexOf(theme) === -1) theme = "dark";
        document.documentElement.setAttribute("data-theme", theme);
        try { localStorage.setItem("yc-theme", theme); } catch (e) {}
        document.querySelectorAll(".shell-theme__btn, .lp-theme__btn").forEach(function (b) {
            b.classList.toggle("is-active", b.getAttribute("data-theme") === theme);
        });
    }
    apply(current());
    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".shell-theme__btn, .lp-theme__btn");
        if (btn && btn.getAttribute("data-theme")) apply(btn.getAttribute("data-theme"));
    });
})();
