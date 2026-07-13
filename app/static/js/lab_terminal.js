/* YushaCyber Lab Engine — terminal client (YC-012.1).
   Vanilla JS, no framework. It is a DUMB CLIENT: it sends actions and renders
   whatever the server returns. All simulation, validation, progress and XP
   happen server-side — the client never holds authoritative state, and never
   learns an objective's expected answer. */
(function () {
    "use strict";

    var cfg = window.LAB_CONFIG;
    if (!cfg) return;

    var screen = document.getElementById("term-screen");
    var form = document.getElementById("term-form");
    var input = document.getElementById("term-input");
    var promptEl = document.getElementById("term-prompt");
    var resetBtn = document.getElementById("lab-reset");
    if (!screen || !form || !input) return;

    var history = [];
    var histIndex = -1;

    function append(text, cls) {
        var pre = document.createElement("pre");
        pre.className = "lab-term__line" + (cls ? " " + cls : "");
        pre.textContent = text;
        screen.appendChild(pre);
        screen.scrollTop = screen.scrollHeight;
    }

    function refreshObjectives(objectives) {
        if (!objectives) return;
        objectives.forEach(function (o) {
            var li = document.querySelector('[data-objective="' + o.id + '"]');
            if (!li) return;
            li.classList.toggle("is-done", !!o.completed);
            var check = li.querySelector(".lab-obj__check");
            if (check) check.textContent = o.completed ? "✓" : "○";
        });
    }

    function toast(msg) {
        append(msg, "lab-term__reward");
    }

    function send(type, payload) {
        return fetch(cfg.actionUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": cfg.csrf
            },
            body: JSON.stringify({ type: type, payload: payload })
        }).then(function (r) { return r.json(); });
    }

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var command = input.value;
        if (!command.trim()) return;

        append((promptEl ? promptEl.textContent : "$ ") + command, "lab-term__echo");
        history.push(command);
        histIndex = history.length;
        input.value = "";

        send("command", { command: command })
            .then(function (res) {
                if (!res.ok) { append("Something went wrong.", "lab-term__err"); return; }

                if (res.clear) {
                    screen.innerHTML = "";
                } else if (res.output) {
                    append(res.output);
                }
                if (res.prompt && promptEl) promptEl.textContent = res.prompt;

                refreshObjectives(res.objectives);

                (res.newly_completed || []).forEach(function (o) {
                    toast("✅ Objective complete: " + o.title + "  (+" + o.xp + " XP)");
                });
                if (res.lab_completed) {
                    toast("🎉 Lab complete! Well done.");
                }
            })
            .catch(function () { append("Network error.", "lab-term__err"); });
    });

    /* command history with arrow keys */
    input.addEventListener("keydown", function (e) {
        if (e.key === "ArrowUp") {
            if (histIndex > 0) { histIndex--; input.value = history[histIndex]; }
            e.preventDefault();
        } else if (e.key === "ArrowDown") {
            if (histIndex < history.length - 1) {
                histIndex++; input.value = history[histIndex];
            } else { histIndex = history.length; input.value = ""; }
            e.preventDefault();
        }
    });

    screen.addEventListener("click", function () { input.focus(); });

    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            if (!confirm("Reset the terminal? Your completed objectives and XP are kept.")) return;
            fetch(cfg.resetUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf }
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    screen.innerHTML = "";
                    append("Session reset. Type 'help' to begin.", "lab-term__welcome");
                    refreshObjectives(res.objectives);
                });
        });
    }
})();
