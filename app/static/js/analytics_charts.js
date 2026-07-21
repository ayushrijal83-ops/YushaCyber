/* ===========================================================================
   Analytics charts (YC-033.0)

   Thin, dependency-light glue: reads the JSON payload embedded by the
   template (no extra requests), themes Chart.js with the platform's
   CSS variables, and instantiates one chart per canvas that exists on
   the page. All numbers are server-computed — this file only draws.
   =========================================================================== */
(function () {
    "use strict";
    if (typeof Chart === "undefined") return;

    function cssVar(name, fallback) {
        var v = getComputedStyle(document.documentElement)
            .getPropertyValue(name).trim();
        return v || fallback;
    }

    var TEXT = cssVar("--color-text-muted", "#7a8794");
    var GRID = "rgba(122, 135, 148, .15)";
    var GREEN = cssVar("--color-primary", "#00ff88");
    var BLUE = "#6fb7ff";
    var AMBER = "#ffb454";
    var PURPLE = "#b98cff";
    var RED = "#ff6b6b";
    var CYAN = "#4dd6d6";

    Chart.defaults.color = TEXT;
    Chart.defaults.borderColor = GRID;
    Chart.defaults.font.family =
        "'JetBrains Mono', 'Segoe UI', system-ui, monospace";
    Chart.defaults.font.size = 11;

    function payload(id) {
        var node = document.getElementById(id);
        if (!node) return null;
        try { return JSON.parse(node.textContent); }
        catch (e) { return null; }
    }

    function shortLabels(labels) {
        return labels.map(function (iso) { return iso.slice(5); });
    }

    function baseOptions(yTitle) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false },
                     ticks: { maxTicksLimit: 10 } },
                y: { beginAtZero: true, grid: { color: GRID },
                     title: yTitle
                         ? { display: true, text: yTitle } : undefined }
            }
        };
    }

    function line(canvas, labels, data, color, fill, yTitle) {
        return new Chart(canvas, {
            type: "line",
            data: { labels: labels, datasets: [{
                data: data, borderColor: color, borderWidth: 2,
                pointRadius: 0, pointHitRadius: 12, tension: .3,
                fill: fill,
                backgroundColor: fill ? color + "22" : undefined,
                spanGaps: true
            }] },
            options: baseOptions(yTitle)
        });
    }

    function bars(canvas, labels, data, color, yTitle) {
        return new Chart(canvas, {
            type: "bar",
            data: { labels: labels, datasets: [{
                data: data, backgroundColor: color + "aa",
                borderColor: color, borderWidth: 1, borderRadius: 3,
                maxBarThickness: 18
            }] },
            options: baseOptions(yTitle)
        });
    }

    /* ---------------- overview page ---------------- */
    var series = payload("ana-series");
    if (series) {
        var labels = shortLabels(series.labels);
        var byId = function (id) { return document.getElementById(id); };
        if (byId("chart-dau")) {
            line(byId("chart-dau"), labels, series.daily_active,
                 GREEN, true, "students");
        }
        if (byId("chart-xp")) {
            line(byId("chart-xp"), labels, series.xp_growth,
                 PURPLE, true, "XP (cumulative)");
        }
        if (byId("chart-lessons")) {
            bars(byId("chart-lessons"), labels, series.lessons,
                 BLUE, "completions");
        }
        if (byId("chart-quiz")) {
            var quiz = new Chart(byId("chart-quiz"), {
                type: "line",
                data: { labels: labels, datasets: [{
                    data: series.quiz_pass_rate, borderColor: AMBER,
                    borderWidth: 2, pointRadius: 2, tension: .3,
                    spanGaps: true
                }] },
                options: (function () {
                    var opts = baseOptions("pass rate %");
                    opts.scales.y.max = 100;
                    return opts;
                })()
            });
            void quiz;
        }
        if (byId("chart-labs")) {
            bars(byId("chart-labs"), labels, series.labs,
                 CYAN, "completions");
        }
        if (byId("chart-ctf")) {
            bars(byId("chart-ctf"), labels, series.ctf,
                 RED, "solves");
        }
    }

    /* ---------------- student detail page ---------------- */
    var trend = payload("ana-student-trend");
    var trendCanvas = document.getElementById("chart-student-xp");
    if (trend && trendCanvas) {
        line(trendCanvas, shortLabels(trend.labels), trend.data,
             GREEN, true, "XP earned (30d, cumulative)");
    }
})();
