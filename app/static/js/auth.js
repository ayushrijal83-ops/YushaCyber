/* ==========================================================================
   YushaCyber — auth.js
   Client-side enhancements for the authentication pages.
   Vanilla JavaScript only — no inline handlers, no dependencies.

   NOTE: everything here is UX sugar. Authoritative validation always
   happens server-side in Flask-WTF; this layer only gives faster feedback.
   ========================================================================== */

(function () {
    "use strict";

    /* ----------------------------------------------------------------------
       Password visibility toggles
       Buttons carry data-toggle-password="<input id>".
       ---------------------------------------------------------------------- */
    function initPasswordToggles() {
        const toggles = document.querySelectorAll("[data-toggle-password]");

        toggles.forEach((button) => {
            const input = document.getElementById(button.dataset.togglePassword);
            if (!input) return;

            button.addEventListener("click", () => {
                const showing = input.type === "text";
                input.type = showing ? "password" : "text";
                button.setAttribute("aria-pressed", String(!showing));
                button.setAttribute(
                    "aria-label",
                    showing ? "Show password" : "Hide password"
                );
                input.focus({ preventScroll: true });
            });
        });
    }

    /* ----------------------------------------------------------------------
       Password strength meter
       Container carries data-strength-for="<input id>"; scores 0–4.
       ---------------------------------------------------------------------- */
    function scorePassword(value) {
        let score = 0;
        if (value.length >= 8) score += 1;
        if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
        if (/\d/.test(value)) score += 1;
        if (value.length >= 12 || /[^A-Za-z0-9]/.test(value)) score += 1;
        return score;
    }

    const STRENGTH_LABELS = ["Too weak", "Weak", "Okay", "Good", "Strong"];

    function initStrengthMeters() {
        const meters = document.querySelectorAll("[data-strength-for]");

        meters.forEach((meter) => {
            const input = document.getElementById(meter.dataset.strengthFor);
            const label = meter.querySelector(".auth-strength__label");
            if (!input || !label) return;

            input.addEventListener("input", () => {
                const value = input.value;
                meter.classList.toggle("auth-strength--active", value.length > 0);

                const score = scorePassword(value);
                meter.className = meter.className
                    .replace(/auth-strength--[1-4]/g, "")
                    .trim();
                if (score > 0) meter.classList.add("auth-strength--" + score);
                label.textContent = "Password strength: " + STRENGTH_LABELS[score];
            });
        });
    }

    /* ----------------------------------------------------------------------
       Confirm-password live match check
       Confirm input carries data-match="<password input id>".
       ---------------------------------------------------------------------- */
    function initMatchChecks() {
        const confirms = document.querySelectorAll("[data-match]");

        confirms.forEach((confirmInput) => {
            const source = document.getElementById(confirmInput.dataset.match);
            if (!source) return;

            function check() {
                if (!confirmInput.value) {
                    confirmInput.removeAttribute("aria-invalid");
                    return;
                }
                const matches = confirmInput.value === source.value;
                confirmInput.setAttribute("aria-invalid", String(!matches));
            }

            confirmInput.addEventListener("input", check);
            source.addEventListener("input", check);
        });
    }

    /* ----------------------------------------------------------------------
       Required-field feedback on blur
       Marks empty required inputs invalid once the user leaves them.
       ---------------------------------------------------------------------- */
    function initRequiredFeedback() {
        const inputs = document.querySelectorAll(".auth-field__input");

        inputs.forEach((input) => {
            input.addEventListener("blur", () => {
                if (input.value.trim() === "") {
                    input.setAttribute("aria-invalid", "true");
                } else if (!input.hasAttribute("data-match")) {
                    input.removeAttribute("aria-invalid");
                }
            });

            input.addEventListener("input", () => {
                if (input.value.trim() !== "" && !input.hasAttribute("data-match")) {
                    input.removeAttribute("aria-invalid");
                }
            });
        });
    }

    /* ----------------------------------------------------------------------
       Loading state on submit
       Submit buttons carry data-loading-text. The form still submits
       normally; the button just locks and shows progress.
       ---------------------------------------------------------------------- */
    function initLoadingButtons() {
        const forms = document.querySelectorAll(".auth-form");

        forms.forEach((form) => {
            form.addEventListener("submit", () => {
                const button = form.querySelector(".auth-form__submit");
                if (!button || button.disabled) return;

                const loadingText = button.dataset.loadingText || "Please wait…";
                button.dataset.originalText = button.value || button.textContent;

                if (button.tagName === "INPUT") {
                    button.value = loadingText;
                } else {
                    button.textContent = loadingText;
                }

                button.classList.add("auth-form__submit--loading");
                // Disable on the next tick so the value is included in the POST.
                window.setTimeout(() => {
                    button.disabled = true;
                }, 0);
            });
        });
    }

    /* ----------------------------------------------------------------------
       Bootstrap
       ---------------------------------------------------------------------- */
    document.addEventListener("DOMContentLoaded", () => {
        initPasswordToggles();
        initStrengthMeters();
        initMatchChecks();
        initRequiredFeedback();
        initLoadingButtons();
    });
})();
