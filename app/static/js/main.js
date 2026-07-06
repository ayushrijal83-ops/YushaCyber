/* ==========================================================================
   YushaCyber — main.js
   Vanilla JavaScript only. No external dependencies. No inline handlers.
   Organized as small init functions, bootstrapped at the bottom.
   ========================================================================== */

(function () {
    "use strict";

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    /* ----------------------------------------------------------------------
       Navbar: scrolled shadow + mobile menu toggle
       ---------------------------------------------------------------------- */
    function initNavbar() {
        const navbar = document.getElementById("navbar");
        const navToggle = document.getElementById("nav-toggle");
        const navMenu = document.getElementById("nav-menu");
        if (!navbar || !navToggle || !navMenu) return;

        window.addEventListener(
            "scroll",
            () => {
                navbar.classList.toggle("navbar--scrolled", window.scrollY > 8);
            },
            { passive: true }
        );

        navToggle.addEventListener("click", () => {
            const isOpen = navMenu.classList.toggle("navbar__menu--open");
            navToggle.setAttribute("aria-expanded", String(isOpen));
        });

        // Close the mobile menu after choosing a link (smooth scroll continues).
        navMenu.addEventListener("click", (event) => {
            if (event.target.closest("a")) {
                navMenu.classList.remove("navbar__menu--open");
                navToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    /* ----------------------------------------------------------------------
       Hero terminal: typed command sequence
       ---------------------------------------------------------------------- */
    function initTerminal() {
        const typedTarget = document.getElementById("typed-command");
        const outputTarget = document.getElementById("terminal-output");
        if (!typedTarget || !outputTarget) return;

        const script = [
            { command: "whoami", output: ["future_security_pro"], ok: false },
            {
                command: "yusha enroll --track offensive-security",
                output: ["[+] Roadmap unlocked: 8 stages, 120 labs"],
                ok: true
            },
            {
                command: "yusha start lesson-01",
                output: ["[+] Lab environment ready. Happy hacking!"],
                ok: true
            }
        ];

        function appendOutput(step) {
            const echoLine = document.createElement("p");
            echoLine.className = "terminal__line";

            const prompt = document.createElement("span");
            prompt.className = "terminal__prompt";
            prompt.textContent = "$";
            echoLine.appendChild(prompt);
            echoLine.appendChild(document.createTextNode(" " + step.command));
            outputTarget.appendChild(echoLine);

            step.output.forEach((line) => {
                const outLine = document.createElement("p");
                outLine.className =
                    "terminal__output" + (step.ok ? " terminal__output--ok" : "");
                outLine.textContent = line;
                outputTarget.appendChild(outLine);
            });
        }

        // Static fallback when the user prefers reduced motion.
        if (prefersReducedMotion) {
            script.forEach(appendOutput);
            return;
        }

        let stepIndex = 0;

        function typeStep() {
            const step = script[stepIndex];
            let charIndex = 0;
            typedTarget.textContent = "";

            const typing = setInterval(() => {
                typedTarget.textContent = step.command.slice(0, charIndex + 1);
                charIndex += 1;

                if (charIndex === step.command.length) {
                    clearInterval(typing);
                    setTimeout(() => {
                        appendOutput(step);
                        typedTarget.textContent = "";
                        stepIndex += 1;
                        if (stepIndex < script.length) {
                            setTimeout(typeStep, 600);
                        }
                    }, 450);
                }
            }, 55);
        }

        typeStep();
    }

    /* ----------------------------------------------------------------------
       Statistics: count-up when scrolled into view
       ---------------------------------------------------------------------- */
    function initCounters() {
        const counters = document.querySelectorAll(".stats__value[data-count]");
        if (!counters.length) return;

        function animateCounter(element) {
            const target = parseInt(element.dataset.count, 10);

            if (prefersReducedMotion) {
                element.textContent = target.toLocaleString();
                return;
            }

            const duration = 1400;
            const start = performance.now();

            function frame(now) {
                const progress = Math.min((now - start) / duration, 1);
                // Ease-out cubic for a satisfying settle.
                const eased = 1 - Math.pow(1 - progress, 3);
                element.textContent = Math.round(target * eased).toLocaleString();
                if (progress < 1) requestAnimationFrame(frame);
            }

            requestAnimationFrame(frame);
        }

        const observer = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animateCounter(entry.target);
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.6 }
        );

        counters.forEach((counter) => observer.observe(counter));
    }

    /* ----------------------------------------------------------------------
       Scroll-reveal: fade-in for cards and section headers
       ---------------------------------------------------------------------- */
    function initScrollReveal() {
        const revealElements = document.querySelectorAll(".reveal");
        if (!revealElements.length) return;

        const observer = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("reveal--visible");
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15 }
        );

        revealElements.forEach((element) => observer.observe(element));
    }

    /* ----------------------------------------------------------------------
       Daily Challenge: countdown to next midnight (local time)
       ---------------------------------------------------------------------- */
    function initChallengeTimer() {
        const timerElement = document.getElementById("challenge-timer");
        if (!timerElement) return;

        function update() {
            const now = new Date();
            const midnight = new Date(now);
            midnight.setHours(24, 0, 0, 0);

            const diff = midnight - now;
            const hours = String(Math.floor(diff / 3.6e6)).padStart(2, "0");
            const minutes = String(Math.floor((diff % 3.6e6) / 6e4)).padStart(2, "0");
            const seconds = String(Math.floor((diff % 6e4) / 1e3)).padStart(2, "0");

            timerElement.textContent = `Resets in ${hours}:${minutes}:${seconds}`;
        }

        update();
        setInterval(update, 1000);
    }

    /* ----------------------------------------------------------------------
       FAQ: accessible accordion (one panel open at a time)
       ---------------------------------------------------------------------- */
    function initFaqAccordion() {
        const items = document.querySelectorAll(".faq__item");
        if (!items.length) return;

        function closeItem(item) {
            const button = item.querySelector(".faq__question");
            const panel = item.querySelector(".faq__panel");
            item.classList.remove("faq__item--open");
            button.setAttribute("aria-expanded", "false");
            panel.style.maxHeight = "0px";
            // Hide from assistive tech after the collapse transition ends.
            panel.addEventListener(
                "transitionend",
                () => {
                    if (!item.classList.contains("faq__item--open")) {
                        panel.hidden = true;
                    }
                },
                { once: true }
            );
            if (prefersReducedMotion) panel.hidden = true;
        }

        function openItem(item) {
            const button = item.querySelector(".faq__question");
            const panel = item.querySelector(".faq__panel");
            panel.hidden = false;
            item.classList.add("faq__item--open");
            button.setAttribute("aria-expanded", "true");
            // Measure content height after unhiding, then animate to it.
            panel.style.maxHeight = panel.scrollHeight + "px";
        }

        items.forEach((item) => {
            const button = item.querySelector(".faq__question");
            if (!button) return;

            button.addEventListener("click", () => {
                const isOpen = item.classList.contains("faq__item--open");

                // Close every other panel first (single-open accordion).
                items.forEach((other) => {
                    if (other !== item && other.classList.contains("faq__item--open")) {
                        closeItem(other);
                    }
                });

                if (isOpen) {
                    closeItem(item);
                } else {
                    openItem(item);
                }
            });
        });

        // Keep open panel heights correct if the viewport is resized.
        window.addEventListener(
            "resize",
            () => {
                document.querySelectorAll(".faq__item--open .faq__panel").forEach(
                    (panel) => {
                        panel.style.maxHeight = panel.scrollHeight + "px";
                    }
                );
            },
            { passive: true }
        );
    }

    /* ----------------------------------------------------------------------
       Bootstrap
       ---------------------------------------------------------------------- */
    document.addEventListener("DOMContentLoaded", () => {
        initNavbar();
        initTerminal();
        initCounters();
        initScrollReveal();
        initChallengeTimer();
        initFaqAccordion();
    });
})();
