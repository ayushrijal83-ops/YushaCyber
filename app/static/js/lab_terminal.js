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
    var statusEl = document.getElementById("lw-status");
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
    /* Terminal DOM is optional (YC-029.5.2: forensics labs are pure
       inspector — no terminal is rendered). When absent we still export
       LabWorkspace so panel-only simulators can dispatch actions and
       subscribe to result hooks — but skip everything that reads/writes
       the screen and input elements. */
    var hasTerminal = !!(screen && input);

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

    /* ---------- simulator status panel (generic key/value items) ---------- */
    function renderStatus(items) {
        if (!statusEl || !items || !items.length) return;
        statusEl.innerHTML = "";
        items.forEach(function (item) {
            var row = document.createElement("div");
            row.className = "lw-status__item";
            var label = document.createElement("span");
            label.className = "lw-status__label";
            label.textContent = item.label || "";
            var value = document.createElement("span");
            value.className = "lw-status__value" +
                (item.state ? " lw-status__value--" + item.state : "");
            value.textContent = item.value || "";
            row.appendChild(label);
            row.appendChild(value);
            statusEl.appendChild(row);
        });
    }

    /* ---------- server round-trip ---------- */
    function send(command) {
        return sendAction({ type: "command", payload: { command: command } });
    }

    function sendAction(action) {
        busy = true;
        return fetch(cfg.actionUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf },
            body: JSON.stringify(action)
        })
            .then(function (r) { return r.json(); })
            .finally(function () { busy = false; });
    }

    function run(command) {
        /* echo the command exactly as a real shell would */
        line((promptEl ? promptEl.textContent : "$ ") + command, "lw-line--echo");

        return send(command).then(function (res) {
            if (!res || !res.ok) { line("Unable to run that. Try again.", "lw-line--err"); return; }

            if (res.clear) {
                screen.innerHTML = "";
            } else if (res.output) {
                line(res.output);
            }
            if (res.prompt && promptEl) promptEl.textContent = res.prompt;
            renderStatus(res.status);

            refresh(res.objectives);

            (res.newly_completed || []).forEach(function (o) {
                line("✔ Objective complete — " + o.title + "   (+" + o.xp + " XP)", "lw-line--win");
            });

            if (res.lab_completed) {
                showComplete(res.objectives, res);
            }
            autoscroll();
            return res;
        }).catch(function () {
            line("Network error.", "lw-line--err");
        });
    }

    /* ---------- completion modal ---------- */
    function showComplete(objectives, res) {
        if (!modal) return;
        var xp = 0;
        (objectives || []).forEach(function (o) { if (o.completed) xp += (o.xp_reward || 0); });
        xp += (cfg.labXp || 0);
        if (modalXp) modalXp.textContent = "+" + xp;

        /* Commands used (YC-026.5) */
        var cmdsEl = document.getElementById("lw-modal-cmds");
        if (cmdsEl && res && res.commands_used) {
            cmdsEl.textContent = res.commands_used;
        }

        /* Next Lab link (YC-026.5) */
        var nextBtn = document.getElementById("lw-modal-next");
        if (nextBtn && res && res.next_lab_url) {
            nextBtn.href = res.next_lab_url;
        }

        /* Achievements (YC-026.5) */
        var achBox = document.getElementById("lw-modal-achievements");
        var achList = document.getElementById("lw-modal-ach-list");
        if (achBox && achList && res && res.achievements_earned && res.achievements_earned.length) {
            achBox.hidden = false;
            achList.innerHTML = "";
            res.achievements_earned.forEach(function (a) {
                var li = document.createElement("li");
                li.textContent = a.title + " (+" + a.xp + " XP)";
                achList.appendChild(li);
            });
        }

        setTimeout(function () { modal.hidden = false; }, 800);
    }
    document.querySelectorAll("[data-modal-close]").forEach(function (el) {
        el.addEventListener("click", function () { modal.hidden = true; });
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal && !modal.hidden) modal.hidden = true;
    });

    /* ---------- input: typing, Enter, history ---------- */
    if (hasTerminal) input.addEventListener("keydown", function (e) {
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
    if (hasTerminal) [screen, inputRow].forEach(function (el) {
        if (el) el.addEventListener("click", function () { input.focus(); });
    });

    /* animated cursor follows the typed text */
    function syncCursor() {
        if (!inputRow) return;
        inputRow.classList.toggle("is-typing", input.value.length > 0);
    }
    if (hasTerminal) input.addEventListener("input", syncCursor);

    /* ---------- copy output (YC-026.2) ---------- */
    var copyBtn = document.getElementById("lw-copy");
    if (copyBtn) {
        copyBtn.addEventListener("click", function () {
            var text = screen.innerText || screen.textContent || "";
            var done = function () {
                var lbl = copyBtn.querySelector(".lw-term__copy-label");
                var original = lbl ? lbl.textContent : "";
                if (lbl) { lbl.textContent = "Copied"; }
                copyBtn.classList.add("is-copied");
                window.setTimeout(function () {
                    if (lbl) { lbl.textContent = original || "Copy"; }
                    copyBtn.classList.remove("is-copied");
                }, 1400);
            };
            var fallback = function () {
                var ta = document.createElement("textarea");
                ta.value = text;
                ta.setAttribute("readonly", "");
                ta.style.position = "fixed"; ta.style.top = "-1000px";
                document.body.appendChild(ta);
                ta.select();
                try { document.execCommand("copy"); done(); }
                finally { document.body.removeChild(ta); }
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(done).catch(fallback);
            } else {
                fallback();
            }
        });
    }

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
                    if (promptEl) promptEl.textContent =
                        res.prompt || cfg.bootPrompt || "student@linux-lab:~$ ";
                    renderStatus(res.status);
                    refresh(res.objectives);
                    input.focus();
                });
        });
    }

    /* ---------- interactive topology (YC-026.0) ---------- */
    var topoBox = document.getElementById("lw-topo");
    if (topoBox && cfg.topology && cfg.topology.nodes && cfg.topology.nodes.length) {
        var svg = topoBox.querySelector("svg");
        var linksG = svg.querySelector("#lw-topo-links");
        var nodesG = svg.querySelector("#lw-topo-nodes");
        var selectedHost = null;   /* current highlight; the server owns real state */

        var W = 720, H = 340;
        var deviceIcon = {
            router: "\uD83D\uDCE1", switch: "\u26A1", pc: "\uD83D\uDCBB",
            server: "\uD83D\uDDA5", firewall: "\uD83D\uDD25"
        };

        /* Place nodes with a simple hub-and-spoke: router at top-left, switch
           centred, everything else spread around the switch. This works for the
           YC-026.0 topology; more complex ones can override in future labs. */
        function layout(nodes) {
            var pos = {};
            var switchNode = nodes.filter(function (n) { return n.device_type === "switch"; })[0];
            var router = nodes.filter(function (n) { return n.device_type === "router"; })[0];
            var others = nodes.filter(function (n) {
                return n.device_type !== "switch" && n.device_type !== "router";
            });
            if (router) pos[router.hostname] = { x: 120, y: 70 };
            if (switchNode) pos[switchNode.hostname] = { x: 360, y: 170 };
            var n = others.length || 1;
            others.forEach(function (node, i) {
                var span = 520;
                var x = 100 + (i * span / Math.max(n - 1, 1));
                pos[node.hostname] = { x: x, y: 285 };
            });
            return pos;
        }

        var pos = layout(cfg.topology.nodes);

        function draw() {
            linksG.innerHTML = "";
            nodesG.innerHTML = "";
            cfg.topology.links.forEach(function (l) {
                var a = pos[l.a], b = pos[l.b];
                if (!a || !b) return;
                var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
                line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
                if (selectedHost && (l.a === selectedHost || l.b === selectedHost)) {
                    line.setAttribute("stroke", "var(--color-primary)");
                    line.setAttribute("stroke-width", "3");
                    line.setAttribute("filter", "url(#lw-glow)");
                }
                linksG.appendChild(line);
            });
            cfg.topology.nodes.forEach(function (node) {
                var p = pos[node.hostname]; if (!p) return;
                var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                g.setAttribute("transform", "translate(" + p.x + "," + p.y + ")");
                g.setAttribute("class", "lw-topo__node"
                    + (selectedHost === node.hostname ? " is-selected" : ""));
                g.setAttribute("data-host", node.hostname);
                g.setAttribute("tabindex", "0");
                g.setAttribute("role", "button");
                g.setAttribute("aria-label", node.label + " (" + node.device_type + ")");
                var circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                circle.setAttribute("r", "26");
                g.appendChild(circle);
                var glyph = document.createElementNS("http://www.w3.org/2000/svg", "text");
                glyph.setAttribute("text-anchor", "middle");
                glyph.setAttribute("dominant-baseline", "central");
                glyph.setAttribute("font-size", "22");
                glyph.textContent = deviceIcon[node.device_type] || "\u2022";
                g.appendChild(glyph);
                var label = document.createElementNS("http://www.w3.org/2000/svg", "text");
                label.setAttribute("y", "48"); label.setAttribute("text-anchor", "middle");
                label.setAttribute("class", "lw-topo__label");
                label.textContent = node.label;
                g.appendChild(label);
                if (node.ip) {
                    var ip = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    ip.setAttribute("y", "64"); ip.setAttribute("text-anchor", "middle");
                    ip.setAttribute("class", "lw-topo__ip");
                    ip.textContent = node.ip;
                    g.appendChild(ip);
                }
                g.addEventListener("click", function () { selectHost(node.hostname); });
                g.addEventListener("keydown", function (e) {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault(); selectHost(node.hostname);
                    }
                });
                nodesG.appendChild(g);
            });
        }

        function selectHost(hostname) {
            if (busy) return;
            selectedHost = hostname;
            draw();
            sendAction({ type: "select", payload: { host: hostname } }).then(function (res) {
                if (!res || !res.ok) return;
                if (res.clear) { screen.innerHTML = ""; }
                if (res.output) { line(res.output, "lw-line--sys"); }
                if (res.prompt && promptEl) { promptEl.textContent = res.prompt; }
                renderStatus(res.status);
                refresh(res.objectives);
                (res.newly_completed || []).forEach(function (o) {
                    line("\u2714 Objective complete \u2014 " + o.title
                        + "   (+" + o.xp + " XP)", "lw-line--win");
                });
                if (res.lab_completed) { showComplete(res.objectives, res); }
                autoscroll();
                input.focus();
            });
        }

        draw();
    }

    /* ---------- boot ---------- */
    refresh(cfg.objectives || []);       /* real objective data from the server */
    if (hasTerminal) input.focus();      /* focus terminal on page load */

    /* ---------- workspace API (YC-031.0, additive) ----------
       Companion scripts (e.g. the AD object explorer) drive the SAME
       action pipeline instead of duplicating it: run() echoes the
       command, posts it, renders output, refreshes objectives and the
       status panel. onResult lets them react (refresh their tree). */
    var resultHooks = [];
    var _origRun = run;
    run = function (command) {
        var p = _origRun(command);
        if (p && p.then) {
            p.then(function (res) {
                resultHooks.forEach(function (cb) {
                    try { cb(res); } catch (e) { /* never break the terminal */ }
                });
                return res;
            });
        }
        return p;
    };
    window.LabWorkspace = {
        run: function (command) { return run(command); },
        sendAction: sendAction,
        line: line,
        refresh: refresh,
        renderStatus: renderStatus,
        onResult: function (cb) { if (typeof cb === "function") resultHooks.push(cb); }
    };
})();
