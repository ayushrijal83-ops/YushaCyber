"""Interactive SOC Analyst Simulator (YC-030.0).

Scenario-driven incident investigation where students read logs, filter
events, search for IOCs, build timelines, and submit incident reports.
Everything is pre-generated — no real SIEM, no real logs.

Architecture:
  · Scenario Engine — each scenario has alerts, log entries, a timeline,
    and acceptance criteria (attacker IP, compromised account, attack type)
  · Log Engine — ``logs`` command with source/severity/keyword filtering
  · Alert Engine — ``alerts`` command with severity filtering
  · Timeline Engine — ``timeline`` command showing the attack progression
  · Investigation Engine — ``search`` for IP/user/host/keyword
  · Report Engine — ``report`` command to submit findings
"""

from __future__ import annotations

from typing import Any, Callable

from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL, Action, ActionResult, Simulator,
)


# ---------------------------------------------------------------------------
# Log entry + alert structures
# ---------------------------------------------------------------------------
def _log(ts, source, severity, host, msg, **extra):
    return {"timestamp": ts, "source": source, "severity": severity,
            "host": host, "message": msg, **extra}

def _alert(ts, severity, title, desc, src_ip="", dst_ip="", **extra):
    return {"timestamp": ts, "severity": severity, "title": title,
            "description": desc, "src_ip": src_ip, "dst_ip": dst_ip, **extra}


