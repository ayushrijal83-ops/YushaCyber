"""Cloud Simulator (YC-032.0) — the Lab Engine plugin.

Plugs the reusable cloud engines (cloud / IAM / storage / networking /
policy) into the existing Simulator contract. CLI-flavoured commands,
plus the ``select`` action driving the management-console UI — clicking
a resource behaves exactly like running the matching get/list command,
so the console and the terminal stay one system.

Everything is simulated: no AWS, no Azure, no GCP, no execution.
"""

from __future__ import annotations

import shlex
from typing import Any, Callable

from app.labs.cloud import (
    accounts,
    engine,
    iam_engine,
    network_engine,
    policy_engine,
    storage_engine,
)
from app.labs.cloud.engine import OpResult
from app.labs.registry import register_simulator
from app.labs.simulator_base import (
    CAP_TERMINAL,
    Action,
    ActionResult,
    Simulator,
)

_HELP = """YUSHACLOUD CLI — available commands

 ACCOUNT
  overview                       account dashboard
  audit                          security posture scan
  risk <topic>                   explain a misconfiguration risk
  password-policy                show the account password policy
  set-password-policy <k> <v>    min-length N · require-mfa on/off

 IAM
  list-users / get-user <name>   identities and their properties
  list-roles / get-role <name>   roles and their permissions
  create-user <name> <role>      new identity with one role
  attach-role <user> <role>      grant a role
  detach-role <user> <role>      remove a role
  disable-user / enable-user     block or restore sign-in
  deactivate-key <user>          kill an API access key
  simulate <user> <svc:action>   evaluate a permission, with reasoning

 STORAGE
  list-buckets / get-bucket <b>  buckets and their policies
  list-objects <bucket>          what a bucket holds
  make-private / make-public <b> flip the bucket access policy
  encrypt-bucket <bucket>        enable at-rest encryption
  enable-versioning <bucket>     keep recoverable object versions

 NETWORK
  network                        VPCs, subnets, gateways
  list-sgs / get-sg <name>       security groups and rules
  revoke-ingress <sg> <port> [cidr]   remove a firewall rule
  allow-ingress <sg> <port> <cidr>    add a firewall rule

 COMPUTE & DATA
  list-vms / get-vm <name>       virtual machines
  list-lbs                       load balancers
  list-dbs / get-db <name>       databases
  make-db-private <db>           disable a public DB endpoint

 OTHER
  whoami · region · clear · exit · help"""


def _fail(message: str) -> OpResult:
    return OpResult(False, message)


