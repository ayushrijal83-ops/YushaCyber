# Network Reconnaissance Mission (YC-034.8)

## Purpose

Teaches structured reconnaissance methodology — discover hosts, enumerate
ports, identify services and versions, compare attack surfaces, prioritize
findings, and reach an evidence-based conclusion — rather than memorizing
individual Nmap flags. The mission frames the exercise as an authorized
engagement against a fictional training network; the student does not know
which host is the primary target in advance and must discover it through
reconnaissance, not a hardcoded choice.

Workflow taught: **Discover → Enumerate → Identify → Analyze → Prioritize →
Document**.

This mission adds no new engine — it is entirely a content pack (`app/core/
missions/mission_loader.py`) plus two small, generic extensions to the
existing terminal/validator that other networking missions can reuse too.

## Simulated network

Reuses `VirtualNetwork`/`VirtualHost` from YC-034.5–034.7 (`app/core/
terminal/network.py`) — no second network model. This mission's own
`"network"` config (declarative, like every other mission) defines:

| IP | Host | Notable ports |
|---|---|---|
| 10.10.10.1 | gateway | — |
| 10.10.10.10 | web-server | 22 ssh, 80 http, 443 https |
| 10.10.10.20 | student-machine | (the student's own host) |
| 10.10.10.30 | file-server | 21 ftp, 22 ssh, 445 microsoft-ds |
| 10.10.10.40 | training-server | 22 ssh, 3306 mysql, 8080 http |
| 10.10.10.53 | dns-server | 53/udp dns |

`training-server` is the intended primary target: it's the only host mixing
three genuinely different service categories (remote admin, database, web),
which is what makes it the "right answer" by evidence rather than by being
flagged specially anywhere in code.

## Nmap changes

Extends the existing `nmap` command (`app/core/terminal/commands.py`) and
`VirtualNetwork` (`app/core/terminal/network.py`) — no second Nmap engine.

- **New: `nmap -sn <cidr>`** — host discovery. `VirtualNetwork.discover(cidr)`
  parses the CIDR with the Python standard library `ipaddress` module (pure
  arithmetic — no socket, no ARP, no ICMP) and returns which known virtual
  hosts fall inside that range and whether each is "up" (`reachable` and not
  `blocks_icmp`, consistent with `-Pn`'s existing meaning from YC-034.7).
  `format_discovery()` renders it exactly like real `nmap -sn` output.
- All other flags (`-p`, `-p-`, `-sV`, `-sT`, `-sU`, `-O`, `-Pn`) are the
  existing YC-034.7 implementation, untouched.

## Findings — no new persistence model

The ticket explicitly asks to check for reuse before building a findings
model. The existing virtual filesystem (`VirtualFS`, already read/write/
redirect-capable since YC-034.4) already **is** a general-purpose notes
mechanism once you look at it that way: a `recon/` workspace directory is
seeded in this mission's `"filesystem"` config, and the student builds up a
plain-text findings file with `echo "..." > recon/findings.txt` (and `>>` to
append conclusions later) — the same mechanism already exercised by Bash
Fundamentals and Linux Permissions. Objectives validate its content with the
existing `file_contains` validator type.

No `ReconFinding` model, no new table, no new in-memory tracking structure.
If a future mission needs genuinely *structured* findings (not just a text
file), that's the point to introduce a model — not speculatively here.

## Validation changes

No new validator type. Two additions, both to the existing engine in
`app/core/missions/mission_validator.py`:

1. **`match` may be a list of alternatives**, not just one string, for the
   `command`, `output_contains`, and `file_contains` types. This is the
   direct answer to the ticket's "don't validate only one exact command —
   validate the meaning of the result": an objective like "investigate one
   of the discovered servers" now accepts any of several genuinely-correct
   commands (`{"type": "command", "match": ["nmap 10.10.10.10", "nmap
   10.10.10.30", "nmap 10.10.10.40"]}`) instead of forcing one specific host.
   Fully backward compatible — existing missions all pass a plain string,
   which behaves exactly as before.
2. Objectives still validate against *output that only appears once the
   right scan actually ran* (e.g. `"3306/tcp open mysql"`), not just command
   text — the same "state, not just text" principle used throughout the
   0.34.x mission series where it matters.

## CyberMentor / Context Engine

Two small, generic additions to `MissionRunner` (`app/core/missions/
mission_runner.py`), useful to any mission, not just this one:

- `ai_context()["last_output"]` — the most recent command's output, tracked
  alongside the existing `last_command`.
- `ai_context()["scanned_targets"]` — IPv4 addresses seen in `nmap` commands
  so far, derived from the existing `shell.history` (no new tracking state).

Both are additive; no change to how any other mission's context is built.
Deliberately **not** added: a recon-specific "findings" field baked into the
shared `ai_context()` — that would couple a generic function to one
mission's file layout. The mentor can already see the student's own notes
whenever they `cat recon/findings.txt`, which shows up via `last_output`.

## Security isolation

Structurally, not just behaviorally: `network.py` has zero imports of
`socket`, `subprocess`, `requests`, `os`, or any other networking-capable
module — verified by an AST-walking test, not a substring search (a naive
`"socket" not in source` check false-positives on this very file's own
docstring, which explains that it avoids one). `ipaddress` is the only
network-adjacent import, and it does no I/O — it's CIDR math only.

## Achievement

"Recon Scout" was evaluated and **not** added as a database row: the
existing achievement metric calculator (`app/achievement/services.py`)
doesn't yet track "missions completed" as a condition it can evaluate, so a
new achievement row would simply never unlock. The existing generic
mission-completion achievement check still runs (unchanged, reused from
YC-034.3) and will pick up a real "Recon Scout" achievement automatically
once that metric exists.

## Findings panel (UI)

Not built. The ticket makes it explicitly optional and conditional on clean
integration; a live structured panel needs structured backing data, and this
design deliberately keeps findings as free-form workspace text (see above)
rather than adding a new persistence layer to feed one panel.
