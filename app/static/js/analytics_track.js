/* ===========================================================================
   Analytics tracker (YC-033.0) — hint usage.

   Deliberately decoupled: a capture-phase listener on the existing
   hint button, zero changes to lab_terminal.js. Fire-and-forget POST;
   failures are swallowed — analytics must never break a lab.
   =========================================================================== */
(function () {
    "use strict";

    var hintBtn = document.getElementById("lw-hint");
    var curBox = document.getElementById("lw-current");
    if (!hintBtn || !curBox) return;

    var lab = (window.location.pathname.match(/\/labs\/([^/]+)/) || [])[1];

    hintBtn.addEventListener("click", function () {
        if (hintBtn.disabled) return;
        var objectiveId = parseInt(curBox.dataset.for || "", 10);
        if (!objectiveId) return;
        try {
            fetch("/admin/analytics/events", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": (window.LAB_CONFIG || {}).csrf || ""
                },
                body: JSON.stringify({
                    event_type: "hint_used",
                    subject_type: "objective",
                    subject_id: objectiveId,
                    meta: { lab: lab || "" }
                }),
                keepalive: true
            }).catch(function () { /* analytics never breaks labs */ });
        } catch (e) { /* ignore */ }
    }, true);
})();