# ---------------------------------------------------------------------------
# Scenarios — complete incident investigations
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, dict[str, Any]] = {
    "brute-force": {
        "title": "Brute Force Attack Investigation",
        "description": "Multiple failed login alerts triggered. Investigate whether an account was compromised.",
        "attacker_ip": "10.0.5.99",
        "compromised_account": "jsmith",
        "attack_type": "brute-force",
        "severity": "high",
        "affected_systems": ["dc-01", "web-01"],
        "alerts": [
            _alert("09:12:03", "medium", "Multiple Failed Logins", "5 failed logins from 10.0.5.99 to dc-01 in 60s", src_ip="10.0.5.99", dst_ip="10.0.1.10"),
            _alert("09:14:22", "high",   "Brute Force Detected",  "20 failed logins from 10.0.5.99 targeting jsmith", src_ip="10.0.5.99", dst_ip="10.0.1.10"),
            _alert("09:18:45", "high",   "Successful Login After Failures", "jsmith logged in from 10.0.5.99 after 23 failed attempts", src_ip="10.0.5.99", dst_ip="10.0.1.10"),
            _alert("09:22:11", "critical","New Admin Account Created", "Account 'backdoor_admin' created by jsmith on dc-01", src_ip="10.0.5.99", dst_ip="10.0.1.10"),
        ],
        "logs": [
            _log("09:10:01", "windows", "info",    "dc-01", "Event 4624: Successful logon for admin from 10.0.1.50", user="admin", event_id="4624"),
            _log("09:12:03", "windows", "warning", "dc-01", "Event 4625: Failed logon for jsmith from 10.0.5.99", user="jsmith", event_id="4625", ip="10.0.5.99"),
            _log("09:12:05", "windows", "warning", "dc-01", "Event 4625: Failed logon for jsmith from 10.0.5.99", user="jsmith", event_id="4625", ip="10.0.5.99"),
            _log("09:12:08", "windows", "warning", "dc-01", "Event 4625: Failed logon for jsmith from 10.0.5.99", user="jsmith", event_id="4625", ip="10.0.5.99"),
            _log("09:13:01", "windows", "warning", "dc-01", "Event 4625: Failed logon for jsmith from 10.0.5.99", user="jsmith", event_id="4625", ip="10.0.5.99"),
            _log("09:13:15", "windows", "warning", "dc-01", "Event 4625: Failed logon for jsmith from 10.0.5.99", user="jsmith", event_id="4625", ip="10.0.5.99"),
            _log("09:14:00", "firewall","info",    "fw-01", "ALLOW TCP 10.0.5.99:49821 -> 10.0.1.10:445 SMB", ip="10.0.5.99"),
            _log("09:14:22", "windows", "warning", "dc-01", "Event 4625: 20 total failed logons for jsmith in 3 minutes", user="jsmith", event_id="4625", ip="10.0.5.99"),
            _log("09:18:45", "windows", "info",    "dc-01", "Event 4624: Successful logon for jsmith from 10.0.5.99", user="jsmith", event_id="4624", ip="10.0.5.99"),
            _log("09:19:02", "windows", "warning", "dc-01", "Event 4672: Special privileges assigned to jsmith", user="jsmith", event_id="4672"),
            _log("09:20:30", "windows", "warning", "dc-01", "Event 4720: User account 'backdoor_admin' created by jsmith", user="jsmith", event_id="4720"),
            _log("09:22:11", "windows", "critical","dc-01", "Event 4732: backdoor_admin added to Domain Admins by jsmith", user="jsmith", event_id="4732"),
            _log("09:23:00", "dns",     "info",    "dns-01","DNS query: pastebin.com from 10.0.5.99", ip="10.0.5.99"),
            _log("09:24:15", "firewall","warning", "fw-01", "ALLOW TCP 10.0.5.99:50112 -> 104.16.0.1:443 HTTPS (pastebin.com)", ip="10.0.5.99"),
        ],
        "answer_keywords": {
            "attacker_ip": ["10.0.5.99"],
            "compromised_account": ["jsmith"],
            "attack_type": ["brute force", "brute-force", "password spray"],
            "severity": ["high", "critical"],
            "remediation": ["disable", "reset password", "block ip", "mfa", "lockout"],
        },
    },

    "port-scan-malware": {
        "title": "Port Scan & Malware Download",
        "description": "IDS detected a port scan followed by suspicious outbound traffic. Determine the scope.",
        "attacker_ip": "203.0.113.50",
        "compromised_account": "webadmin",
        "attack_type": "port-scan-malware",
        "severity": "critical",
        "affected_systems": ["web-01", "db-01"],
        "alerts": [
            _alert("14:02:00", "medium", "Port Scan Detected", "SYN scan from 203.0.113.50 against web-01 (1000+ ports)", src_ip="203.0.113.50", dst_ip="10.0.2.20"),
            _alert("14:08:30", "high",   "SQL Injection Attempt", "POST /search with SQLi payload from 203.0.113.50", src_ip="203.0.113.50", dst_ip="10.0.2.20"),
            _alert("14:15:00", "critical","Reverse Shell Detected", "Outbound connection from web-01 to 203.0.113.50:4444", src_ip="10.0.2.20", dst_ip="203.0.113.50"),
            _alert("14:22:00", "critical","Data Exfiltration", "Large data transfer from db-01 to 203.0.113.50", src_ip="10.0.2.30", dst_ip="203.0.113.50"),
        ],
        "logs": [
            _log("14:01:00", "firewall","info",    "fw-01", "ALLOW TCP 203.0.113.50 -> 10.0.2.20:80 HTTP", ip="203.0.113.50"),
            _log("14:02:00", "firewall","warning", "fw-01", "IDS: SYN scan detected from 203.0.113.50, 1247 ports probed", ip="203.0.113.50"),
            _log("14:05:00", "apache",  "info",    "web-01","GET /robots.txt from 203.0.113.50 - 200", ip="203.0.113.50"),
            _log("14:06:12", "apache",  "info",    "web-01","GET /admin from 203.0.113.50 - 403", ip="203.0.113.50"),
            _log("14:08:30", "apache",  "warning", "web-01","POST /search body='q=' UNION SELECT * FROM users--' from 203.0.113.50", ip="203.0.113.50"),
            _log("14:08:31", "apache",  "info",    "web-01","POST /search - 200 (returned 500 rows)", ip="203.0.113.50"),
            _log("14:10:00", "syslog",  "warning", "web-01","Connection to 203.0.113.50:4444 established (nc)", ip="203.0.113.50"),
            _log("14:12:00", "syslog",  "critical","web-01","Process: /bin/sh -i spawned by www-data", user="www-data"),
            _log("14:14:00", "syslog",  "warning", "web-01","whoami executed by www-data", user="www-data"),
            _log("14:15:00", "syslog",  "critical","web-01","Privilege escalation: www-data -> root via CVE-2024-1086", user="root"),
            _log("14:18:00", "syslog",  "critical","db-01", "mysqldump executed by root, output piped to nc 203.0.113.50:8080", user="root", ip="203.0.113.50"),
            _log("14:22:00", "firewall","critical","fw-01", "ALLOW TCP 10.0.2.30:3306 -> 203.0.113.50:8080 (50MB transferred)", ip="203.0.113.50"),
            _log("14:25:00", "dns",     "info",    "dns-01","DNS query: evil-c2.example.com from 10.0.2.20", ip="10.0.2.20"),
        ],
        "answer_keywords": {
            "attacker_ip": ["203.0.113.50"],
            "compromised_account": ["webadmin", "www-data", "root"],
            "attack_type": ["port scan", "sql injection", "reverse shell", "exfiltration", "malware"],
            "severity": ["critical"],
            "remediation": ["isolate", "patch", "waf", "block", "incident response"],
        },
    },

    "insider-threat": {
        "title": "Insider Threat Investigation",
        "description": "After-hours access and unusual data downloads flagged by DLP. Investigate the employee.",
        "attacker_ip": "10.0.3.15",
        "compromised_account": "mthompson",
        "attack_type": "insider-threat",
        "severity": "high",
        "affected_systems": ["file-01", "vpn-01"],
        "alerts": [
            _alert("23:15:00", "low",    "After-Hours VPN Login",  "mthompson connected via VPN at 23:15 (outside business hours)", src_ip="198.51.100.22", dst_ip="10.0.0.1"),
            _alert("23:22:00", "medium", "Unusual File Access",    "mthompson accessed 47 files in /confidential/financials/ in 5 min", src_ip="10.0.3.15"),
            _alert("23:30:00", "high",   "DLP Alert: Large Download", "mthompson downloaded 2.3GB from file-01 to USB", src_ip="10.0.3.15"),
            _alert("23:35:00", "high",   "Email with Attachment",  "mthompson sent email to personal address with 15MB attachment", src_ip="10.0.3.15"),
        ],
        "logs": [
            _log("23:15:00", "vpn",     "info",    "vpn-01","VPN connection established: mthompson from 198.51.100.22", user="mthompson", ip="198.51.100.22"),
            _log("23:16:00", "windows", "info",    "ws-15", "Event 4624: Logon for mthompson from VPN", user="mthompson", event_id="4624"),
            _log("23:18:00", "windows", "info",    "file-01","Event 4663: mthompson accessed \\\\file-01\\confidential\\Q4-report.xlsx", user="mthompson", event_id="4663"),
            _log("23:19:00", "windows", "info",    "file-01","Event 4663: mthompson accessed \\\\file-01\\confidential\\salary-data.csv", user="mthompson", event_id="4663"),
            _log("23:20:00", "windows", "info",    "file-01","Event 4663: mthompson accessed 45 more files in \\confidential\\financials\\", user="mthompson", event_id="4663"),
            _log("23:28:00", "windows", "warning", "ws-15", "USB device inserted: SanDisk 64GB", user="mthompson"),
            _log("23:30:00", "windows", "warning", "ws-15", "File copy: 2.3GB to E:\\ (USB)", user="mthompson"),
            _log("23:33:00", "windows", "info",    "ws-15", "Outlook: mthompson composed email to mthompson.personal@gmail.com", user="mthompson"),
            _log("23:35:00", "windows", "warning", "ws-15", "Email sent with 15MB attachment: financial-summary.zip", user="mthompson"),
            _log("23:40:00", "vpn",     "info",    "vpn-01","VPN disconnected: mthompson", user="mthompson"),
        ],
        "answer_keywords": {
            "attacker_ip": ["10.0.3.15", "198.51.100.22"],
            "compromised_account": ["mthompson"],
            "attack_type": ["insider", "data theft", "data exfiltration", "insider threat"],
            "severity": ["high"],
            "remediation": ["disable account", "hr", "legal", "dlp", "usb policy", "revoke access"],
        },
    },
}

