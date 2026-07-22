/* ===========================================================================
   Forensics workstation (YC-029.5.2).

   Drives the forensic workstation UI. Every interaction runs through the
   SAME pipeline as the terminal via window.LabWorkspace.sendAction — so
   objectives, XP, the status panel and the completion modal all behave
   identically whether the student clicks or (in future) types. After each
   action the panel state re-fetches from /forensics/state, so metadata,
   hash viewer and the findings marks stay in sync with server state.

   Actions posted:
     select   payload: { asset_id }                  — inspect evidence
     flag     payload: { asset_id }                  — toggle suspicious
     submit   payload: { modified_slug, modified_hash,
                         modified_time, suspicious_slug }
   =========================================================================== */
(function () {
    "use strict";

    var cfg = window.LAB_CONFIG;
    if (!cfg || !cfg.forensicsStateUrl) return;

    var explorer = document.getElementById("fx-explorer");
    var metadata = document.getElementById("fx-metadata");
    var hashBox = document.getElementById("fx-hash");
    var timeline = document.getElementById("fx-timeline");
    var findings = document.getElementById("fx-findings");
    var modifiedSlug = document.getElementById("fx-modified-slug");
    var modifiedHash = document.getElementById("fx-modified-hash");
    var modifiedTime = document.getElementById("fx-modified-time");
    var suspiciousSlug = document.getElementById("fx-suspicious-slug");
    var submitBtn = document.getElementById("fx-submit");
    /* Applied-lab (YC-029.5.3) DOM. */
    var sourcesCard = document.getElementById("fx-sources");
    var sourceTabs = document.getElementById("fx-source-tabs");
    var sourceViewer = document.getElementById("fx-source-viewer");
    var reportCard = document.getElementById("fx-report");
    var reportFirstLogin = document.getElementById("fx-first-login");
    var reportUsbSerial = document.getElementById("fx-usb-serial");
    var reportDownload = document.getElementById("fx-download");
    var reportSuspiciousUrl = document.getElementById("fx-suspicious-url");
    var reportTimelineFirst = document.getElementById("fx-timeline-first");
    var reportSummary = document.getElementById("fx-report-summary");
    var submitReport = document.getElementById("fx-submit-report");
    if (!explorer || !metadata || !submitBtn) return;

    var KIND_ICON = {
        document: "📄", image: "🖼", pdf: "📕", archive: "🗃",
        usb: "🔌", browser: "🌐", download: "⬇", recycle_bin: "🗑"
    };
    var KIND_LABEL = {
        document: "Documents", image: "Images", pdf: "PDFs",
        archive: "Archives", usb: "USB Devices",
        browser: "Browser Data", download: "Downloads",
        recycle_bin: "Recycle Bin"
    };

    var currentView = null;
    var currentMetadata = {};
    var currentSelected = "";
    var currentFlagged = [];
    var currentChecks = {};
    var currentActiveSource = "";
    var currentOpenedSources = [];

    function el(tag, cls, text) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text != null) node.textContent = text;
        return node;
    }

    /* ---------------------------------------------------------------------
       Explorer (left column).
       ------------------------------------------------------------------ */
    function renderExplorer() {
        explorer.innerHTML = "";
        var grouped = currentView.grouped || {};
        var kinds = Object.keys(grouped).sort(function (a, b) {
            return (KIND_LABEL[a] || a).localeCompare(KIND_LABEL[b] || b);
        });
        if (!kinds.length) {
            explorer.appendChild(
                el("div", "fx-empty", "No evidence in this case."));
            return;
        }
        kinds.forEach(function (kind) {
            explorer.appendChild(
                el("div", "fx-explorer__title",
                   KIND_LABEL[kind] || kind));
            grouped[kind].forEach(function (item) {
                var row = el("div", "fx-item");
                row.setAttribute("data-slug", item.slug);
                if (item.slug === currentSelected) row.classList.add("is-active");
                row.appendChild(el("span", "fx-item__icon",
                                   KIND_ICON[item.kind] || "📄"));
                row.appendChild(el("span", "fx-item__name",
                                   item.filename));
                var flagBtn = el("button", "fx-flag-btn",
                                 currentFlagged.indexOf(item.slug) >= 0
                                     ? "flagged" : "flag");
                if (currentFlagged.indexOf(item.slug) >= 0) {
                    flagBtn.classList.add("is-on");
                }
                flagBtn.addEventListener("click", function (e) {
                    e.stopPropagation();
                    sendFlag(item.slug);
                });
                row.appendChild(flagBtn);
                row.addEventListener("click", function () {
                    sendSelect(item.slug);
                });
                explorer.appendChild(row);
            });
        });
    }

    /* ---------------------------------------------------------------------
       Metadata + Hash panels.
       ------------------------------------------------------------------ */
    function renderMetadata() {
        var head = '<header class="fx-card__head">'
            + '<h3 class="fx-card__title">Metadata</h3>'
            + "</header>";
        if (!currentSelected || !currentMetadata[currentSelected]) {
            metadata.innerHTML = head
                + '<p class="fx-card__hint">Select an evidence item '
                + "on the left to inspect its metadata.</p>";
            hashBox.innerHTML = '<header class="fx-card__head">'
                + '<h3 class="fx-card__title">Hash Viewer</h3>'
                + "</header>"
                + '<p class="fx-card__hint">MD5 and SHA-256 appear here '
                + "once an item is selected.</p>";
            return;
        }
        var m = currentMetadata[currentSelected];
        var body = '<div class="fx-meta">'
            + row("Filename", m.filename)
            + row("Extension", m.extension || "—")
            + row("Owner", m.owner)
            + row("Created", m.created)
            + row("Modified", m.modified)
            + row("Size", m.size)
            + "</div>"
            + (m.notes ? '<p class="fx-card__hint" style="margin-top:10px">'
                + escapeHtml(m.notes) + "</p>" : "");
        metadata.innerHTML = head + body;
        hashBox.innerHTML = '<header class="fx-card__head">'
            + '<h3 class="fx-card__title">Hash Viewer '
            + '(simulated · deterministic)</h3></header>'
            + hashRow("MD5", m.md5)
            + hashRow("SHA-256", m.sha256);
        wireCopyButtons();
    }
    function row(label, value) {
        return '<span class="fx-meta__label">' + escapeHtml(label) + "</span>"
            + '<span class="fx-meta__value">' + escapeHtml(value || "—")
            + "</span>";
    }
    function hashRow(algo, digest) {
        return '<div class="fx-hash__row">'
            + '<span class="fx-hash__algo">' + algo + "</span>"
            + '<span class="fx-hash__digest">' + digest + "</span>"
            + '<button type="button" class="fx-hash__copy" '
            + 'data-copy="' + digest + '">copy</button></div>';
    }
    function wireCopyButtons() {
        hashBox.querySelectorAll(".fx-hash__copy").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var value = btn.getAttribute("data-copy") || "";
                try {
                    navigator.clipboard.writeText(value);
                    btn.textContent = "copied";
                    setTimeout(function () { btn.textContent = "copy"; }, 1200);
                } catch (e) { /* clipboard blocked — no-op */ }
            });
        });
    }

    /* ---------------------------------------------------------------------
       Timeline.
       ------------------------------------------------------------------ */
    var KIND_TL_ICON = {
        login: "🔑", usb: "🔌", file_created: "📄",
        file_modified: "✎", download: "⬇", recycle_bin: "🗑",
        logout: "🚪", other: "•"
    };
    function renderTimeline() {
        var list = timeline.querySelector(".fx-timeline__list");
        list.innerHTML = "";
        (currentView.timeline || []).forEach(function (event) {
            var row = el("li", "fx-tl");
            if (event.evidence_slug && event.evidence_slug === currentSelected) {
                row.classList.add("is-active");
            }
            row.appendChild(el("span", "fx-tl__time", event.at_time));
            row.appendChild(el("span", "fx-tl__icon",
                               KIND_TL_ICON[event.kind] || "•"));
            row.appendChild(el("span", "", event.description));
            row.appendChild(el("span", "fx-tl__kind",
                               (event.kind || "other").replace("_", " ")));
            if (event.evidence_slug) {
                row.addEventListener("click", function () {
                    sendSelect(event.evidence_slug);
                });
            }
            list.appendChild(row);
        });
    }

    /* ---------------------------------------------------------------------
       Findings form.
       ------------------------------------------------------------------ */
    function populateSelects() {
        var evidence = currentView.evidence || [];
        [modifiedSlug, suspiciousSlug].forEach(function (sel) {
            var current = sel.value;
            sel.innerHTML = "";
            sel.appendChild(new Option("— pick one —", ""));
            evidence.forEach(function (item) {
                sel.appendChild(new Option(item.filename, item.slug));
            });
            if (current) sel.value = current;
        });
    }
    function renderChecks() {
        function mark(node, ok) {
            if (!node) return;
            if (ok == null) {
                node.textContent = ""; node.className = "fx-field__mark";
            } else {
                node.textContent = ok ? "✓ correct" : "✖ try again";
                node.className = "fx-field__mark fx-field__mark--"
                    + (ok ? "ok" : "bad");
            }
        }
        mark(document.getElementById("fx-mark-slug"),
             pick(currentChecks, "modified_slug"));
        mark(document.getElementById("fx-mark-hash"),
             pick(currentChecks, "modified_hash"));
        mark(document.getElementById("fx-mark-time"),
             pick(currentChecks, "modified_time"));
        mark(document.getElementById("fx-mark-susp"),
             pick(currentChecks, "suspicious_slug"));
    }
    function pick(obj, key) {
        if (!obj || !Object.prototype.hasOwnProperty.call(obj, key)) return null;
        return !!obj[key];
    }

    submitBtn.addEventListener("click", function () {
        window.LabWorkspace.sendAction({
            type: "submit", payload: {
                modified_slug: modifiedSlug.value || "",
                modified_hash: (modifiedHash.value || "").trim(),
                modified_time: (modifiedTime.value || "").trim(),
                suspicious_slug: suspiciousSlug.value || ""
            }
        }).then(refresh);
    });

    /* ---------------------------------------------------------------------
       Action senders — go through the shared pipeline.
       ------------------------------------------------------------------ */
    function sendSelect(slug) {
        window.LabWorkspace.sendAction({
            type: "select", payload: { asset_id: slug }
        }).then(refresh);
    }
    function sendFlag(slug) {
        window.LabWorkspace.sendAction({
            type: "flag", payload: { asset_id: slug }
        }).then(refresh);
    }

    /* ---------------------------------------------------------------------
       Refresh from /forensics/state.
       ------------------------------------------------------------------ */
    function refresh() {
        return fetch(cfg.forensicsStateUrl, {
            credentials: "same-origin"
        }).then(function (r) { return r.json(); }).then(function (data) {
            currentView = data.view || {};
            currentMetadata = currentView.metadata || {};
            currentSelected = data.selected || "";
            currentFlagged = data.flagged || [];
            currentChecks = data.checks || {};
            currentActiveSource = data.active_source || "";
            currentOpenedSources = data.opened_sources || [];
            var applied = (currentView.mode === "applied");
            toggleMode(applied);
            renderExplorer();
            if (applied) {
                renderSourceTabs();
                renderSourceViewer();
                renderUnifiedTimeline();
                populateReportSelects();
                renderReportChecks();
            } else {
                renderMetadata();
                renderTimeline();
                populateSelects();
                renderChecks();
            }
        }).catch(function () { /* keep the UI as-is on transient errors */ });
    }

    function toggleMode(applied) {
        /* Fundamentals panels visible only in fundamentals mode. */
        [metadata, hashBox, findings].forEach(function (n) {
            if (n) n.hidden = applied;
        });
        /* Applied panels visible only in applied mode. */
        [sourcesCard, reportCard].forEach(function (n) {
            if (n) n.hidden = !applied;
        });
    }

    /* ---------------------------------------------------------------------
       Applied-lab renderers.
       ------------------------------------------------------------------ */
    var SOURCE_TAB_ICON = {
        browser_history: "🌐", downloads: "⬇", event_log: "📋",
        usb_history: "🔌", login_history: "🔑", recent_docs: "📄"
    };

    function renderSourceTabs() {
        if (!sourceTabs) return;
        sourceTabs.innerHTML = "";
        var sources = currentView.sources || [];
        if (!sources.length) {
            sourceTabs.appendChild(el("div", "fx-empty",
                "No source data seeded for this case."));
            return;
        }
        sources.forEach(function (source) {
            var opened = currentOpenedSources.indexOf(source.source_type) >= 0;
            var tab = el("button", "fx-source-tab");
            if (source.source_type === currentActiveSource) {
                tab.classList.add("is-active");
            }
            if (opened) tab.classList.add("is-opened");
            tab.appendChild(el("span", "fx-source-tab__icon",
                SOURCE_TAB_ICON[source.source_type] || "•"));
            tab.appendChild(el("span", "fx-source-tab__label",
                source.label));
            tab.appendChild(el("span", "fx-source-tab__count",
                "(" + source.count + ")"));
            tab.addEventListener("click", function () {
                sendSelectSource(source.source_type);
            });
            sourceTabs.appendChild(tab);
        });
    }

    function renderSourceViewer() {
        if (!sourceViewer) return;
        var active = currentActiveSource;
        if (!active) {
            sourceViewer.innerHTML =
                '<p class="fx-card__hint">Pick a source tab above to open its viewer.</p>';
            return;
        }
        var schema = (currentView.schema && currentView.schema[active]) || [];
        var rows = (currentView.artifacts_by_source
            && currentView.artifacts_by_source[active]) || [];
        var table = el("table", "fx-source-table");
        var thead = el("thead", "");
        var tr = el("tr", "");
        tr.appendChild(el("th", "", "Time"));
        schema.forEach(function (field) {
            tr.appendChild(el("th", "", field.replace(/_/g, " ")));
        });
        thead.appendChild(tr);
        table.appendChild(thead);
        var tbody = el("tbody", "");
        rows.forEach(function (artifact) {
            var row = el("tr", "fx-source-row");
            row.setAttribute("data-id", artifact.id);
            if (artifact.is_key) row.classList.add("is-key");
            row.appendChild(el("td", "fx-source-row__time",
                artifact.at_time));
            schema.forEach(function (field) {
                var value = (artifact.data || {})[field];
                var td = el("td", "");
                if (typeof value === "number"
                    && field.indexOf("size") >= 0) {
                    td.textContent = formatSize(value);
                } else {
                    td.textContent = value == null ? "" : String(value);
                }
                row.appendChild(td);
            });
            row.addEventListener("click", function () {
                window.LabWorkspace.sendAction({
                    type: "select_artifact",
                    payload: { artifact_id: artifact.id }
                }).then(refresh);
            });
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        sourceViewer.innerHTML = "";
        sourceViewer.appendChild(el("h4", "fx-source-viewer__title",
            (SOURCE_TAB_ICON[active] || "") + " "
            + ((currentView.sources || []).find(function (s) {
                return s.source_type === active;
            }) || { label: active }).label));
        sourceViewer.appendChild(table);
    }

    function formatSize(n) {
        if (n < 1024) return n + " B";
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
        return (n / (1024 * 1024)).toFixed(1) + " MB";
    }

    function renderUnifiedTimeline() {
        var list = timeline.querySelector(".fx-timeline__list");
        if (!list) return;
        list.innerHTML = "";
        (currentView.unified_timeline || []).forEach(function (event) {
            var row = el("li", "fx-tl");
            row.appendChild(el("span", "fx-tl__time", event.at_time));
            row.appendChild(el("span", "fx-tl__icon",
                SOURCE_TAB_ICON[event.source] || "•"));
            row.appendChild(el("span", "", event.description));
            row.appendChild(el("span", "fx-tl__kind",
                (event.source || "other").replace("_", " ")));
            list.appendChild(row);
        });
    }

    function populateReportSelects() {
        if (!reportTimelineFirst) return;
        var current = reportTimelineFirst.value;
        reportTimelineFirst.innerHTML = "";
        reportTimelineFirst.appendChild(new Option("— pick one —", ""));
        (currentView.sources || []).forEach(function (source) {
            reportTimelineFirst.appendChild(
                new Option(source.label, source.source_type));
        });
        if (current) reportTimelineFirst.value = current;
    }

    function renderReportChecks() {
        function mark(node, ok) {
            if (!node) return;
            if (ok == null) {
                node.textContent = ""; node.className = "fx-field__mark";
            } else {
                node.textContent = ok ? "✓ correct" : "✖ try again";
                node.className = "fx-field__mark fx-field__mark--"
                    + (ok ? "ok" : "bad");
            }
        }
        mark(document.getElementById("fx-mark-first-login"),
             pick(currentChecks, "first_login"));
        mark(document.getElementById("fx-mark-usb"),
             pick(currentChecks, "usb_serial"));
        mark(document.getElementById("fx-mark-download"),
             pick(currentChecks, "download"));
        mark(document.getElementById("fx-mark-website"),
             pick(currentChecks, "website"));
        mark(document.getElementById("fx-mark-timeline"),
             pick(currentChecks, "timeline"));
        mark(document.getElementById("fx-mark-report"),
             pick(currentChecks, "report"));
    }

    function sendSelectSource(sourceType) {
        window.LabWorkspace.sendAction({
            type: "select_source",
            payload: { source_type: sourceType }
        }).then(refresh);
    }

    if (submitReport) {
        submitReport.addEventListener("click", function () {
            window.LabWorkspace.sendAction({
                type: "submit", payload: {
                    first_login_time: (reportFirstLogin.value || "").trim(),
                    usb_serial: (reportUsbSerial.value || "").trim(),
                    downloaded_filename:
                        (reportDownload.value || "").trim(),
                    suspicious_url:
                        (reportSuspiciousUrl.value || "").trim(),
                    timeline_first_kind:
                        reportTimelineFirst.value || "",
                    report_summary:
                        (reportSummary.value || "").trim()
                }
            }).then(refresh);
        });
    }

    function escapeHtml(text) {
        return String(text == null ? "" : text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    /* Refresh after every action anyone dispatches — keeps every panel
       in sync when someone eventually adds terminal commands too. */
    if (window.LabWorkspace && window.LabWorkspace.onResult) {
        window.LabWorkspace.onResult(function () { refresh(); });
    }
    refresh();
})();
