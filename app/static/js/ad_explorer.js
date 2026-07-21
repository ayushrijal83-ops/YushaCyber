/* ===========================================================================
   Active Directory object explorer (YC-031.0)

   Renders the domain tree (OUs → users/computers, groups, shares, GPOs)
   and drives every interaction through the SAME pipeline as the
   terminal: clicking a node runs the matching `get-*` command via
   window.LabWorkspace.run(), so output, objectives, XP, the status
   panel and the completion modal all behave identically whether the
   student types or clicks. After every action the tree re-fetches, so
   moves, disables and membership changes appear live.
   =========================================================================== */
(function () {
    "use strict";

    var box = document.getElementById("adx");
    var cfg = window.LAB_CONFIG;
    if (!box || !cfg || !cfg.adStateUrl) return;

    var ICONS = {
        domain: "🏢", ou: "📁", user: "👤", computer: "🖥",
        group: "👥", share: "📂", gpo: "📜"
    };
    var selected = "";

    function el(tag, cls, text) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text) node.textContent = text;
        return node;
    }

    function badge(text, kind) {
        return el("span", "adx__badge adx__badge--" + kind, text);
    }

    /* One clickable object row. ref = "kind:key", cmd = command to run. */
    function nodeButton(ref, icon, label, cmd, badges) {
        var btn = el("button", "adx__node");
        btn.type = "button";
        btn.setAttribute("data-ref", ref);
        if (ref === selected) btn.classList.add("is-selected");
        var ic = el("span", "adx__icon", icon);
        ic.setAttribute("aria-hidden", "true");
        btn.appendChild(ic);
        btn.appendChild(el("span", "", label));
        (badges || []).forEach(function (b) { btn.appendChild(b); });
        btn.addEventListener("click", function () {
            selected = ref;
            markSelection();
            if (window.LabWorkspace) window.LabWorkspace.run(cmd);
        });
        return btn;
    }

    function markSelection() {
        box.querySelectorAll(".adx__node").forEach(function (b) {
            b.classList.toggle("is-selected",
                b.getAttribute("data-ref") === selected);
        });
    }

    function section(title, count, open) {
        var details = el("details", "adx__section");
        if (open) details.open = true;
        var summary = el("summary", "", title);
        summary.appendChild(el("span", "adx__count", String(count)));
        details.appendChild(summary);
        var items = el("div", "adx__items");
        details.appendChild(items);
        return { details: details, items: items };
    }

    function render(tree) {
        /* Remember which sections the user left open across refreshes. */
        var openTitles = {};
        box.querySelectorAll(".adx__section").forEach(function (d) {
            var t = d.querySelector("summary");
            if (t) openTitles[t.firstChild.textContent] = d.open;
        });
        var wasEmpty = !box.childNodes.length;

        box.innerHTML = "";
        var domainRow = el("div", "adx__domain");
        domainRow.appendChild(el("span", "adx__icon", ICONS.domain));
        domainRow.appendChild(el("span", "", tree.domain.name || "DOMAIN"));
        box.appendChild(domainRow);

        function isOpen(title, fallback) {
            return (title in openTitles) ? openTitles[title] : fallback;
        }

        (tree.ous || []).forEach(function (ou) {
            var total = ou.users.length + ou.computers.length;
            var sec = section(ou.name, total,
                isOpen(ou.name, wasEmpty ? total > 0 && total <= 6 : false));
            ou.users.forEach(function (u) {
                var badges = [];
                if (u.locked) badges.push(badge("locked", "locked"));
                if (!u.enabled) badges.push(badge("disabled", "disabled"));
                sec.items.appendChild(nodeButton(
                    "user:" + u.sam, ICONS.user, u.sam,
                    "get-user " + u.sam, badges));
            });
            ou.computers.forEach(function (c) {
                var badges = c.is_dc ? [badge("DC", "dc")] : [];
                sec.items.appendChild(nodeButton(
                    "computer:" + c.name.toLowerCase(), ICONS.computer,
                    c.name, "get-computer " + c.name.toLowerCase(), badges));
            });
            if (!total) sec.items.appendChild(
                el("div", "adx__node", "(empty)"));
            box.appendChild(sec.details);
        });

        var groups = section("Groups", (tree.groups || []).length,
                             isOpen("Groups", false));
        (tree.groups || []).forEach(function (g) {
            var badges = [el("span", "adx__count", String(g.member_count))];
            if (g.slug === "domain-admins") badges.push(badge("priv", "warn"));
            groups.items.appendChild(nodeButton(
                "group:" + g.slug, ICONS.group, g.name,
                'get-group "' + g.name + '"', badges));
        });
        box.appendChild(groups.details);

        var shares = section("Shared Folders", (tree.shares || []).length,
                             isOpen("Shared Folders", false));
        (tree.shares || []).forEach(function (s) {
            shares.items.appendChild(nodeButton(
                "share:" + s.slug, ICONS.share, s.name,
                "get-share " + s.slug, []));
        });
        box.appendChild(shares.details);

        var gpos = section("Group Policy", (tree.gpos || []).length,
                           isOpen("Group Policy", false));
        (tree.gpos || []).forEach(function (g) {
            gpos.items.appendChild(nodeButton(
                "gpo:" + g.slug, ICONS.gpo, g.name,
                "get-gpo " + g.slug, []));
        });
        box.appendChild(gpos.details);
        markSelection();
    }

    function refreshTree() {
        fetch(cfg.adStateUrl, { headers: { "Accept": "application/json" } })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.tree) render(data.tree);
            })
            .catch(function () { /* keep the last good tree */ });
    }

    /* Live updates: whenever ANY terminal action completes, re-fetch. */
    if (window.LabWorkspace && window.LabWorkspace.onResult) {
        window.LabWorkspace.onResult(function () { refreshTree(); });
    }

    refreshTree();
})();