@register_simulator
class CloudSimulator(Simulator):
    """Cloud security sandbox on a virtual provider account."""

    key = "cloud"

    #: lab slug -> account key (data-driven; admin scenarios can retarget
    #: a lab via a content node path="scenario").
    SLUG_TO_ACCOUNT: dict[str, str] = {
        "cloud-orientation": "yushacloud-prod",
        "cloud-public-bucket": "yushacloud-prod",
        "cloud-iam-overprivileged": "yushacloud-prod",
        "cloud-open-ssh": "yushacloud-prod",
        "cloud-exposed-database": "yushacloud-prod",
        "cloud-hardening": "yushacloud-prod",
    }

    # ------------------------------------------------------------------
    # Simulator contract
    # ------------------------------------------------------------------
    def bootstrap(self, lab: Any, content: dict[str, Any]) -> dict[str, Any]:
        account_key = "yushacloud-prod"
        for node in (content or {}).get("filesystem", []):
            if node.get("path") == "scenario" and node.get("content"):
                account_key = str(node["content"]).strip().lower()
        if lab is not None and getattr(lab, "slug", None):
            account_key = self.SLUG_TO_ACCOUNT.get(lab.slug, account_key)

        definition = accounts.get_account(account_key) \
            or accounts.BUILTIN_ACCOUNTS["yushacloud-prod"]
        return {
            "sim": self.key,
            "account_key": definition["key"],
            "deployment": engine.build_deployment(definition),
            "selected": "",
            "flags": {"commands_used": 0},
        }

    def capabilities(self) -> set[str]:
        return {CAP_TERMINAL}

    def prompt(self, state: dict[str, Any]) -> str:
        region = (state.get("deployment", {}).get("account", {})
                  .get("region") or "np-ktm-1")
        return f"yc:{region} admin$ "

    def welcome(self, state: dict[str, Any]) -> str:
        deployment = state.get("deployment", {})
        return engine.format_overview(deployment) + \
            "\n\nClick resources in the console tree, or type `help`."

    def status_panel(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        deployment = state.get("deployment", {})
        findings = engine.audit_findings(deployment)
        open_count = sum(len(v) for v in findings.values())
        public_buckets = sum(
            1 for b in deployment.get("buckets", {}).values()
            if b["public"])
        return [
            {"label": "Account",
             "value": deployment.get("account", {}).get("name", "—")},
            {"label": "Region",
             "value": deployment.get("account", {}).get("region", "—")},
            {"label": "IAM users",
             "value": str(len(deployment.get("users", {})))},
            {"label": "Public buckets", "value": str(public_buckets)},
            {"label": "Open findings", "value": str(open_count)},
            {"label": "Selected", "value": state.get("selected") or "—"},
        ]

    def describe_ui(self) -> dict[str, Any]:
        return {
            "title": "YushaCloud Management Console (simulated)",
            "cloud": True,
        }

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------
    def handle(self, state: dict[str, Any], action: Action) -> ActionResult:
        state = dict(state)
        state.setdefault("flags", {})
        deployment = state.get("deployment") or {}

        if action.type == "select":
            return self._handle_select(state, deployment, action)

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

        result = handler(self, deployment, args, state)
        events = list(result.events)
        events.append({"type": "command_run", "verb": verb, "ok": result.ok})
        return ActionResult(output=result.message, new_state=state,
                            events=events)

    def _handle_select(self, state: dict[str, Any],
                       deployment: dict[str, Any],
                       action: Action) -> ActionResult:
        """Console click: ``payload = {"object": "bucket:customer-backups"}``.
        Renders the same output as the matching command and records the
        selection."""
        ref = str(action.payload.get("object", "") or "")
        kind, _, key = ref.partition(":")
        renderers: dict[str, Callable[[], OpResult]] = {
            "user": lambda: self._cmd_get_user(deployment, [key], state),
            "role": lambda: self._cmd_get_role(deployment, [key], state),
            "bucket": lambda: self._cmd_get_bucket(deployment, [key], state),
            "vpc": lambda: self._cmd_network(deployment, [], state),
            "subnet": lambda: self._cmd_network(deployment, [], state),
            "sg": lambda: self._cmd_get_sg(deployment, [key], state),
            "vm": lambda: self._cmd_get_vm(deployment, [key], state),
            "lb": lambda: self._cmd_list_lbs(deployment, [], state),
            "db": lambda: self._cmd_get_db(deployment, [key], state),
            "policy": lambda: self._cmd_password_policy(
                deployment, [], state),
            "account": lambda: OpResult(
                True, engine.format_overview(deployment),
                events=[{"type": "overview_viewed"}]),
        }
        renderer = renderers.get(kind)
        if renderer is None:
            return ActionResult(output="Unknown resource.", new_state=state)
        result = renderer()
        if result.ok:
            state["selected"] = ref
        events = list(result.events)
        events.append({"type": "resource_selected", "kind": kind,
                       "key": key})
        return ActionResult(output=result.message, new_state=state,
                            events=events)

    # ------------------------------------------------------------------
    # Command implementations — thin wrappers over the engines.
    # ------------------------------------------------------------------
    def _cmd_help(self, deployment, args, state) -> OpResult:
        return OpResult(True, _HELP)

    def _cmd_overview(self, deployment, args, state) -> OpResult:
        return OpResult(True, engine.format_overview(deployment),
                        events=[{"type": "overview_viewed"}])

    def _cmd_audit(self, deployment, args, state) -> OpResult:
        findings = engine.audit_findings(deployment)
        counts = {key: len(value) for key, value in findings.items()}
        return OpResult(
            True, engine.format_audit(deployment),
            events=[{"type": "audit_run",
                     "total": sum(counts.values()),
                     "hardening_findings": counts["weak_policy"]
                     + counts["unused_admins"],
                     **counts}])

    def _cmd_risk(self, deployment, args, state) -> OpResult:
        if not args:
            return policy_engine.format_risk("")
        return policy_engine.format_risk(args[0])

    def _cmd_whoami(self, deployment, args, state) -> OpResult:
        account = deployment.get("account", {})
        return OpResult(True, f"admin @ {account.get('name', '?')} "
                              f"({account.get('account_id', '?')})")

    def _cmd_region(self, deployment, args, state) -> OpResult:
        return OpResult(
            True, deployment.get("account", {}).get("region", "?"))

    # ---- IAM ---------------------------------------------------------
    def _cmd_list_users(self, deployment, args, state) -> OpResult:
        return OpResult(True, iam_engine.format_user_table(deployment),
                        events=[{"type": "iam_users_viewed",
                                 "count": len(deployment.get("users", {}))}])

    def _cmd_get_user(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-user <username>")
        user = engine.find_user(deployment, args[0])
        if user is None:
            return _fail(f"Unknown user '{args[0]}'. See `list-users`.")
        return OpResult(True, iam_engine.format_user(deployment, user),
                        events=iam_engine.user_events(deployment, user))

    def _cmd_list_roles(self, deployment, args, state) -> OpResult:
        return OpResult(True, iam_engine.format_role_table(deployment),
                        events=[{"type": "iam_roles_viewed"}])

    def _cmd_get_role(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-role <role>")
        role = engine.find_role(deployment, args[0])
        if role is None:
            return _fail(f"Unknown role '{args[0]}'. See `list-roles`.")
        return OpResult(True, iam_engine.format_role(deployment, role),
                        events=[{"type": "iam_role_inspected",
                                 "role": role["slug"],
                                 "admin": "*:*" in role["permissions"]}])

    def _cmd_create_user(self, deployment, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: create-user <name> <role>")
        return iam_engine.create_user(deployment, args[0], args[1])

    def _cmd_attach_role(self, deployment, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: attach-role <user> <role>")
        return iam_engine.attach_role(deployment, args[0], args[1])

    def _cmd_detach_role(self, deployment, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: detach-role <user> <role>")
        return iam_engine.detach_role(deployment, args[0], args[1])

    def _cmd_disable_user(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: disable-user <username>")
        return iam_engine.set_user_enabled(deployment, args[0], False)

    def _cmd_enable_user(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: enable-user <username>")
        return iam_engine.set_user_enabled(deployment, args[0], True)

    def _cmd_deactivate_key(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: deactivate-key <username>")
        return iam_engine.deactivate_access_key(deployment, args[0])

    def _cmd_simulate(self, deployment, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: simulate <user> <service:action>")
        return iam_engine.simulate_permission(deployment, args[0], args[1])

    # ---- Storage -----------------------------------------------------
    def _cmd_list_buckets(self, deployment, args, state) -> OpResult:
        return OpResult(
            True, storage_engine.format_bucket_table(deployment),
            events=[{"type": "buckets_viewed",
                     "count": len(deployment.get("buckets", {}))}])

    def _cmd_get_bucket(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-bucket <bucket>")
        bucket = engine.find_bucket(deployment, args[0])
        if bucket is None:
            return _fail(f"Unknown bucket '{args[0]}'. See `list-buckets`.")
        return OpResult(True, storage_engine.format_bucket(bucket),
                        events=storage_engine.bucket_events(bucket))

    def _cmd_list_objects(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: list-objects <bucket>")
        bucket = engine.find_bucket(deployment, args[0])
        if bucket is None:
            return _fail(f"Unknown bucket '{args[0]}'.")
        sensitive = sum(1 for o in bucket["objects"] if o.get("sensitive"))
        return OpResult(True, storage_engine.format_objects(bucket),
                        events=[{"type": "objects_viewed",
                                 "bucket": bucket["slug"],
                                 "sensitive_exposed": bool(sensitive)
                                 and bucket["public"]}])

    def _cmd_make_private(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: make-private <bucket>")
        return storage_engine.set_public(deployment, args[0], False)

    def _cmd_make_public(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: make-public <bucket>")
        return storage_engine.set_public(deployment, args[0], True)

    def _cmd_encrypt_bucket(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: encrypt-bucket <bucket>")
        return storage_engine.enable_encryption(deployment, args[0])

    def _cmd_enable_versioning(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: enable-versioning <bucket>")
        return storage_engine.enable_versioning(deployment, args[0])

    # ---- Network -----------------------------------------------------
    def _cmd_network(self, deployment, args, state) -> OpResult:
        return OpResult(True, network_engine.format_network(deployment),
                        events=[{"type": "network_viewed"}])

    def _cmd_list_sgs(self, deployment, args, state) -> OpResult:
        return OpResult(True, network_engine.format_sg_table(deployment),
                        events=[{"type": "sgs_viewed"}])

    def _cmd_get_sg(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-sg <group>")
        sg = engine.find_sg(deployment, args[0])
        if sg is None:
            return _fail(f"Unknown security group '{args[0]}'. See "
                         f"`list-sgs`.")
        return OpResult(True, network_engine.format_sg(sg),
                        events=network_engine.sg_events(sg))

    def _cmd_revoke_ingress(self, deployment, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: revoke-ingress <sg> <port> [cidr]")
        try:
            port = int(args[1])
        except ValueError:
            return _fail("Port must be a number.")
        cidr = args[2] if len(args) > 2 else "0.0.0.0/0"
        return network_engine.revoke_ingress(deployment, args[0], port, cidr)

    def _cmd_allow_ingress(self, deployment, args, state) -> OpResult:
        if len(args) < 3:
            return _fail("Usage: allow-ingress <sg> <port> <cidr>")
        try:
            port = int(args[1])
        except ValueError:
            return _fail("Port must be a number.")
        return network_engine.allow_ingress(deployment, args[0], port,
                                            args[2])

    # ---- Compute & data ----------------------------------------------
    def _cmd_list_vms(self, deployment, args, state) -> OpResult:
        return OpResult(True, engine.format_vm_table(deployment),
                        events=[{"type": "vms_viewed"}])

    def _cmd_get_vm(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-vm <name>")
        vm = engine.find_vm(deployment, args[0])
        if vm is None:
            return _fail(f"Unknown VM '{args[0]}'. See `list-vms`.")
        return OpResult(True, engine.format_vm(deployment, vm),
                        events=[{"type": "vm_inspected", "vm": vm["slug"],
                                 "public": bool(vm["public_ip"])}])

    def _cmd_list_lbs(self, deployment, args, state) -> OpResult:
        return OpResult(True, engine.format_lb_table(deployment),
                        events=[{"type": "lbs_viewed"}])

    def _cmd_list_dbs(self, deployment, args, state) -> OpResult:
        return OpResult(True, network_engine.format_db_table(deployment),
                        events=[{"type": "dbs_viewed"}])

    def _cmd_get_db(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: get-db <name>")
        database = engine.find_db(deployment, args[0])
        if database is None:
            return _fail(f"Unknown database '{args[0]}'. See `list-dbs`.")
        return OpResult(True,
                        network_engine.format_db(deployment, database),
                        events=network_engine.db_events(deployment,
                                                        database))

    def _cmd_make_db_private(self, deployment, args, state) -> OpResult:
        if not args:
            return _fail("Usage: make-db-private <db>")
        return network_engine.set_db_public(deployment, args[0], False)

    # ---- Policy ------------------------------------------------------
    def _cmd_password_policy(self, deployment, args, state) -> OpResult:
        return OpResult(
            True,
            policy_engine.format_password_policy(
                deployment.get("password_policy", {})),
            events=[{"type": "policy_viewed",
                     "strong": policy_engine.policy_strong(
                         deployment.get("password_policy", {}))}])

    def _cmd_set_password_policy(self, deployment, args, state) -> OpResult:
        if len(args) < 2:
            return _fail("Usage: set-password-policy <setting> <value>\n"
                         "e.g. set-password-policy min-length 14")
        return policy_engine.update_policy(
            deployment.get("password_policy", {}), args[0], args[1])

    # ------------------------------------------------------------------
    def _dispatch(self) -> dict[str, Callable]:
        return {
            "help": CloudSimulator._cmd_help,
            "overview": CloudSimulator._cmd_overview,
            "dashboard": CloudSimulator._cmd_overview,
            "audit": CloudSimulator._cmd_audit,
            "risk": CloudSimulator._cmd_risk,
            "whoami": CloudSimulator._cmd_whoami,
            "region": CloudSimulator._cmd_region,
            "list-users": CloudSimulator._cmd_list_users,
            "get-user": CloudSimulator._cmd_get_user,
            "list-roles": CloudSimulator._cmd_list_roles,
            "get-role": CloudSimulator._cmd_get_role,
            "create-user": CloudSimulator._cmd_create_user,
            "attach-role": CloudSimulator._cmd_attach_role,
            "detach-role": CloudSimulator._cmd_detach_role,
            "disable-user": CloudSimulator._cmd_disable_user,
            "enable-user": CloudSimulator._cmd_enable_user,
            "deactivate-key": CloudSimulator._cmd_deactivate_key,
            "simulate": CloudSimulator._cmd_simulate,
            "list-buckets": CloudSimulator._cmd_list_buckets,
            "get-bucket": CloudSimulator._cmd_get_bucket,
            "list-objects": CloudSimulator._cmd_list_objects,
            "make-private": CloudSimulator._cmd_make_private,
            "make-public": CloudSimulator._cmd_make_public,
            "encrypt-bucket": CloudSimulator._cmd_encrypt_bucket,
            "enable-versioning": CloudSimulator._cmd_enable_versioning,
            "network": CloudSimulator._cmd_network,
            "list-vpcs": CloudSimulator._cmd_network,
            "list-sgs": CloudSimulator._cmd_list_sgs,
            "get-sg": CloudSimulator._cmd_get_sg,
            "revoke-ingress": CloudSimulator._cmd_revoke_ingress,
            "allow-ingress": CloudSimulator._cmd_allow_ingress,
            "list-vms": CloudSimulator._cmd_list_vms,
            "get-vm": CloudSimulator._cmd_get_vm,
            "list-lbs": CloudSimulator._cmd_list_lbs,
            "list-dbs": CloudSimulator._cmd_list_dbs,
            "get-db": CloudSimulator._cmd_get_db,
            "make-db-private": CloudSimulator._cmd_make_db_private,
            "password-policy": CloudSimulator._cmd_password_policy,
            "set-password-policy":
                CloudSimulator._cmd_set_password_policy,
        }