# ---------------------------------------------------------------------------
# The Simulator
# ---------------------------------------------------------------------------
@register_simulator
class SOCSimulator(Simulator):
    """SOC Analyst investigation simulator (YC-030.0)."""

    key = "soc-analyst"
    capabilities_set = (CAP_TERMINAL,)

    SLUG_TO_SCENARIO = {
        "soc-brute-force": "brute-force",
        "soc-port-scan": "port-scan-malware",
        "soc-insider": "insider-threat",
    }

    def capabilities(self) -> set[str]:
        return set(self.capabilities_set)

    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        scenario_key = (content or {}).get("scenario", "brute-force")
        if lab and hasattr(lab, "slug"):
            scenario_key = self.SLUG_TO_SCENARIO.get(lab.slug, scenario_key)
        sc = SCENARIOS.get(scenario_key, SCENARIOS["brute-force"])
        return {
            "sim": self.key,
            "scenario_key": scenario_key,
            "flags": {},
            "commands_used": 0,
            "report_submitted": False,
        }

    def prompt(self, state: dict[str, Any]) -> str:
        return "soc-analyst> "

    def welcome(self, state: dict[str, Any]) -> str:
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        n_alerts = len(sc.get("alerts", []))
        n_logs = len(sc.get("logs", []))
        return (
            f"╔══════════════════════════════════════════════╗\n"
            f"║  SOC ANALYST CONSOLE — INCIDENT INVESTIGATION  ║\n"
            f"╚══════════════════════════════════════════════╝\n"
            f"\n"
            f"Case: {sc.get('title', 'Unknown')}\n"
            f"{sc.get('description', '')}\n"
            f"\n"
            f"  {n_alerts} alerts  ·  {n_logs} log entries\n"
            f"\n"
            f"Commands: alerts, logs, search, timeline, investigate,\n"
            f"          filter, hosts, report, help"
        )

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        return [
            {"label": "Case", "value": sc.get("title", "—")[:30]},
            {"label": "Severity", "value": sc.get("severity", "—").upper(), "state": "err" if sc.get("severity") == "critical" else "warn"},
            {"label": "Alerts", "value": str(len(sc.get("alerts", [])))},
            {"label": "Log Entries", "value": str(len(sc.get("logs", [])))},
            {"label": "Report", "value": "Submitted" if state.get("report_submitted") else "Pending"},
        ]

    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        state = dict(state) if state else self.bootstrap(None, {})
        if action.type == "command":
            return self._handle_command(state, action)
        return ActionResult(new_state=state)

    def _handle_command(self, state, action):
        raw = action.command.strip()
        if not raw:
            return ActionResult(new_state=state)
        state["commands_used"] = state.get("commands_used", 0) + 1
        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        dispatch = {
            "help": self._cmd_help,
            "alerts": self._cmd_alerts,
            "logs": self._cmd_logs,
            "search": self._cmd_search,
            "timeline": self._cmd_timeline,
            "filter": self._cmd_filter,
            "hosts": self._cmd_hosts,
            "investigate": self._cmd_investigate,
            "report": self._cmd_report,
            "clear": self._cmd_clear,
        }
        handler = dispatch.get(cmd)
        if not handler:
            return ActionResult(output=f"Unknown command: {cmd}. Type 'help'.", new_state=state)
        return handler(state, arg)

    def _cmd_help(self, state, arg):
        return ActionResult(output=(
            "SOC Analyst Commands:\n"
            "  alerts [severity]   view alert queue (critical/high/medium/low)\n"
            "  logs [source]       view logs (windows/firewall/apache/syslog/dns/vpn)\n"
            "  search <query>      search logs by IP, username, hostname, or keyword\n"
            "  timeline            show the attack timeline\n"
            "  filter <field> <val> filter logs by field (user, ip, host, severity)\n"
            "  hosts               list affected systems\n"
            "  investigate <ip|user> deep-dive on a specific IOC\n"
            "  report <findings>   submit your incident report\n"
            "  clear               clear the terminal"
        ), new_state=state, events=[{"type": "help_shown"}])

    def _cmd_alerts(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        alerts = sc.get("alerts", [])
        sev_filter = arg.strip().lower() if arg else ""
        if sev_filter:
            alerts = [a for a in alerts if a["severity"] == sev_filter]
        lines = [f"{'TIME':<12}{'SEV':<10}{'TITLE':<35}{'SRC IP':<18}{'DST IP'}"]
        lines.append("─" * 90)
        for a in alerts:
            sev_icon = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🔵"}.get(a["severity"],"⚪")
            lines.append(f"{a['timestamp']:<12}{sev_icon} {a['severity']:<8}{a['title']:<35}{a.get('src_ip','—'):<18}{a.get('dst_ip','—')}")
            lines.append(f"  └─ {a['description']}")
        lines.append(f"\n{len(alerts)} alert(s)" + (f" (filtered: {sev_filter})" if sev_filter else ""))
        state.setdefault("flags", {})["alerts_viewed"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "alerts_viewed", "count": len(alerts),
                                     "has_alerts": len(alerts) > 0}])

    def _cmd_logs(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        logs = sc.get("logs", [])
        source_filter = arg.strip().lower() if arg else ""
        if source_filter:
            logs = [l for l in logs if l["source"] == source_filter]
        lines = [f"{'TIME':<12}{'SOURCE':<10}{'SEV':<10}{'HOST':<10}{'MESSAGE'}"]
        lines.append("─" * 95)
        for l in logs:
            sev_color = {"critical":"🔴","warning":"🟡","info":"🔵"}.get(l["severity"],"⚪")
            lines.append(f"{l['timestamp']:<12}{l['source']:<10}{sev_color} {l['severity']:<8}{l['host']:<10}{l['message'][:60]}")
        lines.append(f"\n{len(logs)} log entries" + (f" (source: {source_filter})" if source_filter else ""))
        state.setdefault("flags", {})["logs_viewed"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "logs_viewed", "count": len(logs),
                                     "source": source_filter or "all"}])

    def _cmd_search(self, state, arg):
        if not arg:
            return ActionResult(output="Usage: search <ip|username|hostname|keyword>", new_state=state)
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        query = arg.strip().lower()
        matches = []
        for l in sc.get("logs", []):
            text = f"{l['timestamp']} {l['source']} {l['host']} {l['message']} {l.get('user','')} {l.get('ip','')} {l.get('event_id','')}".lower()
            if query in text:
                matches.append(l)
        lines = [f"Search results for: {arg} ({len(matches)} matches)"]
        lines.append("─" * 80)
        for l in matches:
            lines.append(f"  {l['timestamp']}  [{l['source']}] {l['host']}: {l['message'][:65]}")
        if not matches:
            lines.append("  No results found.")
        state.setdefault("flags", {}).setdefault("searches", [])
        if query not in state["flags"]["searches"]:
            state["flags"]["searches"].append(query)
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "search_performed", "query": query,
                                     "results": len(matches), "has_results": len(matches) > 0}])

    def _cmd_timeline(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        events = sorted(
            sc.get("alerts", []) + sc.get("logs", []),
            key=lambda e: e["timestamp"]
        )
        lines = ["╔══ ATTACK TIMELINE ══╗", ""]
        prev_ts = ""
        for e in events:
            ts = e["timestamp"]
            sev = e.get("severity", "info")
            icon = {"critical":"🔴","high":"🟠","warning":"🟡","medium":"🟡","info":"🔵","low":"🔵"}.get(sev,"⚪")
            msg = e.get("title", e.get("message", ""))[:55]
            marker = "│" if ts == prev_ts else "├"
            lines.append(f"  {ts}  {icon} {marker}── {msg}")
            prev_ts = ts
        lines.append(f"\n{len(events)} events in timeline")
        state.setdefault("flags", {})["timeline_viewed"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "timeline_viewed", "event_count": len(events)}])

    def _cmd_filter(self, state, arg):
        parts = arg.split(None, 1) if arg else []
        if len(parts) < 2:
            return ActionResult(output="Usage: filter <user|ip|host|severity> <value>", new_state=state)
        field, value = parts[0].lower(), parts[1].lower()
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        logs = sc.get("logs", [])
        filtered = []
        for l in logs:
            if field == "user" and value in l.get("user", "").lower():
                filtered.append(l)
            elif field == "ip" and value in l.get("ip", "").lower():
                filtered.append(l)
            elif field == "host" and value in l.get("host", "").lower():
                filtered.append(l)
            elif field == "severity" and l.get("severity", "").lower() == value:
                filtered.append(l)
        lines = [f"Filtered logs ({field}={value}): {len(filtered)} results"]
        lines.append("─" * 80)
        for l in filtered:
            lines.append(f"  {l['timestamp']}  [{l['source']}] {l['host']}: {l['message'][:60]}")
        if not filtered:
            lines.append("  No matches.")
        state.setdefault("flags", {})["filter_used"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "filter_used", "field": field, "value": value,
                                     "results": len(filtered)}])

    def _cmd_hosts(self, state, arg):
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        hosts = set()
        for l in sc.get("logs", []):
            hosts.add(l["host"])
        lines = ["Affected Systems:"]
        for h in sorted(hosts):
            log_count = sum(1 for l in sc.get("logs", []) if l["host"] == h)
            lines.append(f"  {h:<15} ({log_count} log entries)")
        state.setdefault("flags", {})["hosts_viewed"] = True
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "hosts_viewed", "count": len(hosts)}])

    def _cmd_investigate(self, state, arg):
        if not arg:
            return ActionResult(output="Usage: investigate <ip or username>", new_state=state)
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        query = arg.strip().lower()
        logs = sc.get("logs", [])
        related = [l for l in logs if query in f"{l.get('user','')} {l.get('ip','')} {l.get('host','')}".lower()]
        if not related:
            return ActionResult(output=f"No activity found for: {arg}", new_state=state,
                                events=[{"type": "investigated", "query": query, "found": False}])
        first = related[0]["timestamp"]
        last = related[-1]["timestamp"]
        sources = list(set(l["source"] for l in related))
        hosts = list(set(l["host"] for l in related))
        lines = [
            f"Investigation: {arg}",
            f"─" * 50,
            f"  Activity period: {first} — {last}",
            f"  Total events: {len(related)}",
            f"  Log sources: {', '.join(sources)}",
            f"  Hosts involved: {', '.join(hosts)}",
            "",
            "  Key events:",
        ]
        for l in related:
            lines.append(f"    {l['timestamp']}  {l['message'][:55]}")
        state.setdefault("flags", {})["investigated"] = True
        state["flags"].setdefault("investigated_iocs", [])
        if query not in state["flags"]["investigated_iocs"]:
            state["flags"]["investigated_iocs"].append(query)
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "investigated", "query": query, "found": True,
                                     "events": len(related)}])

    def _cmd_report(self, state, arg):
        if not arg:
            return ActionResult(
                output="Usage: report <your incident findings>\n"
                       "Include: attacker IP, compromised account, attack type, severity, remediation",
                new_state=state)
        sc = SCENARIOS.get(state.get("scenario_key", ""), {})
        answer_keys = sc.get("answer_keywords", {})
        arg_lower = arg.lower()
        matched = {}
        for category, keywords in answer_keys.items():
            hits = [kw for kw in keywords if kw.lower() in arg_lower]
            if hits:
                matched[category] = hits
        score = len(matched)
        total = len(answer_keys)
        state["report_submitted"] = True
        state.setdefault("flags", {})["report_submitted"] = True
        state["flags"]["report_score"] = score
        state["flags"]["report_total"] = total
        if score >= 3:
            state["flags"]["report_correct"] = True
        lines = [
            "╔══ INCIDENT REPORT SUBMITTED ══╗",
            "",
            f"Score: {score}/{total} categories matched",
            "",
        ]
        for cat in answer_keys:
            if cat in matched:
                lines.append(f"  ✓ {cat}: {', '.join(matched[cat])}")
            else:
                lines.append(f"  ✗ {cat}: not identified")
        if score >= 3:
            lines.append(f"\n✓ Good analysis! You identified the key indicators.")
        elif score >= 1:
            lines.append(f"\n⚠ Partial — review the logs and alerts for more IOCs.")
        else:
            lines.append(f"\n✗ Try investigating more thoroughly before submitting.")
        return ActionResult(output="\n".join(lines), new_state=state,
                            events=[{"type": "report_submitted", "score": score,
                                     "total": total, "correct": score >= 3,
                                     "matched": matched}])

    def _cmd_clear(self, state, arg):
        return ActionResult(output="", new_state=state, clear=True)
