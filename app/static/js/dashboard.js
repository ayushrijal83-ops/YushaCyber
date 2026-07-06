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

            const row = fill.closest(".progress-row");
            const label = row && row.querySelector(".progress-row__percent");
            if (label) label.textContent = percent + "%";
        }

        const observer = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        reveal(entry.target);
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.4 }
        );

        bars.forEach((bar) => observer.observe(bar));
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
