"""Active Directory Simulator (YC-031.0) — the Lab Engine plugin.

Plugs the reusable AD engines (domain / user / group / policy /
permission) into the existing Simulator contract. PowerShell-flavoured
commands, plus the ``select`` action driving the object-explorer UI —
selecting a tree node behaves exactly like running the matching
``get-*`` command, so the terminal and the explorer stay one system.

Everything is simulated: no LDAP, no real Windows, no execution.
"""

from __future__ import annotations

import shlex
from typing import Any, Callable

from app.labs.ad import (
    domains,
    engine,
    group_engine,
    permission_engine,
    policy_engine,
    user_engine,
)
from app.labs.ad.user_engine import OpResult
from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)

_HELP = """AD ADMINISTRATION CONSOLE — available commands

 DIRECTORY
  get-users                     list every user account
  get-user <sam>                one user's full properties
  get-groups                    list security groups
  get-group <name>              one group + its members
  members <group>               shorthand for get-group
  get-ous                       organizational units
  get-computers                 domain-joined computers
  get-computer <name>           one computer's properties
  get-shares                    shared folders
  get-share <name>              one share + its permissions

 ACCOUNT MANAGEMENT
  reset-password <sam> <new>    reset a password (policy enforced)
  unlock <sam>                  clear an account lockout
  enable <sam> / disable <sam>  activate / deactivate an account
  move <sam> <ou>               move a user to another OU

 GROUP MANAGEMENT
  add-member <group> <sam>      add a user to a group
  remove-member <group> <sam>   remove a user from a group

 SECURITY
  access <sam> <share>          test a user's access to a share
  grant-access <share> <group> <right>    right: read|write|full
  revoke-access <share> <group>
  kerberos <sam> [service]      visualize the Kerberos ticket flow
  policy                        password + lockout policy
  gpos                          list Group Policy Objects

 OTHER
  whoami · hostname · clear · exit · help

Names with spaces need quotes: members "Domain Admins"."""


def _fail(message: str) -> OpResult:
    return OpResult(False, message)


