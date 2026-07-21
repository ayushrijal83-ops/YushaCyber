/* ===========================================================================
   Cloud management console tree (YC-032.0)

   Renders the account's resources (IAM, storage, network, security
   groups, compute, databases, policy) and drives every interaction
   through the SAME pipeline as the terminal: clicking a resource runs
   the matching command via window.LabWorkspace.run(), so output,
   objectives, XP, the status panel and the completion modal all behave
   identically whether the student types or clicks. After every action
   the tree re-fetches, so remediations (private buckets, revoked rules,
   disabled users) appear live.
   =========================================================================== */
(function () {
    "use strict";

    var box = document.getElementById("cldx");
    var cfg = window.LAB_CONFIG;
    if (!box || !cfg || !cfg.cloudStateUrl) return;

    var ICONS = {
        account: "☁", user: "👤", role: "🔑", bucket: "🪣",
        vpc: "🌐", subnet: "▦", sg: "🛡", vm: "🖥", lb: "⚖",
        db: "🗄", policy: "📜"
    };
    var selected = "";

    function el(tag, cls, text) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text) node.textContent = text;
        return node;
    }

    function badge(text, kind) {
        return el("span", "cldx__badge cldx__badge--" + kind, text);
    }

    /* One clickable resource row. ref = "kind:key", cmd = command. */
    function nodeButton(ref, icon, label, cmd, badges) {
        var btn = el("button", "cldx__node");
        btn.type = "button";
        btn.setAttribute("data-ref", ref);
        if (ref === selected) btn.classList.add("is-selected");
        var ic = el("span", "cldx__icon", icon);
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
        box.querySelectorAll(".cldx__node").forEach(function (b) {
            b.classList.toggle("is-selected",
                b.getAttribute("data-ref") === selected);
        });
    }

    function section(title, count, open) {
        var details = el("details", "cldx__section");
        if (open) details.open = true;
        var summary = el("summary", "", title);
        summary.appendChild(el("span", "cldx__count", String(count)));
        details.appendChild(summary);
        var items = el("div", "cldx__items");
        details.appendChild(items);
        return { details: details, items: items };
    }

    function render(tree) {
        /* Remember which sections the user left open across refreshes. */
        var openTitles = {};
        box.querySelectorAll(".cldx__section").forEach(function (d) {
            var t = d.querySelector("summary");
            if (t) openTitles[t.firstChild.textContent] = d.open;
        });
        var wasEmpty = !box.childNodes.length;

        box.innerHTML = "";
        var accountRow = el("div", "cldx__domain");
        accountRow.appendChild(el("span", "cldx__icon", ICONS.account));
        accountRow.appendChild(el("span", "",
            (tree.account && tree.account.name) || "ACCOUNT"));
        box.appendChild(accountRow);

        function isOpen(title, fallback) {
            return (title in openTitles) ? openTitles[title] : fallback;
        }

        var iam = tree.iam || {};
        var users = section("IAM Users", (iam.users || []).length,
                            isOpen("IAM Users", wasEmpty));
        (iam.users || []).forEach(function (u) {
            var badges = [];
            if (!u.enabled) badges.push(badge("disabled", "disabled"));
            else if (u.admin && u.stale) badges.push(badge("stale", "stale"));
            else if (u.admin) badges.push(badge("admin", "warn"));
            users.items.appendChild(nodeButton(
                "user:" + u.username, ICONS.user, u.username,
                "get-user " + u.username, badges));
        });
        box.appendChild(users.details);

        var roles = section("IAM Roles", (iam.roles || []).length,
                            isOpen("IAM Roles", false));
        (iam.roles || []).forEach(function (r) {
            var badges = r.admin ? [badge("full", "warn")] : [];
            roles.items.appendChild(nodeButton(
                "role:" + r.slug, ICONS.role, r.slug,
                "get-role " + r.slug, badges));
        });
        box.appendChild(roles.details);

        var buckets = section("Storage Buckets", (tree.buckets || []).length,
                              isOpen("Storage Buckets", wasEmpty));
        (tree.buckets || []).forEach(function (b) {
            var badges = [b.public ? badge("public", "public")
                                   : badge("private", "ok")];
            buckets.items.appendChild(nodeButton(
                "bucket:" + b.slug, ICONS.bucket, b.name,
                "get-bucket " + b.slug, badges));
        });
        box.appendChild(buckets.details);

        var nets = section("Network", (tree.network || []).length,
                           isOpen("Network", false));
        (tree.network || []).forEach(function (v) {
            nets.items.appendChild(nodeButton(
                "vpc:" + v.slug, ICONS.vpc, v.name + "  " + v.cidr,
                "network", []));
            (v.subnets || []).forEach(function (s) {
                var badges = s.public ? [badge("public", "stale")] : [];
                nets.items.appendChild(nodeButton(
                    "subnet:" + s.slug, ICONS.subnet,
                    "  " + s.slug + "  " + s.cidr, "network", badges));
            });
        });
        box.appendChild(nets.details);

        var sgs = section("Security Groups",
                          (tree.security_groups || []).length,
                          isOpen("Security Groups", false));
        (tree.security_groups || []).forEach(function (g) {
            var badges = g.open_ssh ? [badge("ssh open", "public")] : [];
            sgs.items.appendChild(nodeButton(
                "sg:" + g.slug, ICONS.sg, g.name,
                "get-sg " + g.slug, badges));
        });
        box.appendChild(sgs.details);

        var vms = section("Virtual Machines", (tree.vms || []).length,
                          isOpen("Virtual Machines", false));
        (tree.vms || []).forEach(function (m) {
            var badges = m.public ? [badge("public ip", "stale")] : [];
            vms.items.appendChild(nodeButton(
                "vm:" + m.slug, ICONS.vm, m.name,
                "get-vm " + m.slug, badges));
        });
        box.appendChild(vms.details);

        var lbs = section("Load Balancers",
                          (tree.load_balancers || []).length,
                          isOpen("Load Balancers", false));
        (tree.load_balancers || []).forEach(function (b) {
            lbs.items.appendChild(nodeButton(
                "lb:" + b.slug, ICONS.lb, b.name, "list-lbs", []));
        });
        box.appendChild(lbs.details);

        var dbs = section("Databases", (tree.databases || []).length,
                          isOpen("Databases", false));
        (tree.databases || []).forEach(function (d) {
            var badges = [d.public ? badge("exposed", "public")
                                   : badge("private", "ok")];
            dbs.items.appendChild(nodeButton(
                "db:" + d.slug, ICONS.db, d.name,
                "get-db " + d.slug, badges));
        });
        box.appendChild(dbs.details);

        var pol = section("Account Policy", 1, isOpen("Account Policy",
                                                      false));
        pol.items.appendChild(nodeButton(
            "policy:password", ICONS.policy, "Password policy",
            "password-policy", []));
        box.appendChild(pol.details);

        markSelection();
    }

    function refreshTree() {
        fetch(cfg.cloudStateUrl,
              { headers: { "Accept": "application/json" } })
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
