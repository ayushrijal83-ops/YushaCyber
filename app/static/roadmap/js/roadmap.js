/* ==========================================================================
   YushaCyber — roadmap.js
   Roadmap page interactions. The shared shell behaviour (sidebar toggle,
   profile dropdown) is handled by dashboard.js; this file only owns
   roadmap-specific touches. Vanilla JavaScript, no dependencies.
   ========================================================================== */

(function () {
    "use strict";

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    /* Staggered entrance for the tier cards. */
    function initTierReveal() {
        const tiers = document.querySelectorAll(".rm-tier");
        if (!tiers.length || prefersReducedMotion) return;

        tiers.forEach((tier, index) => {
            tier.style.opacity = "0";
            tier.style.transform = "translateY(16px)";
            tier.style.transition = "opacity 0.45s ease, transform 0.45s ease";
            window.setTimeout(() => {
                tier.style.opacity = "1";
                tier.style.transform = "translateY(0)";
            }, 90 * index + 80);
        });
    }

    document.addEventListener("DOMContentLoaded", initTierReveal);
})();
