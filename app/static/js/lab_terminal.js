/* YushaCyber — Interactive Lab terminal (YC-012.2).
   Vanilla JS. No xterm.js, no libraries, no jQuery.

   This is a DUMB CLIENT: it sends commands and renders what the server
   returns. All simulation, objective validation, progress and XP happen
   server-side (Lab Engine, YC-012.1). The client never holds authoritative
   state and never learns an objective's expected answer. */
(function () {
    "use strict";

    var cfg = window.LAB_CONFIG;
    if (!cfg) return;

    var screen   = document.getElementById("lw-screen");
    var input    = document.getElementById("lw-input");
    var promptEl = document.getElementById("lw-prompt");
    var inputRow = document.getElementById("lw-inputrow");
    var resetBtn = document.getElementById("lw-reset");
    var hintBtn  = document.getElementById("lw-hint");
    var hintBox  = document.getElementById("lw-hints");
    var hintN    = document.getElementById("lw-hint-n");
    var curBox   = document.getElementById("lw-current");
    var curText  = document.getElementById("lw-current-text");
    var fill     = document.getElementById("lw-fill");
    var pctEl    = document.getElementById("lw-pct");
    var doneEl   = document.getElementById("lw-done");
    var modal    = document.getElementById("lw-modal");
    var modalXp  = document.getElementById("lw-modal-xp");
    if (!screen || !input) return;

    var history = [];       // command history (↑ / ↓)
    var histIdx = -1;
    var draft   = "";       // preserves what was typed before browsing history
    var hintsShown = 0;     // progressive hint counter for the current objective
    var busy = false;

    /* ---------- rendering ---------- */
    function line(text, cls) {
        var pre = document.createElement("pre");
        pre.className = "lw-line" + (cls ? " " + cls : "");
        pre.textContent = text;
        screen.appendChild(pre);
        autoscroll();
        return pre;
    }
    function autoscroll() { screen.scrollTop = screen.scrollHeight; }

    /* ---------- objectives / progress ---------- */
    function currentObjective(objectives) {
        for (var i = 0; i < objectives.length; i++) {
            if (!objectives[i].completed) return objectives[i];
        }
        return null;
    }

    function refresh(objectives) {
        if (!objectives) return;
        var done = 0;

        objectives.forEach(function (o) {
            var li = document.querySelector('[data-objective="' + o.id + '"]');
            if (o.completed) done++;
            if (!li) return;
            var wasDone = li.classList.contains("is-done");
            li.classList.toggle("is-done", !!o.completed);
            li.classList.remove("is-current");
            var box = li.querySelector(".lw-obj__box");
            if (box) box.textContent = o.completed ? "✔" : "☐";
            if (o.completed && !wasDone) {
                li.classList.add("just-done");
                setTimeout(function () { li.classList.remove("just-done"); }, 900);
            }
        });

        /* progress bar */
        var pct = cfg.total ? Math.round((done / cfg.total) * 100) : 0;
        if (fill)  fill.style.width = pct + "%";
        if (pctEl) pctEl.textContent = pct + "%";
        if (doneEl) doneEl.textContent = done;

        /* current objective + highlight */
        var cur = currentObjective(objectives);
        if (cur) {
            var li = document.querySelector('[data-objective="' + cur.id + '"]');
            if (li) li.classList.add("is-current");
            if (curText) curText.textContent = cur.instruction;
            if (curBox) curBox.hidden = false;
            /* new objective -> reset the hint ladder */
            if (curBox && curBox.dataset.for !== String(cur.id)) {
                curBox.dataset.for = String(cur.id);
                hintsShown = 0;
                if (hintBox) hintBox.innerHTML = "";
                if (hintBtn) hintBtn.disabled = false;
                updateHintLabel(cur);
            }
        } else if (curBox) {
            curBox.hidden = true;   /* all done */
        }
    }

    function objectiveHints(id) {
        var li = document.querySelector('[data-objective="' + id + '"]');
        if (!li) return [];
        try { return JSON.parse(li.dataset.hints || "[]"); } catch (e) { return []; }
    }

    function updateHintLabel(cur) {
        if (!hintBtn || !hintN || !cur) return;
        var hints = objectiveHints(cur.id);
        hintN.textContent = hints.length ? "(" + hintsShown + "/" + hints.length + ")" : "";
        hintBtn.disabled = hintsShown >= hints.length;
        hintBtn.textContent = hintsShown === 0 ? "💡 Show hint " : "💡 Next hint ";
        hintBtn.appendChild(hintN);
    }

    /* ---------- hints: one at a time, never the answer up front ---------- */
    if (hintBtn) {
        hintBtn.addEventListener("click", function () {
            var id = curBox && curBox.dataset.for;
            if (!id) return;
            var hints = objectiveHints(id);
            if (hintsShown >= hints.length) return;

            var p = document.createElement("p");
            p.className = "lw-hint";
            p.textContent = "Hint " + (hintsShown + 1) + ": " + hints[hintsShown];
            hintBox.appendChild(p);
            hintsShown++;

            updateHintLabel({ id: id });
        });
    }

    /* ---------- server round-trip ---------- */
    function send(command) {
        busy = true;
        return fetch(cfg.actionUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf },
            body: JSON.stringify({ type: "command", payload: { command: command } })
        })
            .then(function (r) { return r.json(); })
            .finally(function () { busy = false; });
    }

    function run(command) {
        /* echo the command exactly as a real shell would */
        line((promptEl ? promptEl.textContent : "$ ") + command, "lw-line--echo");

        send(command).then(function (res) {
            if (!res || !res.ok) { line("Unable to run that. Try again.", "lw-line--err"); return; }

            if (res.clear) {
                screen.innerHTML = "";
            } else if (res.output) {
                line(res.output);
            }
            if (res.prompt && promptEl) promptEl.textContent = res.prompt;

            refresh(res.objectives);

            (res.newly_completed || []).forEach(function (o) {
                line("✔ Objective complete — " + o.title + "   (+" + o.xp + " XP)", "lw-line--win");
            });

            if (res.lab_completed) {
                showComplete(res.objectives);
            }
            autoscroll();
        }).catch(function () {
            line("Network error.", "lw-line--err");
        });
    }

    /* ---------- completion modal ---------- */
    function showComplete(objectives) {
        if (!modal) return;
        var xp = 0;
        (objectives || []).forEach(function (o) { if (o.completed) xp += (o.xp_reward || 0); });
        xp += (cfg.labXp || 0);                       /* + lab completion bonus */
        if (modalXp) modalXp.textContent = "+" + xp;
        setTimeout(function () { modal.hidden = false; }, 800);
    }
    document.querySelectorAll("[data-modal-close]").forEach(function (el) {
        el.addEventListener("click", function () { modal.hidden = true; });
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal && !modal.hidden) modal.hidden = true;
    });

    /* ---------- input: typing, Enter, history ---------- */
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            if (busy) return;
            var cmd = input.value;
            if (!cmd.trim()) { line((promptEl ? promptEl.textContent : "$ ")); return; }
            history.push(cmd);
            histIdx = history.length;
            draft = "";
            input.value = "";
            run(cmd);
            return;
        }

        if (e.key === "ArrowUp") {
            e.preventDefault();
            if (!history.length) return;
            if (histIdx === history.length) draft = input.value;   /* keep the draft */
            if (histIdx > 0) histIdx--;
            input.value = history[histIdx];
            moveCaretToEnd();
            return;
        }

        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (!history.length) return;
            if (histIdx < history.length - 1) {
                histIdx++;
                input.value = history[histIdx];
            } else {
                histIdx = history.length;
                input.value = draft;                                /* restore the draft */
            }
            moveCaretToEnd();
            return;
        }

        /* Ctrl+L clears, like a real shell */
        if (e.key === "l" && e.ctrlKey) {
            e.preventDefault();
            screen.innerHTML = "";
        }
    });

    function moveCaretToEnd() {
        var v = input.value;
        setTimeout(function () { input.setSelectionRange(v.length, v.length); }, 0);
    }

    /* clicking anywhere in the terminal focuses the input (real-terminal feel) */
    [screen, inputRow].forEach(function (el) {
        if (el) el.addEventListener("click", function () { input.focus(); });
    });

    /* animated cursor follows the typed text */
    function syncCursor() {
        if (!inputRow) return;
        inputRow.classList.toggle("is-typing", input.value.length > 0);
    }
    input.addEventListener("input", syncCursor);

    /* ---------- reset ---------- */
    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            if (!confirm("Reset the terminal? Completed objectives and earned XP are kept.")) return;
            fetch(cfg.resetUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf }
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    screen.innerHTML = "";
                    line("Session reset. Type 'help' to see the available commands.", "lw-line--sys");
                    if (promptEl) promptEl.textContent = "student@linux-lab:~$ ";
                    refresh(res.objectives);
                    input.focus();
                });
        });
    }

    /* ---------- boot ---------- */
    refresh(cfg.objectives || []);       /* real objective data from the server */
    input.focus();                       /* focus terminal on page load */
})();
