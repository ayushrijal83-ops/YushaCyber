/* ===========================================================================
   SOC Analyst workspace (YC-030.1).

   Drives the SOC-specific panels — dashboard, alert queue, playbook,
   checklist, closure form. The forensics panels below (evidence
   sources, unified timeline, correlation, notes, suspects) render
   themselves from /forensics/state via forensics.js — this script
   never duplicates that logic.

   Actions dispatched:
     open_alert       — payload: { alert_code }
     tick_checklist   — payload: { slug }
     select_playbook  — payload: { key }
     set_root_cause   — payload: { text }
     close_incident   — payload: { report }

   Everything else (select_source, select_artifact, add_note,
   link_artifacts, select_suspect) is a forensics action; the SOC
   simulator forwards those through to its composed
   ForensicsSimulator. forensics.js keeps working unchanged.
   =========================================================================== */
(function () {
    "use strict";

    var cfg = window.LAB_CONFIG;
    if (!cfg || !cfg.socStateUrl) return;

    var openList = document.getElementById("soc-open-list");
    var resolvedList = document.getElementById("soc-resolved-list");
    var alertDetail = document.getElementById("soc-alert-detail");
    var playbookCard = document.getElementById("soc-playbook");
    var playbookSelect = document.getElementById("soc-playbook-select");
    var playbookBody = document.getElementById("soc-playbook-body");
    var checklistCard = document.getElementById("soc-checklist-card");
    var checklist = document.getElementById("soc-checklist");
    var closureCard = document.getElementById("soc-closure");
    var rootCauseInput = document.getElementById("soc-root-cause");
    var reportInput = document.getElementById("soc-report");
    var closeBtn = document.getElementById("soc-close-btn");
    var closureChecks = document.getElementById("soc-closure-checks");
    if (!openList || !alertDetail || !closeBtn) return;

    var SEVERITY_CLASS = {
        critical: "sev--crit", high: "sev--high",
        medium: "sev--med", low: "sev--low",
        informational: "sev--info"
    };
    var PHASE_LABEL = {
        identification: "Identification",
        containment: "Containment",
        eradication: "Eradication",
        recovery: "Recovery",
        lessons_learned: "Lessons Learned"
    };

    function el(tag, cls, text) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text != null) node.textContent = text;
        return node;
    }

    /* ---------------------------------------------------------------------
       Dashboard stat cards.
       ------------------------------------------------------------------ */
    function renderStats(stats) {
        stats = stats || {};
        document.getElementById("soc-stat-open").textContent =
            stats.open || 0;
        document.getElementById("soc-stat-crit").textContent =
            stats.critical || 0;
        document.getElementById("soc-stat-high").textContent =
            stats.high || 0;
        document.getElementById("soc-stat-med").textContent =
            stats.medium || 0;
        document.getElementById("soc-stat-resolved").textContent =
            stats.resolved || 0;
    }

    /* ---------------------------------------------------------------------
       Alert queue rows.
       ------------------------------------------------------------------ */
    function renderQueue(list, alerts, activeCode) {
        list.innerHTML = "";
        if (!alerts || !alerts.length) {
            list.appendChild(el("li", "soc-alert__empty",
                "No alerts."));
            return;
        }
        alerts.forEach(function (alert) {
            var row = el("li", "soc-alert");
            if (alert.alert_code === activeCode) {
                row.classList.add("is-active");
            }
            row.classList.add(SEVERITY_CLASS[alert.severity] || "");
            row.appendChild(el("span", "soc-alert__code",
                alert.alert_code));
            row.appendChild(el("span", "soc-alert__title",
                alert.title));
            row.appendChild(el("span",
                "soc-alert__severity",
                alert.severity));
            var meta = el("span", "soc-alert__meta",
                (alert.source || "") + " · " + (alert.at_time || ""));
            row.appendChild(meta);
            row.addEventListener("click", function () {
                window.LabWorkspace.sendAction({
                    type: "open_alert",
                    payload: { alert_code: alert.alert_code }
                }).then(refresh);
            });
            list.appendChild(row);
        });
    }

    /* ---------------------------------------------------------------------
       Alert detail card.
       ------------------------------------------------------------------ */
    function renderAlertDetail(alert) {
        if (!alert) {
            alertDetail.innerHTML =
                '<p class="soc-hint">Pick an alert on the left '
                + "to open its investigation workspace.</p>";
            return;
        }
        alertDetail.innerHTML = "";
        var head = el("header", "soc-card__head");
        head.appendChild(el("h3", "soc-card__title",
            alert.alert_code + " — " + alert.title));
        head.appendChild(el("span",
            "soc-alert__severity soc-severity "
            + (SEVERITY_CLASS[alert.severity] || ""),
            alert.severity));
        alertDetail.appendChild(head);

        var grid = el("div", "soc-detail__grid");
        function row(label, value) {
            grid.appendChild(el("span", "soc-detail__label", label));
            grid.appendChild(el("span", "soc-detail__value",
                value || "—"));
        }
        row("Type", alert.alert_type || "");
        row("Source", alert.source || "");
        row("Time", alert.at_time || "");
        row("Status", alert.status || "");
        row("Assigned", alert.assigned_analyst || "unassigned");
        alertDetail.appendChild(grid);

        if (alert.description) {
            alertDetail.appendChild(el("p", "soc-detail__desc",
                alert.description));
        }
    }

    /* ---------------------------------------------------------------------
       Playbook viewer + selector.
       ------------------------------------------------------------------ */
    function renderPlaybook(state) {
        if (!state.active_alert) {
            playbookCard.hidden = true;
            return;
        }
        playbookCard.hidden = false;

        /* Populate selector once we have the full playbook list. */
        var current = playbookSelect.value;
        playbookSelect.innerHTML = "";
        playbookSelect.appendChild(new Option("— pick playbook —", ""));
        (state.playbook_options || []).forEach(function (pb) {
            /* Playbooks are keyed by their alert_type. */
            playbookSelect.appendChild(
                new Option(pb.title, pb.alert_type));
        });
        var selected = state.selected_playbook || current;
        if (selected) playbookSelect.value = selected;

        /* Render the selected playbook's steps grouped by phase. */
        playbookBody.innerHTML = "";
        var selectedPlaybook = (state.playbook && state.playbook.phases)
            ? state.playbook : null;
        if (!selectedPlaybook || !selectedPlaybook.phases.length) {
            playbookBody.appendChild(el("p", "soc-hint",
                "Pick a playbook to see the response steps."));
            return;
        }
        selectedPlaybook.phases.forEach(function (phase) {
            if (!phase.steps || !phase.steps.length) return;
            var block = el("div", "soc-phase");
            block.appendChild(el("h4", "soc-phase__title",
                phase.label || phase.key || phase.phase || ""));
            var ol = el("ol", "soc-phase__steps");
            (phase.steps || []).forEach(function (step) {
                var li = el("li", "");
                li.appendChild(el("strong", "", step.title));
                if (step.body) {
                    li.appendChild(el("span", "soc-step__body",
                        " — " + step.body));
                }
                ol.appendChild(li);
            });
            block.appendChild(ol);
            playbookBody.appendChild(block);
        });
    }

    /* Selecting a playbook fires the SOC action. */
    playbookSelect.addEventListener("change", function () {
        if (!playbookSelect.value) return;
        window.LabWorkspace.sendAction({
            type: "select_playbook",
            payload: { alert_type: playbookSelect.value }
        }).then(refresh);
    });

    /* ---------------------------------------------------------------------
       Checklist.
       ------------------------------------------------------------------ */
    function renderChecklist(items, ticked, activeAlert) {
        if (!activeAlert) {
            checklistCard.hidden = true;
            return;
        }
        checklistCard.hidden = false;
        checklist.innerHTML = "";
        if (!items || !items.length) {
            checklist.appendChild(el("li", "soc-hint",
                "No checklist for this alert."));
            return;
        }
        var tickedSet = {};
        (ticked || []).forEach(function (s) { tickedSet[s] = true; });
        items.forEach(function (item) {
            var li = el("li", "soc-check");
            var box = el("input", "soc-check__box");
            box.type = "checkbox";
            box.checked = !!tickedSet[item.slug];
            box.addEventListener("change", function () {
                window.LabWorkspace.sendAction({
                    type: "tick_checklist",
                    payload: { slug: item.slug }
                }).then(refresh);
            });
            var label = el("span", "soc-check__text", item.text);
            if (item.is_required) {
                label.appendChild(el("span", "soc-check__req", "req"));
            }
            li.appendChild(box);
            li.appendChild(label);
            checklist.appendChild(li);
        });
    }

    /* ---------------------------------------------------------------------
       Closure form.
       ------------------------------------------------------------------ */
    function renderClosure(state) {
        if (!state.active_alert) {
            closureCard.hidden = true;
            return;
        }
        closureCard.hidden = false;

        /* Only overwrite the input if the server-side state differs and
           the user isn't currently editing that field. */
        if (state.root_cause && document.activeElement !== rootCauseInput
                && rootCauseInput.value !== state.root_cause) {
            rootCauseInput.value = state.root_cause;
        }

        renderClosureChecks(state.closure_checks || {},
                            state.incident_closed);
    }

    function renderClosureChecks(checks, closed) {
        closureChecks.innerHTML = "";
        function badge(label, ok) {
            var span = el("span",
                "soc-check-badge soc-check-badge--"
                + (ok ? "ok" : "bad"),
                (ok ? "✓ " : "✖ ") + label);
            closureChecks.appendChild(span);
        }
        if (!Object.keys(checks).length) {
            closureChecks.appendChild(el("span", "soc-hint",
                "Ready to close when playbook, checklist, root cause "
                + "and report are all in place."));
            return;
        }
        badge("playbook", !!checks.playbook);
        badge("root cause", !!checks.root_cause);
        badge("report length", !!checks.report_length);
        badge("report sections", !!checks.report_sections);
        badge("checklist", !!checks.checklist);
        if (closed) {
            closureChecks.appendChild(el("span",
                "soc-check-badge soc-check-badge--closed",
                "incident closed"));
        }
    }

    /* Live-update root cause on blur so the objective can fire before
       the user hits close. */
    rootCauseInput.addEventListener("blur", function () {
        var text = (rootCauseInput.value || "").trim();
        if (!text) return;
        window.LabWorkspace.sendAction({
            type: "set_root_cause", payload: { text: text }
        }).then(refresh);
    });

    closeBtn.addEventListener("click", function () {
        var report = (reportInput.value || "").trim();
        if (!report) {
            reportInput.focus();
            return;
        }
        /* Push the root cause synchronously before closing in case
           the blur handler didn't fire (some browsers skip blur when
           the click happens fast). */
        var rootCause = (rootCauseInput.value || "").trim();
        var chain = rootCause
            ? window.LabWorkspace.sendAction({
                type: "set_root_cause", payload: { text: rootCause }
            })
            : Promise.resolve();
        chain.then(function () {
            return window.LabWorkspace.sendAction({
                type: "close_incident",
                payload: { report: report }
            });
        }).then(refresh);
    });

    /* ---------------------------------------------------------------------
       Refresh from /soc/state.
       ------------------------------------------------------------------ */
    function refresh() {
        return fetch(cfg.socStateUrl, {
            credentials: "same-origin"
        }).then(function (r) { return r.json(); }).then(function (data) {
            renderStats(data.stats);
            var activeCode = data.active_alert
                ? data.active_alert.alert_code : "";
            renderQueue(openList, data.open_queue, activeCode);
            renderQueue(resolvedList, data.resolved_queue, activeCode);
            renderAlertDetail(data.active_alert);
            renderPlaybook({
                active_alert: data.active_alert,
                playbook: data.playbook,
                selected_playbook: data.selected_playbook,
                playbook_options: data.playbook_options || []
            });
            renderChecklist(data.checklist, data.ticked,
                            data.active_alert);
            renderClosure({
                active_alert: data.active_alert,
                root_cause: data.root_cause,
                closure_checks: data.closure_checks,
                incident_closed: data.incident_closed
            });
        }).catch(function () { /* keep UI as-is on transient errors */ });
    }

    /* Refresh after every action dispatched by any script (including
       forensics.js) so SOC panels stay in sync with forensics ones. */
    if (window.LabWorkspace && window.LabWorkspace.onResult) {
        window.LabWorkspace.onResult(function () { refresh(); });
    }
    refresh();
})();