@register_simulator
class ADSimulator(Simulator):
    """Enterprise identity sandbox on a virtual domain."""

    key = "ad"

    #: lab slug -> domain key (data-driven; admin custom domains can be
    #: targeted by seeding a lab whose slug maps here or via content).
    SLUG_TO_DOMAIN: dict[str, str] = {
        "ad-orientation": "yusha-local",
        "ad-inactive-account": "yusha-local",
        "ad-compromised-password": "yusha-local",
        "ad-overprivileged": "yusha-local",
        "ad-least-privilege": "yusha-local",
    }

    # ------------------------------------------------------------------
    # Simulator contract
    # ------------------------------------------------------------------
    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        domain_key = "yusha-local"
        # Content override first (lets admin scenarios retarget a lab)…
        for node in (content or {}).get("filesystem", []):
            if node.get("path") == "domain" and node.get("content"):
                domain_key = str(node["content"]).strip().lower()
        # …then the slug mapping.
        if lab is not None and getattr(lab, "slug", None):
            domain_key = self.SLUG_TO_DOMAIN.get(lab.slug, domain_key)

        definition = domains.get_domain(domain_key) \
            or domains.BUILTIN_DOMAINS["yusha-local"]
        return {
            "sim": self.key,
            "domain_key": definition["key"],
            "directory": engine.build_directory(definition),
            "selected": "",
            "flags": {"commands_used": 0},
        }

    def capabilities(self) -> set[str]:
        return {CAP_TERMINAL}

    def prompt(self, state: dict[str, Any]) -> str:
        netbios = (state.get("directory", {}).get("domain", {})
                   .get("netbios") or "YUSHA")
        return f"PS {netbios}\\admin> "

    def welcome(self, state: dict[str, Any]) -> str:
        directory = state.get("directory", {})
        domain = directory.get("domain", {})
        return (
            f"╔══════════════════════════════════════════════════╗\n"
            f"║   ACTIVE DIRECTORY ADMINISTRATION — SIMULATED     ║\n"
            f"╚══════════════════════════════════════════════════╝\n"
            f"\n"
            f"Connected to domain: {domain.get('name', '?')}  "
            f"(functional level {domain.get('functional_level', '?')})\n"
            f"{domain.get('description', '')}\n"
            f"\n"
            f"  {len(directory.get('users', {}))} users · "
            f"{len(directory.get('groups', {}))} groups · "
            f"{len(directory.get('ous', {}))} OUs · "
            f"{len(directory.get('computers', {}))} computers · "
            f"{len(directory.get('shares', {}))} shares\n"
            f"\n"
            f"Click objects in the explorer, or type `help` for commands."
        )

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        directory = state.get("directory", {})
        domain = directory.get("domain", {})
        locked = sum(1 for u in directory.get("users", {}).values()
                     if u["locked"])
        disabled = sum(1 for u in directory.get("users", {}).values()
                       if not u["enabled"])
        admins = len(directory.get("groups", {})
                     .get("domain-admins", {}).get("members", []))
        return [
            {"label": "Domain", "value": domain.get("name", "—")},
            {"label": "Users", "value": str(len(directory.get("users", {})))},
            {"label": "Locked out", "value": str(locked)},
            {"label": "Disabled", "value": str(disabled)},
            {"label": "Domain Admins", "value": str(admins)},
            {"label": "Selected", "value": state.get("selected") or "—"},
        ]

    def describe_ui(self) -> dict[str, Any]:
        return {
            "title": "YUSHA\\admin — AD Administration Console (simulated)",
            "ad": True,
        }

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------
    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        state = dict(state)
        state.setdefault("flags", {})
        directory = state.get("directory") or {}

        if action.type == "select":
            return self._handle_select(state, directory, action)

        command_line = action.command.strip()
        state["flags"]["commands_used"] = \
            int(state["flags"].get("commands_used", 0)) + 1

        if not command_line:
            return ActionResult(output="", new_state=state)

        try:
            parts = shlex.split(command_line)
        except ValueError:
            return ActionResult(
                output="Parse error — check your quotes.", new_state=state)

        verb, args = parts[0].lower(), parts[1:]

        if verb == "clear":
            return ActionResult(output="", new_state=state, clear=True)
        if verb == "exit":
            return ActionResult(
                output="Use the lab navigation to leave — the session is "
                       "saved automatically.", new_state=state)

        handler = self._dispatch().get(verb)
        if handler is None:
            return ActionResult(
                output=f"'{verb}' is not recognized. Type `help` for the "
                       f"command list.", new_state=state)

        result = handler(self, directory, args, state)
        events = list(result.events)
        events.append({"type": "command_run", "verb": verb, "ok": result.ok})
        return ActionResult(output=result.message, new_state=state,
                            events=events)

    def _handle_select(self, state: dict[str, Any], directory: dict[str, Any],
                       action: Action) -> ActionResult:
        """Explorer click: ``payload = {"object": "user:mrai"}``. Renders
        the same output as the matching get-* command and records the
        selection so validators can hang off ``object_selected``."""
        ref = str(action.payload.get("object", "") or "")
        kind, _, key = ref.partition(":")
        renderers: dict[str, Callable[[], OpResult]] = {
            "user": lambda: self._cmd_get_user(directory, [key], state),
            "group": lambda: self._cmd_get_group(directory, [key], state),
            "ou": lambda: self._cmd_get_ou(directory, [key], state),
            "computer": lambda: self._cmd_get_computer(directory, [key], state),
            "share": lambda: self._cmd_get_share(directory, [key], state),
            "gpo": lambda: self._cmd_get_gpo(directory, [key], state),
            "domain": lambda: OpResult(True, self.welcome(state)),
        }
        renderer = renderers.get(kind)
        if renderer is None:
            return ActionResult(output="Unknown object.", new_state=state)
        result = renderer()
        if result.ok:
            state["selected"] = ref
        events = list(result.events)
        events.append({"type": "object_selected", "kind": kind, "key": key})
        return ActionResult(output=result.message, new_state=state,
                            events=events)

    # ------------------------------------------------------------------
    # Command implementations — thin wrappers over the engines.
    # ------------------------------------------------------------------
    def _cmd_help(self, directory, args, state) -> OpResult:
        return OpResult(True, _HELP)

    def _cmd_get_users(self, directory, args, state) -> OpResult:
        return OpResult(True, user_engine.format_user_table(directory),
                        events=[{"type": "users_viewed",
                                 "count": len(directory.get("users", {}))}])

    def _cmd_get_user(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-user <sam>")
        user = engine.find_user(directory, args[0])
        if user is None:
            return _fail(f"Get-ADUser : Cannot find an object with "
                         f"identity: '{args[0]}'.")
        return OpResult(True, user_engine.format_user(directory, user),
                        events=[{"type": "user_inspected", "sam": user["sam"],
                                 "inactive": user.get("last_logon_days", 0) >= 90,
                                 "locked": user["locked"],
                                 "privileged": "domain-admins" in user["groups"]}])

    def _cmd_get_groups(self, directory, args, state) -> OpResult:
        return OpResult(True, group_engine.format_group_table(directory),
                        events=[{"type": "groups_viewed"}])

    def _cmd_get_group(self, directory, args, state) -> OpResult:
        if not args:
            return _fail('Usage: get-group <name>   (quote names with '
                         'spaces: get-group "Domain Admins")')
        group = engine.find_group(directory, args[0])
        if group is None:
            return _fail(f"Get-ADGroup : Cannot find an object with "
                         f"identity: '{args[0]}'.")
        return OpResult(True, group_engine.format_group(directory, group),
                        events=[{"type": "group_members_viewed",
                                 "group": group["slug"],
                                 "member_count": len(group["members"])}])

    def _cmd_get_ous(self, directory, args, state) -> OpResult:
        rows = ["ORGANIZATIONAL UNIT        USERS  COMPUTERS", "─" * 45]
        for slug in sorted(directory.get("ous", {})):
            ou = directory["ous"][slug]
            rows.append(
                f"{ou['name']:<26} {len(engine.users_in_ou(directory, slug)):>5}"
                f"  {len(engine.computers_in_ou(directory, slug)):>9}")
        rows += ["", "Use `move <sam> <ou>` to move a user between OUs."]
        return OpResult(True, "\n".join(rows),
                        events=[{"type": "ous_viewed"}])

    def _cmd_get_ou(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-ou <name>")
        ou = engine.find_ou(directory, args[0])
        if ou is None:
            return _fail(f"Cannot find OU '{args[0]}'.")
        users = engine.users_in_ou(directory, ou["slug"])
        computers = engine.computers_in_ou(directory, ou["slug"])
        body = "\n".join(f"  · {u['sam']} ({u['display']})" for u in users)
        comp = "\n".join(f"  · {c['name']} [{c['os']}]" for c in computers)
        return OpResult(
            True,
            f"OU          : {ou['name']}\n"
            f"Description : {ou.get('description') or '—'}\n"
            f"Users       :\n{body or '  (none)'}\n"
            f"Computers   :\n{comp or '  (none)'}",
            events=[{"type": "ou_inspected", "ou": ou["slug"]}])

    def _cmd_get_computers(self, directory, args, state) -> OpResult:
        rows = ["NAME     OS                    IP           ROLE", "─" * 52]
        for key in sorted(directory.get("computers", {})):
            comp = directory["computers"][key]
            role = "DOMAIN CONTROLLER" if comp["is_dc"] else "member"
            rows.append(f"{comp['name']:<8} {comp['os']:<21} "
                        f"{comp['ip']:<12} {role}")
        return OpResult(True, "\n".join(rows),
                        events=[{"type": "computers_viewed"}])

    def _cmd_get_computer(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-computer <name>")
        comp = engine.find_computer(directory, args[0])
        if comp is None:
            return _fail(f"Cannot find computer '{args[0]}'.")
        ou = directory.get("ous", {}).get(comp.get("ou", ""), {})
        role = ("Domain Controller — runs AD DS, DNS and the KDC"
                if comp["is_dc"] else "Member computer")
        return OpResult(
            True,
            f"Computer    : {comp['name']}\n"
            f"OS          : {comp['os']}\n"
            f"IP address  : {comp['ip']}\n"
            f"OU          : {ou.get('name', '—')}\n"
            f"Role        : {role}\n"
            f"Description : {comp.get('description') or '—'}",
            events=[{"type": "computer_inspected", "name": comp["name"],
                     "is_dc": comp["is_dc"]}])

    def _cmd_get_shares(self, directory, args, state) -> OpResult:
        return OpResult(True,
                        permission_engine.format_share_table(directory),
                        events=[{"type": "shares_viewed"}])

    def _cmd_get_share(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-share <name>")
        share = engine.find_share(directory, args[0])
        if share is None:
            return _fail(f"Cannot find shared folder '{args[0]}'.")
        return OpResult(True,
                        permission_engine.format_share(directory, share),
                        events=[{"type": "share_inspected",
                                 "share": share["slug"]}])

    def _cmd_get_gpo(self, directory, args, state) -> OpResult:
        if not args:
            return self._cmd_gpos(directory, args, state)
        gpo = engine.find_gpo(directory, args[0])
        if gpo is None:
            return _fail(f"Cannot find GPO '{args[0]}'.")
        return OpResult(True, policy_engine.format_gpo(gpo),
                        events=[{"type": "gpo_viewed", "gpo": gpo["slug"]}])

    def _cmd_gpos(self, directory, args, state) -> OpResult:
        return OpResult(True, policy_engine.list_gpos(directory),
                        events=[{"type": "gpo_viewed", "gpo": "*"}])

    def _cmd_policy(self, directory, args, state) -> OpResult:
        return OpResult(True,
                        policy_engine.format_password_policy(directory),
                        events=[{"type": "policy_viewed"}])

    def _cmd_reset_password(self, directory, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: reset-password <sam> <new-password>")
        return user_engine.reset_password(directory, args[0], args[1])

    def _cmd_unlock(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: unlock <sam>")
        return user_engine.unlock_account(directory, args[0])

    def _cmd_enable(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: enable <sam>")
        return user_engine.set_enabled(directory, args[0], True)

    def _cmd_disable(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: disable <sam>")
        return user_engine.set_enabled(directory, args[0], False)

    def _cmd_move(self, directory, args, state) -> OpResult:
        if len(args) < 2:
            return _fail('Usage: move <sam> <ou>   e.g. move kshrestha '
                         '"Disabled Accounts"')
        return user_engine.move_user(directory, args[0], args[1])

    def _cmd_add_member(self, directory, args, state) -> OpResult:
        if len(args) < 2:
            return _fail('Usage: add-member <group> <sam>')
        return group_engine.add_member(directory, args[0], args[1])

    def _cmd_remove_member(self, directory, args, state) -> OpResult:
        if len(args) < 2:
            return _fail('Usage: remove-member <group> <sam>')
        return group_engine.remove_member(directory, args[0], args[1])

    def _cmd_access(self, directory, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: access <sam> <share>")
        return permission_engine.check_access(directory, args[0], args[1])

    def _cmd_grant_access(self, directory, args, state) -> OpResult:
        if len(args) < 3:
            return _fail("Usage: grant-access <share> <group> <read|write|full>")
        return permission_engine.grant_access(directory, args[0], args[1],
                                              args[2])

    def _cmd_revoke_access(self, directory, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: revoke-access <share> <group>")
        return permission_engine.revoke_access(directory, args[0], args[1])

    def _cmd_kerberos(self, directory, args, state) -> OpResult:
        if not args:
            return _fail("Usage: kerberos <sam> [service]")
        service = args[1] if len(args) > 1 else ""
        return permission_engine.kerberos_flow(directory, args[0], service)

    def _cmd_whoami(self, directory, args, state) -> OpResult:
        netbios = directory.get("domain", {}).get("netbios", "YUSHA")
        return OpResult(True, f"{netbios.lower()}\\admin "
                              f"(simulated administrator session)")

    def _cmd_hostname(self, directory, args, state) -> OpResult:
        dc = next((c for c in directory.get("computers", {}).values()
                   if c.get("is_dc")), None)
        return OpResult(True, dc["name"] if dc else "DC-01")

    # ------------------------------------------------------------------
    # Dispatch — data-driven so future labs can extend single commands.
    # ------------------------------------------------------------------
    def _dispatch(self) -> dict[str, Callable]:
        return {
            "help": ADSimulator._cmd_help,
            "get-users": ADSimulator._cmd_get_users,
            "get-user": ADSimulator._cmd_get_user,
            "get-groups": ADSimulator._cmd_get_groups,
            "get-group": ADSimulator._cmd_get_group,
            "members": ADSimulator._cmd_get_group,
            "get-ous": ADSimulator._cmd_get_ous,
            "get-ou": ADSimulator._cmd_get_ou,
            "get-computers": ADSimulator._cmd_get_computers,
            "get-computer": ADSimulator._cmd_get_computer,
            "get-shares": ADSimulator._cmd_get_shares,
            "get-share": ADSimulator._cmd_get_share,
            "get-gpo": ADSimulator._cmd_get_gpo,
            "gpos": ADSimulator._cmd_gpos,
            "gpo": ADSimulator._cmd_get_gpo,
            "policy": ADSimulator._cmd_policy,
            "reset-password": ADSimulator._cmd_reset_password,
            "unlock": ADSimulator._cmd_unlock,
            "enable": ADSimulator._cmd_enable,
            "disable": ADSimulator._cmd_disable,
            "move": ADSimulator._cmd_move,
            "add-member": ADSimulator._cmd_add_member,
            "remove-member": ADSimulator._cmd_remove_member,
            "access": ADSimulator._cmd_access,
            "grant-access": ADSimulator._cmd_grant_access,
            "revoke-access": ADSimulator._cmd_revoke_access,
            "kerberos": ADSimulator._cmd_kerberos,
            "whoami": ADSimulator._cmd_whoami,
            "hostname": ADSimulator._cmd_hostname,
        }
