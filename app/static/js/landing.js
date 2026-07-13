/* YushaCyber landing — animation only (YC-011.A).
   No dependencies. Degrades gracefully: without JS the stats show their
   final numbers (set server-side) and sections are fully visible. */
(function () {
    "use strict";

    var reduce = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* ---- Animated stat counters ---- */
    function runCounter(el) {
        var target = parseInt(el.getAttribute("data-target"), 10) || 0;
        var suffix = el.getAttribute("data-suffix") || "";
        if (reduce) { el.textContent = target.toLocaleString() + suffix; return; }
        var start = null;
        var duration = 1400;
        function tick(ts) {
            if (start === null) start = ts;
            var p = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - p, 3);           // easeOutCubic
            var val = Math.floor(eased * target);
            el.textContent = val.toLocaleString() + suffix;
            if (p < 1) requestAnimationFrame(tick);
            else el.textContent = target.toLocaleString() + suffix;
        }
        requestAnimationFrame(tick);
    }

    var counters = document.querySelectorAll(".lp-stat__value[data-target]");
    if ("IntersectionObserver" in window && counters.length) {
        var statObs = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (e) {
                if (e.isIntersecting) { runCounter(e.target); obs.unobserve(e.target); }
            });
        }, { threshold: 0.4 });
        counters.forEach(function (c) { statObs.observe(c); });
    } else {
        counters.forEach(runCounter);
    }

    /* ---- Reveal-on-scroll ---- */
    var revealSelector = ".lp-feature, .lp-why__card, .lp-step, .lp-stat, .lp-faq__item";
    var items = document.querySelectorAll(revealSelector);
    if (!reduce && "IntersectionObserver" in window && items.length) {
        items.forEach(function (el) { el.classList.add("lp-reveal"); });
        var revObs = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (e) {
                if (e.isIntersecting) { e.target.classList.add("is-in"); obs.unobserve(e.target); }
            });
        }, { threshold: 0.12 });
        items.forEach(function (el) { revObs.observe(el); });
    }
})();
