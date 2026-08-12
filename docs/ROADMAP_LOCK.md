# YushaCyber Curriculum — Locked Specification (YC-036.2)

`ROADMAP_VERSION = "1.0"` (`app/roadmap/services.py`)

This document is the **authoritative roadmap specification**. It locks the
curriculum's *architecture* — its tracks, module order, lesson order, and
progression rules — as they exist today in the live database
(`instance/yushacyber.db`, audited 2026-08-10). It does **not** lock lesson
*content*: explanations, examples, exercises, labs, and quizzes may keep
improving without this document changing, per Rule 10 below.

Everything in this document is traceable to real code and real database
rows. Nothing here was invented to match an idealized structure — where the
live curriculum doesn't yet cover a target topic, it is listed under
**Future Curriculum**, not silently added.

---

## Mission

YushaCyber teaches practical cybersecurity through a structured
knowledge → practice loop: a lesson explains a concept, an interactive lab
or terminal mission lets the student exercise it against a safe simulated
target, and XP/progress tracking makes the learning visible. The platform
currently spans four active learning categories — **Beginner**,
**Intermediate**, **Red Team**, and **AI Security** — backed by 79
interactive labs and 16 terminal missions (see **Lab Mapping** /
**Mission Mapping** below).

## Target Student

Someone starting close to zero (the Beginner category assumes no prior
Linux, networking, or programming background) who wants a guided path from
"how a computer and a network work" through to offensive security
technique and, at the frontier, AI/LLM security. The roadmap does not
assume a CS degree or prior IT job experience — Principle 1 below
(progressive difficulty) exists specifically so a true beginner isn't
handed `nmap` before they've seen a terminal.

## Learning Philosophy

```
LESSON  →  EXAMPLE  →  KNOWLEDGE CHECK  →  INTERACTIVE LAB  →  MISSION  →  XP  →  PROGRESS
```

In today's implementation this loop is **partially wired**:

- **Lesson** — a `Lesson` row rendered from a Markdown file (`content_path`).
- **Knowledge Check** — a per-module `Quiz` (32 exist, one per module).
- **Interactive Lab / Mission** — `app/labs/` (79 labs) and the terminal
  mission engine (`app/core/missions/mission_loader.py`, 16 missions) are
  both real and reachable. As of YC-036.2, no lesson linked to either
  (verified: zero `url_for('labs...`, `missions...` references anywhere
  in `app/templates/roadmap/` or `app/content/`) — the **Lab Mapping**
  and **Mission Mapping** sections below were purely documentation, a
  foundation for wiring real links in a future ticket. YC-036.4, YC-036.5,
  and YC-036.6 are that ticket, for three modules so far: every
  `linux-fundamentals` lesson links to the free-practice terminal, and
  its `hands-on-practice` additionally links to the real `linux-basics`
  terminal mission; `computer-networking`'s `introduction` and
  `hands-on-practice` link to the real `networking-fundamentals` terminal
  mission (no free-practice terminal link there — see "Content Status —
  Computer Networking" below for why); all three `web-fundamentals`
  lessons link to the real `web-fundamentals` terminal mission (also no
  free-practice link — see "Content Status — Web Fundamentals" below).
  YC-036.4/.5 linked missions only; YC-036.6 additionally links two
  `web-fundamentals` lessons to real interactive labs
  (`websec-http`, `websec-cookies`) — the first lab links wired from any
  lesson. Every other module's lessons still have no lab/mission link —
  this remains a real gap for whoever picks up the next module.
- **XP / Progress** — fully real: `award_xp()`, `UserLessonProgress`,
  `UserModuleProgress`, level-up, all wired and tested by manual
  verification below.

---

## Curriculum Tracks — locked structure (what's live today)

The **locked hierarchy** is exactly what's in the database: 4 active
`RoadmapCategory` rows, each with 8 `RoadmapModule` rows (`display_order`
1–8), each module with exactly 3 `Lesson` rows (`display_order` 1–3:
*Introduction* → *Core Concepts* → *Hands-on Practice*).

| # | Category (`display_order`) | Difficulty | Modules | Lessons | Total XP |
|---|---|---|---|---|---|
| 1 | **Beginner** | beginner | 8 | 24 | 1,400 |
| 2 | **Intermediate** | intermediate | 8 | 24 | 1,400 |
| 3 | **Red Team** | advanced | 8 | 24 | 1,400 |
| 4 | **AI Security** | advanced | 8 | 24 | 1,400 |
| — | Security Operations Center *(orphan, see Known Issues)* | — | 0 | 0 | 0 |

**32 modules / 96 lessons / 5,600 lesson+module XP** across the 4 active
categories. Every module additionally awards `xp_reward=175` once on
completion (already included above), gated by `bonus_awarded`.

A category's categories/module ordering is the only sequencing the schema
has — there is **no** `prerequisite_id` column anywhere in the roadmap
schema (see **Prerequisites**).

---

## Module Order (exact, `display_order` ascending within category)

### Beginner (category id 1)
1. `linux-fundamentals` — Linux Fundamentals
2. `computer-networking` — Computer Networking
3. `python-programming` — Python Programming
4. `web-fundamentals` — Web Fundamentals
5. `git-github` — Git & GitHub
6. `operating-systems` — Operating Systems
7. `cryptography-basics` — Cryptography Basics
8. `virtualization` — Virtualization

### Intermediate (category id 2)
1. `nmap` — Nmap
2. `wireshark` — Wireshark
3. `burp-suite` — Burp Suite
4. `owasp-top-10` — OWASP Top 10
5. `active-directory-basics` — Active Directory Basics
6. `metasploit` — Metasploit
7. `windows-privilege-escalation` — Windows Privilege Escalation
8. `linux-privilege-escalation` — Linux Privilege Escalation

### Red Team (category id 3)
1. `reconnaissance` — Reconnaissance
2. `enumeration` — Enumeration
3. `exploitation` — Exploitation
4. `web-pentesting` — Web Pentesting
5. `active-directory-attacks` — Active Directory Attacks
6. `pivoting` — Pivoting
7. `persistence` — Persistence
8. `evasion-techniques` — Evasion Techniques

### AI Security (category id 4)
1. `ai-fundamentals` — AI Fundamentals
2. `prompt-injection` — Prompt Injection
3. `llm-security` — LLM Security
4. `ai-red-teaming` — AI Red Teaming
5. `secure-ai-applications` — Secure AI Applications
6. `model-attacks` — Model Attacks
7. `ai-threat-detection` — AI Threat Detection
8. `agent-security` — Agent Security

*(Note: this category bundles both AI/LLM foundations (`ai-fundamentals`)
and AI Security proper (the other 7) — see the Track-Letter mapping below
for how this maps onto the long-term target taxonomy.)*

## Lesson Order (exact, every module)

Every module's 3 lessons follow the identical, fixed order:

1. `introduction` — "Introduction" (10 min, 25 XP, **preview** — viewable
   even when the module is locked)
2. `core-concepts` — "Core Concepts" (20 min, 50 XP)
3. `hands-on-practice` — "Hands-on Practice" (30 min, 100 XP)

---

## Prerequisites — the real dependency graph

There is no `prerequisite_id` column on `RoadmapModule` or `Lesson`.
Progression is enforced entirely through `UserModuleProgress.unlocked`,
computed by `app/roadmap/services.py`:

- **Within a category**: strictly linear. Module *N* unlocks only after
  module *N-1* in the **same category** is completed
  (`unlock_next_module`, keyed on `display_order`).
- **Across categories**: **parallel, not gated.** `initialize_user_progression()`
  unlocks module 1 of **every** active category the first time a user
  loads `/roadmap/`. A brand-new user can start `nmap` (Intermediate) or
  `reconnaissance` (Red Team) on day one, without ever touching Beginner.
  This is the real, current behavior — it is documented here rather than
  silently changed, per the instruction to use the actual curriculum, not
  invent dependencies. If category-level gating (e.g. Intermediate
  requires Beginner-complete) is wanted, it is a deliberate future design
  decision, not something this lock assumes.
- **Lesson-level**: within an unlocked module, lessons are linear
  (`prev_slug`/`next_slug`), except the `introduction` lesson of every
  module, which is always viewable (and completable) as a preview, even
  while its module is locked (`Lesson.is_preview`).
- **Server-side enforcement (fixed in this ticket, see Known Issues)**:
  `GET /roadmap/<module>/<lesson>/` and
  `POST /roadmap/<module>/<lesson>/complete` now both check
  `services.lesson_locked_for_user()` before rendering or awarding XP —
  previously this was UI-only and a locked module's lessons/XP were
  reachable by direct URL.

### Dependency graph (as implemented, per category)

```
Beginner:
linux-fundamentals → computer-networking → python-programming → web-fundamentals
    → git-github → operating-systems → cryptography-basics → virtualization

Intermediate:
nmap → wireshark → burp-suite → owasp-top-10 → active-directory-basics
    → metasploit → windows-privilege-escalation → linux-privilege-escalation

Red Team:
reconnaissance → enumeration → exploitation → web-pentesting
    → active-directory-attacks → pivoting → persistence → evasion-techniques

AI Security:
ai-fundamentals → prompt-injection → llm-security → ai-red-teaming
    → secure-ai-applications → model-attacks → ai-threat-detection → agent-security

(all four chains' first module unlock in parallel for a new user —
no cross-category edge exists in the current implementation)
```

---

## Track-letter mapping (long-term reference, non-binding)

The target taxonomy (Tracks A–L, from the driving spec) is a planning
reference, **not** the locked structure — the locked structure is the
4-category tree above. This table shows how today's modules map onto that
taxonomy, so future work knows where a new module would slot in without
re-deriving it:

| Existing module | Category | Closest target track |
|---|---|---|
| `python-programming` | Beginner | **A — Programming** |
| `operating-systems`, `virtualization` | Beginner | **B — Computer Fundamentals** |
| `linux-fundamentals` | Beginner | **C — Linux** |
| `linux-privilege-escalation` | Intermediate | C — Linux (advanced) |
| `computer-networking` | Beginner | **D — Networking** |
| `nmap`, `wireshark` | Intermediate | D — Networking (tooling) |
| `web-fundamentals` | Beginner | **E — Web Fundamentals** |
| `cryptography-basics` | Beginner | **F — Cybersecurity Fundamentals** |
| `burp-suite`, `owasp-top-10` | Intermediate | **G — Web Security** |
| `web-pentesting` | Red Team | G — Web Security / H — Pentesting |
| `active-directory-basics`, `windows-privilege-escalation` | Intermediate | *(System Security — not yet a target track letter; adjacent to H/I)* |
| `metasploit` | Intermediate | **H — Pentesting** (tooling) |
| `reconnaissance`, `enumeration`, `exploitation` | Red Team | **H — Pentesting** |
| `active-directory-attacks`, `pivoting`, `persistence`, `evasion-techniques` | Red Team | **I — Red Team** |
| `ai-fundamentals` | AI Security | **K — AI / LLM** |
| `prompt-injection`, `llm-security`, `ai-red-teaming`, `secure-ai-applications`, `model-attacks`, `ai-threat-detection`, `agent-security` | AI Security | **L — AI Security** |
| `git-github` | Beginner | *(developer tooling — supports Track A, not itself a target track)* |
| — | — | **J — Blue Team / SOC**: no roadmap lessons exist, but real labs/missions do (see Future Curriculum) |

---

## Labs — audited inventory

`app/labs/` has **79 labs** across 10 categories (`linux`, `networking`,
`web-security`, `soc`, `nmap`, `wireshark`, `active-directory`,
`digital-forensics`, `cloud-security`, `soc-simulator`), reachable at
`/labs/` and `/labs/<slug>`. 12 legacy non-interactive labs (ids 4-15,
`is_interactive=False`) are not shown in the `/labs/` nav but remain
directly reachable by URL — a known drift documented, not fixed, in this
pass (see Known Issues).

## Missions — audited inventory

`app/core/missions/mission_loader.py`'s `MISSIONS` dict has **16**
terminal missions, reachable at `/interactive-labs` and
`/interactive-labs/<slug>`: `linux-basics`, `linux-permissions`,
`bash-fundamentals`, `networking-fundamentals`, `network-troubleshooting`,
`nmap-fundamentals`, `network-reconnaissance`, `wireshark-fundamentals`,
`web-fundamentals`, `http-deep-dive`, `burp-fundamentals`,
`authentication-sessions`, `sql-injection-fundamentals`,
`xss-fundamentals`, `csrf-fundamentals`, `file-upload-security`.

## Lab Mapping (Lesson → Lab)

Only real, existing lab slugs are listed. "None yet" means no lab
currently reinforces that module — it stays a documented gap, not a
fabricated link.

| Roadmap module | Reinforcing lab(s) |
|---|---|
| `linux-fundamentals` | `linux-basics`, `linux-files`, `linux-permissions`, `linux-searching`, `linux-archives`, `linux-processes`, `linux-networking`, `linux-logs`, `linux-challenge` (category `linux`) |
| `computer-networking` | `net-basics`, `net-interfaces`, `net-connectivity`, `net-explore`, `net-reach`, `net-inspect`, `net-dns`, `net-services`, `net-troubleshoot` (category `networking`) |
| `python-programming` | None yet |
| `web-fundamentals` | `websec-http`, `websec-cookies`, `websec-sessions` (category `web-security`) |
| `git-github` | None yet |
| `operating-systems` | None yet |
| `cryptography-basics` | None yet |
| `virtualization` | `cloud-orientation` (category `cloud-security`) — **partial match, linked in YC-037.0**: its `list-vms`/`get-vm`/`network` commands are the only place on this platform showing real virtual machines (state, size, subnet, public IP) and a virtual network; its IAM/storage/`audit` objectives go beyond this module into cloud security proper. The lesson says so explicitly rather than overselling the fit. `cloud-open-ssh` is adjacent (exposed VM management port) but not linked — see Content Status below |
| `nmap` | `nmap-basics` (category `nmap`) — **linked in YC-037.1**, scoped to `hands-on-practice`; `nmap-services`/`nmap-advanced` are real and audited here but not wired (only one `lab_slug` fits per lesson — see Content Status below) |
| `wireshark` | `wireshark-basics`, `wireshark-protocols`, `wireshark-advanced` (category `wireshark`) |
| `burp-suite` | `websec-http`, `websec-headers` (proxy-adjacent; no dedicated Burp lab) |
| `owasp-top-10` | `websec-auth`, `websec-idor`, `websec-sqli`, `websec-xss`, `websec-csrf`, `websec-upload`, `websec-headers` (category `web-security`) |
| `active-directory-basics` | `ad-orientation`, `ad-inactive-account` (category `active-directory`) |
| `metasploit` | None yet |
| `windows-privilege-escalation` | None yet |
| `linux-privilege-escalation` | `linux-permissions`, `linux-processes` (partial — no dedicated privesc lab) |
| `reconnaissance` | `nmap-basics`, `net-explore` |
| `enumeration` | `nmap-services`, `nmap-advanced` |
| `exploitation` | None yet |
| `web-pentesting` | `websec-sqli`, `websec-xss`, `websec-csrf`, `websec-upload`, `websec-idor` |
| `active-directory-attacks` | `ad-compromised-password`, `ad-overprivileged`, `ad-least-privilege` |
| `pivoting` | None yet |
| `persistence` | None yet |
| `evasion-techniques` | None yet |
| `ai-fundamentals` through `agent-security` | None yet (no AI/LLM lab exists) |

**Blue Team / SOC content that exists with no roadmap module to attach
to**: `soc-brute-force`, `soc-port-scan`, `soc-insider` (category `soc`),
and the 16-lab `soc-simulator` category (`soc-analyst-fundamentals`,
`soc-alert-investigation`, `soc-incident-response`,
`soc-scenario-ransomware`, `soc-scenario-phishing`,
`soc-scenario-insider`, `soc-scenario-dns-tunnel`,
`soc-scenario-malware-beacon`, `soc-hunt-powershell`, `soc-hunt-dns`,
`soc-hunt-creds`, `soc-hunt-lateral`, `soc-hunt-schtask`,
`soc-hunt-beacon`, `soc-capstone-black-phoenix`,
`soc-blue-team-assessment`), plus `digital-forensics` category
(`forensics-fundamentals`, `forensics-applied`, `forensics-advanced`).
This is real, substantial Blue Team content — see **Future Curriculum**,
Track J.

## Mission Mapping (Lesson → Mission)

| Roadmap module | Reinforcing terminal mission(s) |
|---|---|
| `linux-fundamentals` | `linux-basics`, `linux-permissions`, `bash-fundamentals` |
| `computer-networking` | `networking-fundamentals`, `network-troubleshooting`, `network-reconnaissance` |
| `web-fundamentals` | `web-fundamentals`, `http-deep-dive` |
| `nmap` | `nmap-fundamentals` |
| `wireshark` | `wireshark-fundamentals` |
| `burp-suite` | `burp-fundamentals` |
| `owasp-top-10` | `authentication-sessions`, `sql-injection-fundamentals`, `xss-fundamentals`, `csrf-fundamentals`, `file-upload-security` |
| `web-pentesting` | `sql-injection-fundamentals`, `xss-fundamentals`, `csrf-fundamentals`, `file-upload-security` |
| all other modules | None yet |

---

## Content Status — Python Programming (YC-036.3)

The first module in the roadmap with real, authored lesson content
(previously: 3 template-placeholder lessons, no content file at all).
Written per-lesson, matching each lesson's actual title and time
budget rather than a forced identical template:

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | What Python is (interpreted vs. compiled), REPL vs. script files, statements vs. expressions, indentation as grammar, comments, `print()`, common syntax mistakes, reading error messages | `app/content/roadmap/beginner/python-programming/introduction.md` |
| `core-concepts` (20 min) | EMPTY | Variables as names-not-boxes, assignment/reassignment, naming rules, dynamic typing, the 5 core types (`int`/`float`/`str`/`bool`/`None`), `type()`, type conversion, arithmetic/comparison operators, f-strings, `input()` | `app/content/roadmap/beginner/python-programming/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | `if`/`elif`/`else`, `and`/`or`/`not`, `for`/`while`/`range()`, `break`/`continue`, defining functions (parameters vs. arguments, `return`, local scope), 2 drills (FizzBuzz, vowel counter) + a capstone exercise (a password-strength checker combining all of the above) | `app/content/roadmap/beginner/python-programming/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY** under the standard used for
this pass: a student who reads a lesson start to finish can explain the
concept in their own words and can run every code example as shown
(every example was hand-verified to execute correctly and produce the
stated output before being written into the lesson). Each lesson uses
the existing markdown → `bleach`-sanitised HTML pipeline unchanged — no
lesson-content architecture change was needed; the existing allowlisted
tag set (headings, paragraphs, lists, tables, fenced code blocks,
blockquotes) was already sufficient.

This lowers the roadmap-wide "empty lessons" count from 94 to 91 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

---

## Content Status — Linux Fundamentals (YC-036.4)

The second module with real, authored lesson content. Unlike Python
Programming, `introduction` already had genuine (if thin) content before
this ticket — written for an earlier pass, 36 lines, no exercises or
knowledge check. It was rewritten to the same depth standard as the other
two lessons rather than left as-is, since "real content" here means every
command taught follows an explain → demonstrate → show output → explain
output → common mistake → exercise structure, which the original did not:

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | WEAK (real but shallow, no exercises/knowledge check) | Terminal vs. shell vs. command vs. program, `pwd` and `whoami` taught to the full command standard, `ls`/`ls -la`, hidden (dot) files, the four most common top-level directories | `app/content/roadmap/beginner/linux-fundamentals/introduction.md` |
| `core-concepts` (20 min) | EMPTY | The filesystem as one tree rooted at `/`, absolute vs. relative paths, `.`/`..`/`~`, navigating with `cd` (including a worked debugging exercise on a mistyped path), reading a file with `cat` | `app/content/roadmap/beginner/linux-fundamentals/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | Creating (`touch`, `mkdir`), copying/moving (`cp`, `mv`), deleting (`rm`, `rm -r` — with an explicit "this is not a recycle bin" section), reading `ls -l` permission strings, changing permissions with `chmod` (symbolic and numeric), why permissions matter for least privilege, and a guided capstone walkthrough of the platform's real **Linux Basics** terminal mission | `app/content/roadmap/beginner/linux-fundamentals/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY** under the same standard used
for Python Programming: a student who reads a lesson start to finish can
explain the concept in their own words, and every command's example output
shown in the lesson is accurate for the platform's actual simulated
environment (the `/home/student` home directory and `Documents/welcome.txt`
used throughout match the real `linux-basics` terminal mission's simulated
filesystem in `app/core/missions/mission_loader.py`, not an invented one).

This lowers the roadmap-wide "empty lessons" count from 91 to 89 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### Terminal / mission cross-links (new in this ticket)

Previously (see the Mission section above, "no lesson currently links to a
lab or mission") this was purely documentation. YC-036.4 wires the first
real links, scoped to the one module/lesson pair they were written for
rather than guessed for all 32 modules:

- Every lesson in `linux-fundamentals` now shows a **"Try it in the
  Terminal"** link to the existing free-practice terminal (`/terminal`,
  `terminal.terminal_page` — no new route).
- `hands-on-practice` additionally shows a **"Linux Basics Mission"**
  link to the existing terminal mission (`/terminal/mission/linux-basics`,
  `terminal.mission_page` — no new route, no new mission).

Implemented as a small static mapping in `app/roadmap/services.py`
(`_LESSON_MISSION_LINKS`, `_TERMINAL_PRACTICE_MODULES`) consumed by
`get_lesson_view_context()`'s `practice` key and rendered in
`lesson.html`'s new `.rm-practice` section — additive only; every other
module's lesson page is unaffected (`practice` is `{}` for them, and the
template renders nothing when it's falsy).

### CyberMentor lesson context (new in this ticket)

`lesson.html` now sets `current_lab = "<module title> — <lesson title>"`
immediately before including `components/ai_chat.html`, which already
reads a `current_lab` template variable (the same hook labs and terminal
missions use — see `app/labs/routes.py`, `app/core/terminal/routes.py`).
No new AI context channel was built: `MentorContext.summary()` already
renders this as "Currently on: ..." in CyberMentor's system prompt
(`app/core/ai/types.py`), and `context_engine.collector.collect_learning`
already looks up a matching `Lab` row by slug when one exists — for a
lesson (not a lab), no `Lab` row matches, which is expected and harmless;
the free-text label is still passed straight through as context. This
change is not Linux-specific: it applies to every roadmap lesson page,
closing a pre-existing gap where CyberMentor had no idea which lesson a
student had open.

---

## Content Status — Computer Networking (YC-036.5)

The third module with real, authored lesson content. `introduction` was
not merely thin here — Known Issues #3b flagged it as a leftover XSS
sanitisation test fixture (`<script>alert(1)</script>`), which made it
the roadmap's one and only `placeholder`-classified lesson. It's been
replaced entirely, not patched:

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | PLACEHOLDER (XSS test payload, not real content — Known Issues #3b) | What a network/host/client/server is, the request path (interface → switch/router → network → server → response), a conceptual MAC-vs-IP preview, what a protocol is, `ping` taught to the full command standard | `app/content/roadmap/beginner/computer-networking/introduction.md` |
| `core-concepts` (20 min) | EMPTY | MAC addresses (local/Layer 2 identity, ARP resolution, broadcast), IPv4 addressing (private/public/loopback), subnetting (CIDR, subnet mask, network/broadcast address, worked `/24` → `/26` examples, host-count formula), ports and sockets, well-known ports | `app/content/roadmap/beginner/computer-networking/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | TCP vs. UDP, the TCP three-way handshake, DNS resolution (query/response flow, `nslookup`, `NXDOMAIN`), routing and the default gateway, NAT (brief, non-oversimplified), `ip addr`/`ip route`/`ss` taught to the full command standard, a 6-step troubleshooting reasoning chain (interface → IP → gateway → connectivity → DNS), and a capstone walkthrough of the real **Networking Fundamentals** terminal mission | `app/content/roadmap/beginner/computer-networking/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY**. Every command example's
output (`ping`, `ip addr`, `ip route`, `ss`, `nslookup`, including the
`NXDOMAIN` failure case) was taken directly from
`app/core/terminal/network.py`'s actual formatting logic and the real
`networking-fundamentals` mission's simulated topology in
`app/core/missions/mission_loader.py` (`10.10.10.20` student-pc,
`10.10.10.1` gateway, `10.10.10.10` example.local, `10.10.10.53` dns01)
— not invented example data.

This lowers the roadmap-wide "empty lessons" count from 89 to 87, and
the "placeholder lessons" count from 1 to **0** (see Known Issues #3/#3b)
— reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### Mission cross-link — scoped differently from Linux Fundamentals

`introduction` and `hands-on-practice` both show a **"Networking
Fundamentals Mission"** link (`/terminal/mission/networking-fundamentals`,
`terminal.mission_page` — no new route, no new mission). Unlike Linux
Fundamentals, **no lesson in this module shows a "Try it in the Terminal"
free-practice link**: `app/core/terminal/services.start_shell()` (the
handler behind the bare `/terminal` sandbox) never attaches a simulated
network to the shell — only `start_mission()` does — so `ping`/`ip`/`ss`/
`nslookup` (everything this module teaches) would fail with "no network
configured for this session" in that sandbox. Sending students there
would have been actively misleading, so the free-practice link is
withheld for this module entirely (`_TERMINAL_PRACTICE_MODULES` in
`app/roadmap/services.py` intentionally excludes `computer-networking`).
`core-concepts` (addressing/subnetting math, no commands) gets no
practice link at all, consistent with the rule that a link should only
appear where it genuinely helps.

### Future curriculum note (not built in this ticket, per scope)

The driving spec's teaching philosophy covers considerably more ground
than 3 lessons can hold without becoming a command dump (Rule: "do not
use one generic template for every networking lesson" / "do not overload
the networking track"). Deliberately left out of this pass, as topics
for a possible future module or lesson expansion:

- **DHCP** (the DORA process) — no lesson currently teaches it.
- **Firewalls** as their own topic — mentioned nowhere yet; a natural
  fit once a module reaches traffic-filtering concepts.
- **A dedicated application-protocol survey** (HTTP/HTTPS/SSH/FTP/SMTP
  beyond the single well-known-ports table in `core-concepts`) —
  intentionally deferred to `web-fundamentals`, per the driving spec's
  own instruction not to duplicate that module's territory.
- **IPv6** — IPv4 only, throughout.
- **OSI vs. TCP/IP layer models as their own explicit lesson** — the
  concepts (link/interface, addressing, transport, application) are
  taught throughout via the actual protocols that live at each layer,
  but no lesson names or diagrams the models directly by their formal
  layer numbers.
- **Wireshark-style packet-field breakdown** (flags, payload framing) —
  out of scope here; `wireshark` is already its own Intermediate-track
  module with its own lesson slots.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next networking
content pass, per the explicit instruction against inventing curriculum.

---

## Content Status — Web Fundamentals (YC-036.6)

The fourth module with real, authored lesson content. All three lessons
were EMPTY (`content_path` pointed at a file that didn't exist —
`app/content/roadmap/beginner/web-fundamentals/` was an empty
directory) — none had the leftover-fixture problem Networking's
`introduction` had:

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | URL anatomy (scheme/host/port/path/query/fragment, and which parts the server actually sees), the DNS → TCP → TLS → HTTP chain built directly on Computer Networking's DNS/TCP content, client vs. server and browser vs. web server, a first look at client-side vs. server-side, `open` taught to the full command standard | `app/content/roadmap/beginner/web-fundamentals/introduction.md` |
| `core-concepts` (20 min) | EMPTY | The request line / status line format, HTTP methods and their conventional semantics, status-code families with a worked 401-vs-403-vs-404 comparison using real simulator evidence, headers (what question each one answers, not a memorization dump), request bodies (form-encoded vs. JSON, why `Content-Type` matters), response bodies (HTML vs. JSON) | `app/content/roadmap/beginner/web-fundamentals/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | Why HTTP is stateless and what problem cookies solve, the `Set-Cookie`/`Cookie` flow traced through a real login, cookie security attributes (`Secure`/`HttpOnly`/`SameSite`) explained by what each one changes, the session model, authentication vs. authorization made concrete with real 401/403 evidence, why authorization must be server-side, JSON APIs including two different real auth mechanisms (cookie session vs. bearer token) on the same server, HTTPS/TLS explained conceptually (and what it does *not* guarantee), `open`/`headers`/`cookies`/`response` taught to the full command standard, a malformed-JSON debugging exercise, and a capstone walkthrough of the real **Web Fundamentals** terminal mission | `app/content/roadmap/beginner/web-fundamentals/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY**. Every request/response
example (`GET /products?id=42`, the `/admin` 401-vs-403 pair, the
`/login` → `Set-Cookie` → `/profile` session flow, `/api/me` with both a
bearer token and a cookie, and the malformed-JSON `/api/login` case) was
captured by actually running `app/core/terminal/web.py`'s `WebApp`
simulator (`build_request` + `WebApp.handle`) and copying its real
output verbatim — not invented example data. The simulated site
(`cybershop.training`, `app/core/terminal/web.py`) is the same one the
**Web Fundamentals** and **HTTP Deep Dive** terminal missions, and every
later `websec-*` interactive lab, already use — nothing new was built to
generate these examples.

This lowers the roadmap-wide "empty lessons" count from 87 to 84 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### Mission cross-links — all three lessons, unlike Networking

All three lessons show a **"Web Fundamentals Mission"** link
(`/terminal/mission/web-fundamentals`, `terminal.mission_page` — no new
route, no new mission). This module does not withhold a link from
`core-concepts` the way Networking withheld one from its own
addressing/subnetting lesson: `core-concepts`' Challenge exercise
directly uses the `open`/`headers` terminal commands, so it genuinely
needs the same practice link as the other two. **No lesson shows a "Try
it in the Terminal" free-practice link**, for the same structural reason
as Networking: `shell.web_lab` is `None` until
`MissionRunner._attach_web_lab()` sets it (`app/core/missions/
mission_runner.py`), which only happens inside a real mission — the bare
`/terminal` sandbox never attaches a simulated web app, so `open`/
`headers`/`cookies`/`response` would fail there
(`_TERMINAL_PRACTICE_MODULES` in `app/roadmap/services.py` excludes
`web-fundamentals`, same as `computer-networking`).

### Lab cross-links — new in this ticket, not attempted by YC-036.4/.5

YC-036.4 and YC-036.5 both deliberately scoped their cross-linking to
missions only, explicitly leaving lab links as "a real gap for whoever
picks up the next module" (see the Mission section near the top of this
document). YC-036.6 is that pickup, still scoped narrowly: a new
`_LESSON_LAB_LINKS` mapping (`app/roadmap/services.py`, additive
alongside the existing `_LESSON_MISSION_LINKS`) links `core-concepts` to
the real **HTTP Requests & Responses** lab (`websec-http`) and
`hands-on-practice` to the real **Cookie Security Flags** lab
(`websec-cookies`) — both already-existing, active, interactive labs in
the `web-security` lab category, matched by actual content rather than
one generic "web-fundamentals" lab guess. `lesson.html` gained one new
conditional block (`practice.lab_slug` → a button to
`labs.detail`), additive only — the existing `show_terminal`/
`mission_slug` blocks are unchanged. `introduction` gets no lab link, by
design: it's a URL/architecture overview with no hands-on lab
counterpart yet. The remaining `web-fundamentals` lab-mapping candidate
from the audited inventory, `websec-sessions` (Session Fixation), is
left unlinked — it fits session *attacks*, which this module
deliberately does not teach yet (see below).

### Future curriculum note (not built in this ticket, per scope)

Deliberately left out of this pass, as topics for a possible future
module or lesson expansion:

- **HTML/CSS/JavaScript as their own dedicated lessons** — the driving
  spec explicitly warns against turning this module into "a full
  frontend-development course." Client-side vs. server-side is taught
  conceptually (Introduction, Hands-on Practice), and the DOM/JavaScript
  execution model is deferred entirely — `web-fundamentals` has no
  lesson slot for it, and XSS Fundamentals (already real content, gated
  behind Burp Suite in the Intermediate track) is where DOM-based
  concerns actually get taught in this platform today.
- **REST as its own theory lesson** — resources/endpoints/statelessness
  are introduced inline in the APIs section (Hands-on Practice §8)
  rather than as a separate theoretical treatment, per the driving
  spec's own instruction to avoid "unnecessary theoretical complexity."
- **Session attacks** (fixation, hijacking) — the *mechanism* (Set-
  Cookie/Cookie, what a session identifier actually is) is taught in
  depth; deliberately stops short of teaching the attacks themselves,
  consistent with "understanding comes first." The real `websec-sessions`
  (Session Fixation) lab exists and is ready to attach once a later
  module teaches session attacks explicitly.
- **A dedicated forms/HTML-forms lesson** — form submission is taught
  through its HTTP consequence (the `application/x-www-form-urlencoded`
  body in Core Concepts §7, and the real login form in Hands-on
  Practice §4), not through HTML tag syntax.
- **WebSockets, HTTP/2, HTTP/3** — out of scope; this module covers
  HTTP/1.1 request/response semantics only, matching what the terminal
  simulator (`app/core/terminal/web.py`) actually implements.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next Web Security
content pass (`burp-suite`, `owasp-top-10`), per the explicit instruction
against inventing curriculum.

---

## Content Status — Cryptography Basics / Cybersecurity Fundamentals (YC-036.7)

The fifth module with real, authored lesson content, and the first
naming mismatch worth recording explicitly: the driving ticket for this
pass was titled "Cybersecurity Fundamentals," but **no module by that
name exists in the locked curriculum** — the Beginner category has no
"misc security fundamentals" slot (Rule 2 above forbids inventing one).
The closest real match is `cryptography-basics` (**Cryptography
Basics**), which the Track-letter mapping table above already assigns
to **F — Cybersecurity Fundamentals**. Rather than inventing a ninth
Beginner module (a roadmap-structure change, forbidden by Rules 48/49)
or renaming the existing one (forbidden by Rule "do not rename lessons
unnecessarily"), this ticket targets `cryptography-basics` as-is,
unchanged in title/slug/order, and uses its 3 real lesson slots to
teach both the general security mental model the ticket asked for
(CIA triad, Asset → Threat → Vulnerability → Risk → Control →
Detection → Response → Recovery, controls, least privilege, defense in
depth, ethics/authorization) *and* the module's own literal subject —
cryptography (hashing vs. encryption vs. encoding, password security,
digital signatures, certificates) — concentrated into `hands-on-practice`
alongside a compressed treatment of malware, phishing, incident
response, and backups. This is a scope decision, not a curriculum
change — flagged here per Rule 49 ("if a curriculum integrity problem
is found: STOP and report it") rather than silently resolved.

All 3 lessons were EMPTY (no content file at all, same starting state
as Web Fundamentals):

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | What cybersecurity means and how it relates to information/computer security and the AppSec/NetSec/OpSec specialties; the CIA triad taught through a medical-record scenario where one incident can break more than one property; the full Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery reasoning chain, introduced as the module's throughline; the eight-question security mindset | `app/content/roadmap/beginner/cryptography-basics/introduction.md` |
| `core-concepts` (20 min) | EMPTY | Asset categories; threats vs. threat actors (motivation/capability/resources/target/opportunity, explicitly not "every threat is a hacker"); vulnerability vs. exploit vs. attack vs. risk kept as four distinct terms via one worked example; risk as likelihood + impact compared across two systems sharing the same vulnerability; attack surface; authentication/authorization/accounting (AAA) reusing Web Fundamentals' real 401-vs-403 `/admin` example verbatim; security controls by category (administrative/technical/physical) and function (preventive/detective/corrective), with explicit overlap; defense in depth and least privilege, the latter tied directly back to Linux Fundamentals' `chmod 777` warning | `app/content/roadmap/beginner/cryptography-basics/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | Hashing vs. encryption vs. encoding (comparison table + why encoding is not security); password security (reuse/credential stuffing, managers, MFA, salting against rainbow tables); digital signatures and certificates taught correctly (not "encryption with a private key" — hash + asymmetric keys, authentication/integrity/non-repudiation as three distinct guarantees) and tied to Web Fundamentals' TLS/certificate content; malware by defining behavior (virus/worm/trojan/ransomware in depth, spyware/botnet/rootkit briefly); phishing and social engineering (why it works, real red flags, layered defenses, no operational templates); logs → detection → the 6-phase incident-response lifecycle via a fictional account-compromise walkthrough; backups as a control, with the "having backups" vs. "having *recoverable* backups" distinction; ethics and authorization as a hard line, stated explicitly ahead of every offensive-security module later in this platform; a full capstone scenario (**YushaBank**) that walks an unfamiliar system through the entire eight-link chain, Socratic (student reasons first) then worked | `app/content/roadmap/beginner/cryptography-basics/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY** under the same standard used
for the four prior content passes. Every cross-reference to another
module's content (the `/admin` 401/403 pair, the `chmod 777` warning,
TLS's three guarantees) quotes or matches that module's actual, already-
written lesson text rather than inventing a new example — the same
discipline Web Fundamentals used for its own Computer Networking
references.

This lowers the roadmap-wide "empty lessons" count from 84 to 81 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### No lab or mission cross-link — a real, documented gap, not an oversight

Unlike Linux Fundamentals, Computer Networking, and Web Fundamentals,
**no lesson in this module links to a lab or terminal mission.** The
audited inventory above has no lab category or mission whose actual
content matches general security-fundamentals/cryptography material —
the closest candidates (`soc-*` labs, `digital-forensics` labs) belong
to Blue Team/SOC territory this module doesn't teach, and inventing a
link to a mismatched lab would violate the explicit "do not create fake
links" rule. `_LESSON_MISSION_LINKS` / `_LESSON_LAB_LINKS` in
`app/roadmap/services.py` are therefore **not** modified by this
ticket — `cryptography-basics` correctly continues to resolve to an
empty `practice` context, exactly as it did before, and exactly as the
pre-existing Lab/Mission Mapping tables above already documented
("None yet"). CyberMentor context still works with no change needed:
the `current_lab` hook wired generically in YC-036.4 applies to every
roadmap lesson page, this module included.

### Future curriculum note (not built in this ticket, per scope)

Deliberately left out of this pass, as topics for a possible future
module or lesson expansion — the driving ticket's own list of 56
sections could not fit 3 lesson slots without becoming a shallow survey
instead of the connected mental model the ticket explicitly asked for:

- **Zero trust** — not taught; it's a real architecture principle but
  adds a fourth major topic to an already-dense `core-concepts` lesson
  without a natural home yet.
- **Threat modeling as a named, formal process** (STRIDE-style or
  otherwise) — the *reasoning* (Asset → Threat → Vulnerability → Risk)
  is taught throughout; a dedicated step-by-step threat-modeling
  methodology lesson is not.
- **Security by design** as its own named section — implicit in the
  "control comes after risk, not before" framing (Introduction §5,
  Core Concepts throughout) but never named as a standalone principle.
- **Blue Team vs. Red Team vs. Purple Team** — not taught; this
  platform's real SOC/Blue Team labs (`soc-simulator`,
  `digital-forensics`) exist with no roadmap module yet (Track J,
  already documented above) — this vocabulary fits better once that
  track gets a lesson slot than bolted onto a cryptography module.
- **Security policies** (acceptable-use, formal password policy
  documents) as their own topic — password *security* is taught in
  depth; the enterprise-policy-document framing of it is not.
- **Cryptography depth beyond concepts** — symmetric vs. asymmetric
  algorithms by name, key exchange, cipher modes — deliberately out of
  scope, consistent with the driving ticket's own instruction to teach
  "concepts, not advanced cryptographic implementation."
- **A formal Quiz-engine knowledge-check** — this module's Knowledge
  Check sections are markdown, embedded in the lesson content itself,
  matching the pattern of every prior content pass; the separate `Quiz`
  DB-row system (Known Issues #4, still placeholder/gameable
  platform-wide) is unchanged, consistent with every prior ticket in
  this series leaving that specific backlog item untouched.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next Beginner or
Intermediate content pass, per the explicit instruction against
inventing curriculum.

---

## Content Status — Git & GitHub (YC-036.8)

The sixth module with real, authored lesson content. Unlike
Cryptography Basics (YC-036.7), this ticket had no naming ambiguity —
`git-github` ("Git & GitHub") is module 5 of the Beginner category,
next in `display_order` after `web-fundamentals` (YC-036.6) and
before `operating-systems`, and was the lowest-order of the three
remaining EMPTY Beginner modules (`git-github`, `operating-systems`,
`virtualization`) at the time this ticket was picked up.

All 3 lessons were EMPTY (no content file at all):

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | The actual problem version control solves; the precise Git-vs-GitHub distinction (Git is standalone, offline software; GitHub is one hosting service built on it); the three-area mental model (working directory → staging area → repository); `git init`/`git status`/`git add`/`git commit` taught to the full command standard with real, accurate output | `app/content/roadmap/beginner/git-github/introduction.md` |
| `core-concepts` (20 min) | EMPTY | `git log`/`git log --oneline`; `git diff` vs. `git diff --staged` (the working-directory-vs-staged vs. staged-vs-last-commit distinction); branches as movable commit pointers, `git branch`/`git switch`/`git switch -c`; fast-forward merges; merge conflicts and the `<<<<<<<`/`=======`/`>>>>>>>` marker syntax; `.gitignore`; remotes (`git remote add`, `origin`) as the exact mechanism connecting to GitHub | `app/content/roadmap/beginner/git-github/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | `git clone` (and why it copies entire history, not just current files); what GitHub adds on top of Git specifically (README, Issues, forks, pull requests — none of them Git features); the full fork → clone → branch → commit → push → pull-request → review → merge workflow; `git push`; a dedicated security section on why a committed secret must be treated as compromised the instant it's pushed regardless of a later "fix" commit, why `.gitignore` can't retroactively help, why a private repository doesn't change the core risk, and the real fix (rotate the credential at its source) — connecting directly back to Cybersecurity Fundamentals' asset/credential framing; a capstone scenario (two students, a pull request, and an accidentally-committed password) | `app/content/roadmap/beginner/git-github/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY** under the same standard used
for the five prior content passes. Every command's output (`git
init`, `git status`, `git add`, `git commit`, `git log`, `git diff`,
`git branch`/`git switch`, `git merge`, `git remote -v`, `git clone`,
`git push`) is real, accurate, standard Git CLI output — verified
against actual Git behavior rather than invented, since (see below)
this platform has no Git simulator to capture output from directly,
unlike prior modules that quoted their platform's real simulator
verbatim.

This lowers the roadmap-wide "empty lessons" count from 81 to 78 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### No lab or mission cross-link — the terminal has no `git` command

Audited directly against `app/core/terminal/commands.py`'s `@cmd`
registry: there is no `git` command implemented anywhere in this
platform's terminal simulator (the registry covers filesystem,
networking, packet-capture, and HTTP commands only — see the file's
full `@cmd(...)` list). Neither the free-practice terminal nor any
terminal mission can run a single command this module teaches. This
is a genuine, larger gap than Cryptography Basics' — Web Fundamentals,
Computer Networking, and Linux Fundamentals could all be practiced
on-platform because a real simulator already existed for each; Git
has none. Rather than inventing a fake `git` terminal command or
linking to an unrelated lab, `hands-on-practice` §8 documents this
explicitly and directs students to their own machine's real Git
installation — every command in this module is standard Git with no
platform-specific behavior, so this loses nothing in accuracy, only
the in-browser convenience prior modules had. `_LESSON_MISSION_LINKS` /
`_LESSON_LAB_LINKS` in `app/roadmap/services.py` are **not** modified
by this ticket — `git-github` resolves to an empty `practice` context,
exactly as it did before. CyberMentor context needed no change: the
generic `current_lab` hook (YC-036.4) applies here unchanged.

### Future curriculum note (not built in this ticket, per scope)

Deliberately left out of this pass:

- **A Git terminal simulation** — the real gap described above. Would
  need its own in-memory repository model (commits, branches, a
  working-directory/staging-area distinction) mirroring
  `app/core/terminal/web.py`'s pattern for HTTP — a genuinely
  substantial addition, not attempted here per the explicit
  instruction against building new infrastructure in a content-only
  ticket.
- **Rebasing, cherry-picking, stashing, tags** — real Git features,
  intentionally deferred as beyond a beginner module's scope; `merge`
  is the only history-combining operation taught.
- **GitHub Actions / CI** — mentioned by name once (as an example of
  what GitHub adds beyond Git) but not taught; belongs closer to a
  DevOps-adjacent module this roadmap doesn't currently have.
- **Resolving a merge conflict end-to-end as a hands-on exercise** —
  the marker syntax and reasoning are taught in depth (Core Concepts
  §6); actually triggering and resolving one requires two real
  branches with real conflicting edits, which the missing terminal
  simulation (above) would make far more teachable than prose alone.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next Beginner
content pass (`operating-systems`, `virtualization`) or a future
platform-infrastructure ticket, per the explicit instruction against
inventing curriculum.

---

## Content Status — Operating Systems (YC-036.9)

The seventh module with real, authored lesson content, and the first
since `linux-fundamentals` (YC-036.4) to genuinely reuse existing
lab/mission infrastructure rather than leave `practice` empty —
`operating-systems` is module 6 of the Beginner category, next after
`git-github` (YC-036.8) and before `cryptography-basics` (already
real, YC-036.7).

All 3 lessons were EMPTY (no content file at all):

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | What an OS actually does as the control layer between applications and hardware; user space vs. kernel space and why the separation exists (security/stability/controlled hardware access); system calls, using a real file-read (`cat`) traced step by step; a first program-vs-process distinction, built directly on Linux Fundamentals' existing "program" definition | `app/content/roadmap/beginner/operating-systems/introduction.md` |
| `core-concepts` (20 min) | EMPTY | Program vs. process made concrete (browser tabs as separate processes, explicitly non-universal); the process lifecycle (Created/Ready/Running/Waiting/Terminated); scheduling, time slices, and context switching; threads vs. processes (shared memory as the key structural difference) and concurrency vs. parallelism; RAM vs. persistent storage as a durability distinction, not just "temporary vs. permanent"; virtual memory (address spaces, pages, page faults, swapping) with the explicit "not just using disk as RAM" correction; a Python Programming tie-in tracing a running `.py` script through every concept in the lesson | `app/content/roadmap/beginner/operating-systems/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | Filesystems as an OS-managed resource (what `ls`/`cat` are actually asking the kernel to do, without re-teaching their syntax); permissions and identity as an OS-enforced security mechanism (`id`/`groups` against real, verified terminal output, tied to Linux Fundamentals' `chmod`); device drivers; networking from the OS's perspective (the kernel's network stack, tied to Computer Networking without repeating it); services/daemons; the boot process; an explicit "OS security together" section connecting every mechanism in the module to privilege escalation, malware analysis, endpoint security, and digital forensics later in this platform; a six-question capstone scenario forcing the student to trace processes/memory/permissions/network through one situation at once | `app/content/roadmap/beginner/operating-systems/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY**. Every terminal command
example (`whoami`, `id`, `groups`, `uname`, `uname -a`) was verified
against the actual implementation in
`app/core/terminal/commands.py` before being written into the lesson
— not invented output — the same discipline used for every prior
content pass's platform-specific examples.

This lowers the roadmap-wide "empty lessons" count from 78 to 75 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### Lab and mission cross-links — real, existing, previously-unused resources

Unlike Cryptography Basics (YC-036.7) and Git & GitHub (YC-036.8),
this module has genuine, already-shipped infrastructure that matches
its content and was sitting completely unlinked from any lesson:

- **`linux-processes` lab** ("Processes" — `ps`/`top`/`kill`/`jobs`
  against a simulated runaway process) reinforces `hands-on-practice`
  §10's process-lifecycle material directly.
- **`linux-permissions` mission** ("Linux Permissions" —
  `ls -l`/`whoami`/`id`/`groups`/`chmod`/`chown` against a realistic
  filesystem) reinforces `hands-on-practice` §4's identity/permissions
  material directly.

Both are added to `_LESSON_MISSION_LINKS`/`_LESSON_LAB_LINKS`
(`app/roadmap/services.py`), scoped to `hands-on-practice` only —
neither `introduction` nor `core-concepts` teaches process or
permission *commands*, so neither gets a mission/lab CTA (same
discipline as Computer Networking's `core-concepts`, which teaches no
commands and gets no practice link at all).

`operating-systems` also joins `_TERMINAL_PRACTICE_MODULES` alongside
`linux-fundamentals`: `whoami`, `uname`, `uname -a`, `id`, and `groups`
(this module's own commands, verified for real against the terminal's
`@cmd` registry) all work in the bare, network-less free-practice
sandbox with no mission attachment required. This is a module-level
flag in the existing implementation (matching how `linux-fundamentals`
already applies it uniformly), so it appears on all three lessons —
including `core-concepts`, which itself teaches no commands directly.
This is a deliberate, documented tradeoff rather than an oversight:
the CTA is a standing "practice this module's commands here" invitation
tied to the module as a whole, not a claim that the specific lesson
you're reading uses the terminal, and the architecture has no
per-lesson granularity for this particular flag today — a real,
scoped gap for whoever revisits `_lesson_practice_links` next.

### Future curriculum note (not built in this ticket, per scope)

Deliberately left out of this pass:

- **CPU scheduling algorithms** (round-robin, priority queues, etc.) —
  the *concept* of scheduling and time-slicing is taught in depth;
  specific algorithms are explicitly out of scope for a beginner
  module, per the driving ticket's own instruction not to overload
  beginners with scheduler internals.
- **A dedicated OS/process-inspection lab or mission built specifically
  for this module** — the real `linux-processes` lab and
  `linux-permissions` mission are strong, genuine matches and are now
  linked, but neither was purpose-built for this lesson's exact
  scenario (Section 11's browser/terminal/download/Python capstone has
  no matching simulated environment). Documented as a possible future
  enhancement, not built here.
- **Filesystem types, journaling, or on-disk data structures** —
  Section 3 explains the filesystem as an OS-managed resource
  conceptually; it deliberately does not go into ext4/NTFS-level
  implementation detail, consistent with "do not repeat the entire
  Linux filesystem lesson."
- **BIOS/UEFI internals** — the boot process (Section 8) stops at the
  conceptual firmware → bootloader → kernel → services → login chain,
  per the driving ticket's explicit instruction not to overcomplicate
  this.
- **Windows- or macOS-specific OS internals** — every concept is
  taught generally (true of any general-purpose OS) with Linux as the
  concrete, practicable example throughout, consistent with every
  other module on this platform.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next Beginner
content pass (`virtualization` is the one remaining EMPTY Beginner
module) or a future platform-infrastructure ticket, per the explicit
instruction against inventing curriculum.

---

## Content Status — Virtualization (YC-037.0)

The eighth module with real, authored lesson content, and the one that
**completes the Beginner category** — `virtualization` is module 8 of
Beginner, last in `display_order`, and was the single remaining EMPTY
Beginner module after YC-036.9. All 24 Beginner lessons now have real
content.

All 3 lessons were EMPTY (`app/content/roadmap/beginner/virtualization/`
did not exist at all):

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | The problem virtualization solves (waste/fragility/inflexibility/irreversibility of one-OS-per-machine); virtualization defined by what software *presents* rather than by a product name; physical vs. virtual resources as a worked table; what a VM actually is and what physically exists of one when powered off (files — chiefly the virtual disk); the hypervisor introduced by analogy to the OS definition from YC-036.9; host vs. guest with four concrete consequences of confusing them; the physical hardware → hypervisor → VM → guest OS → applications stack read as a chain of requests, traced through a real guest file write | `app/content/roadmap/beginner/virtualization/introduction.md` |
| `core-concepts` (20 min) | EMPTY | Type 1 vs. Type 2 hypervisors with a real tradeoff table and an explicit "neither is universally better" plus a caution that the two-type model blurs in practice (Hyper-V's root partition, KVM-in-kernel); virtual hardware as configuration; vCPUs and the two-layer scheduling model, with the "1 vCPU = 1 physical core" oversimplification corrected head-on; memory virtualization as a *second* translation stacked on the guest's own virtual memory (guest virtual → guest physical → host physical), tied directly to OS Core Concepts §8; virtual disks (image formats, fixed vs. thin provisioning, persistence); virtual networking (NAT/bridged/host-only) built on Computer Networking's own NAT/addressing material; allocation, overcommitment and per-resource contention behaviour; a deliberately two-sided performance section (hardware-assisted virtualization, paravirtualized drivers) that neither claims virtualization is free nor that it is always slow; the VM lifecycle | `app/content/roadmap/beginner/virtualization/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | Snapshots and the snapshot-chain mechanism; a dedicated section on why a snapshot is **not** a backup (7-row comparison, three consequences); images/templates, reproducibility, image provenance and baked-in secrets; an explicitly honest isolation section (strong boundary, four named dependencies, not a guarantee); VMs vs. containers built from the one structural difference (own kernel vs. shared kernel), including why Linux containers on Windows/macOS run inside a Linux VM; the cybersecurity connection in both directions — what virtualization enables (labs, CTFs, malware research, vulnerable machines, cloud) and what it risks (hypervisor vulnerabilities, VM escape *as a concept only*, insecure configuration, exposed management interfaces, weak credentials, excessive allocation, unpatched guests/hosts); Linux as host and as guest, with the "commands act on the guest" habit; the guest process → guest OS → virtual devices → hypervisor → physical resources trace tying the whole module back to YC-036.9; two practical exercises (a student's own VM settings, and the real Cloud Basics lab with verbatim simulator output); a 8-question laptop-lab design scenario (16 GB / 8 threads / 512 GB, Kali + vulnerable Ubuntu on a Windows host) with no single "correct" configuration handed out | `app/content/roadmap/beginner/virtualization/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY** under the same standard used
for the seven prior content passes.

**No fabricated output anywhere.** This platform's terminal has no
hypervisor, VM, or `lscpu`/`free`-style command (audited against
`app/core/terminal/commands.py`'s `@cmd` registry — the same audit
YC-036.8 ran for `git`), so rather than invent hypervisor CLI output,
the module uses only two kinds of concrete material: labelled
conceptual diagrams, and **real output captured by actually running
`app/labs/cloud/engine.py`** (`format_vm_table`, `format_vm`) against
the real `YUSHACLOUD_PROD` account definition. Every `list-vms` /
`get-vm` line quoted in `hands-on-practice` §12 is verbatim from that
run, and `tests/test_roadmap_lock.py::TestVirtualizationContent::
test_quoted_lab_output_matches_the_real_simulator` re-runs the engine
and fails if the lesson ever drifts from it. Product names
(VirtualBox, VMware, Hyper-V, KVM, Xen, Proxmox, Parallels; `.vdi`/
`.vmdk`/`.vhdx`/`.qcow2`; VT-x/AMD-V; EPT/NPT) are used only as
accurate identification, never with invented output attached.

This lowers the roadmap-wide "empty lessons" count from 75 to 72 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### Lab cross-link — one, partial, and described as partial

`hands-on-practice` links to the real **Cloud Basics: Tour the Account**
lab (`cloud-orientation`, `/labs/cloud-orientation`, `labs.detail` — no
new route, no new lab), added to `_LESSON_LAB_LINKS` in
`app/roadmap/services.py`. The Lab Mapping table above previously read
"None yet (`cloud-security` category is adjacent, not a direct match)";
that judgement was made at *module* granularity. At command
granularity it is too strong: `list-vms` and `get-vm` return a VM's
state, size, subnet, security group and public IP, and `network` shows
the VPC/subnet layout those VMs sit in — that is precisely this
module's virtual-hardware and virtual-networking material, and it is
the only place on this platform where a student can inspect a real
VM's configuration at all. The lab's other four objectives (IAM,
storage, `audit`) genuinely do go beyond this module, so the lesson
says that outright in §12 rather than implying the whole lab is a
virtualization exercise.

`cloud-open-ssh` ("SSH Open to the World") is a plausible second link
for §8's *exposed management interface* material and was deliberately
**not** wired: one well-matched link per lesson, same restraint every
prior pass in this series used.

### No mission link, and no free-practice terminal link

- **Missions**: none of the 16 terminal missions involves
  virtualization in any form (audited against
  `app/core/missions/mission_loader.py`'s `MISSIONS` dict).
  `_LESSON_MISSION_LINKS` is untouched by this ticket.
- **Free-practice terminal**: `virtualization` is deliberately **not**
  added to `_TERMINAL_PRACTICE_MODULES`. Unlike `linux-fundamentals`
  and `operating-systems`, this module teaches no command that exists
  in the terminal's `@cmd` registry — a "Try it in the Terminal" CTA
  would send students somewhere nothing in the module works, the same
  reasoning that excluded `computer-networking` and `web-fundamentals`
  for their own (different) structural reasons. `introduction` and
  `core-concepts` therefore resolve to an empty `practice` context and
  show no CTA at all, consistent with computer-networking's
  `core-concepts`.

CyberMentor context needed no change: the generic `current_lab` hook
(YC-036.4) applies here unchanged and passes
"Virtualization — <lesson title>" through to the mentor's system
prompt.

### Future curriculum note (not built in this ticket, per scope)

Deliberately left out of this pass:

- **A virtualization lab or terminal simulation built for this module**
  — the real gap. `cloud-orientation` is a genuine but partial match
  (above); nothing on this platform simulates a hypervisor, a VM
  settings page, snapshot chains, or a `host-only`-vs-`bridged`
  experiment. A lab in the shape of "inspect this VM's configuration,
  then predict what it can reach" would reinforce
  `hands-on-practice` §11 far better than prose plus an off-platform
  exercise does. Not attempted here, per the instruction against
  building new infrastructure in a content-only ticket; documented as
  the module's clearest future enhancement.
- **Hypervisor internals** — trap-and-emulate, binary translation,
  ring/privilege-level mechanics, VMCS/VMCB structures. Hardware-
  assisted virtualization and second-level address translation are
  named and explained *by what they achieve*; their implementation is
  out of scope for a beginner module.
- **Container tooling** — Docker/Podman/Kubernetes commands, image
  layers, registries, orchestration. §7 teaches the VM-vs-container
  *distinction* (which the driving ticket asked for) and stops there;
  a container track would be its own module, and none exists.
- **Live migration, clustering, HA, storage tiering** — enterprise
  virtualization operations, well beyond a Beginner-category module.
- **VM escape as technique** — the concept is taught (§8) precisely
  because it is what makes "it's in a VM" a mitigation rather than a
  guarantee; exploitation is explicitly out of scope and stated as
  such in the lesson itself.
- **Cloud as its own roadmap module** — no `cloud` module exists in the
  locked structure, though 6 real `cloud-security` labs do. §12 borrows
  one of them; a proper cloud module remains Future Curriculum.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next content pass
(the Beginner category is now complete; `nmap` is the lowest-order
EMPTY module remaining, in Intermediate) or a future
platform-infrastructure ticket, per the explicit instruction against
inventing curriculum.

---

## Content Status — Nmap (YC-037.1)

The ninth module with real, authored lesson content, and the first in
the **Intermediate** category — `nmap` is module 1 of Intermediate,
the lowest-order EMPTY module remaining after the Beginner category's
completion in YC-037.0. Framed throughout as reconnaissance and
enumeration (discovery → evidence → next investigation), not as an
exploitation module — this platform's offensive-technique modules are
later, gated content, and this module explicitly stops before them.

All 3 lessons were EMPTY (`app/content/roadmap/intermediate/nmap/` did
not exist at all):

| Lesson | Classification before | Scope written | File |
|---|---|---|---|
| `introduction` (10 min, preview) | EMPTY | What Nmap is and the investigation-tool framing (infer, not know); host/port/service vocabulary; why a port number is not proof of a service (well-known/registered/dynamic ranges); TCP vs. UDP conceptually (built on Computer Networking, not re-taught); the three port states (open/closed/filtered) with the exact beginner-misconception corrections; host discovery vs. port scanning, demonstrated with real `-sn` output | `app/content/roadmap/intermediate/nmap/introduction.md` |
| `core-concepts` (20 min) | EMPTY | The default scan explained precisely (what it does and doesn't test); targeted port scanning (`-p`) and ranges (`-p 1-1000`) with the coverage/time tradeoff; scanning all TCP ports (`-p-`); service/version detection (`-sV`) framed as evidence with real confidence, not certainty; TCP vs. UDP scanning in practice (`-sT`/`-sU`); host discovery failure and `-Pn`; OS detection (`-O`) as inference; NSE scripting (`-sC`) conceptually, explicitly not as automatic vulnerability discovery; all four WRONG/CORRECT corrections from the driving spec, restated in context; TCP connect vs. SYN scanning (`-sS`) at the network level, explicitly not as evasion; responsible scanning/timing; output formats, briefly | `app/content/roadmap/intermediate/nmap/core-concepts.md` |
| `hands-on-practice` (30 min) | EMPTY | The six-question enumeration mindset; a dedicated security-ethics section (authorization boundary, IDS/IPS/firewall/SIEM/rate-limit consequences, no detection-evasion framing); six practical exercises (host discovery, open ports, a specific port, a port range, service/version detection, interpret-and-decide) each with objective/command/real output/reasoning/interpretation/common mistake; a full evidence-based investigation write-up (Target/Host/Open ports/Services/Versions/Findings/Next investigation) using real data, stopping at "worth investigating further" rather than a vulnerability claim; the six-stage Reconnaissance→Enumeration→Service identification→Vulnerability research→Validation→Remediation methodology, with Nmap's role in it stated explicitly; cross-track callbacks to Computer Networking, Linux Fundamentals, Web Fundamentals, Operating Systems, Cryptography Basics, and Virtualization | `app/content/roadmap/intermediate/nmap/hands-on-practice.md` |

All three now classify as **HIGH_QUALITY** under the same standard used
for the eight prior content passes.

**No fabricated output anywhere.** This platform's terminal has a real,
deterministic simulated `nmap` command (`app/core/terminal/commands.py`
`_nmap`, backed by `app/core/terminal/network.py`'s `VirtualNetwork`) —
every scan quoted in all three lessons (`-sn`, the default scan, `-p`,
port ranges, `-sV`, `-sT`, `-sU`, `-Pn -O`, and the combined
`-Pn -O -sV`) was captured by actually running that real command
handler against the real, authorized lab network already declared in
the real **Nmap Fundamentals** mission (`app/core/missions/
mission_loader.py`, `10.10.10.0/24`: web01/fileserver/dns01/training)
— not invented example data, and re-verified a second time against the
exact `_nmap()` command handler (not just the lower-level engine
functions) before being written into the lessons.
`tests/test_roadmap_lock.py::TestNmapContent::
test_quoted_scan_output_matches_the_real_simulator` re-runs the same
command handler and fails if a lesson's quoted output ever drifts from
it. Two things are deliberately described only in prose, with no
output claimed: `-p 1-1000` (the real output is 1,000 lines; quoting
it in full would be unreadable, so only the command's real, verified
effect is described) and `-sC` (the simulator accepts the flag without
error but does not model script-specific output, so NSE is taught
conceptually with an explicit note that no simulated script result
exists to quote).

This lowers the roadmap-wide "empty lessons" count from 72 to 69 (see
Known Issues #3) — reflected in both `flask roadmap-audit` and
`tests/test_roadmap_lock.py`'s pinned baseline.

### Lab and mission cross-links — both real, both scoped to hands-on-practice

- **Mission**: the real **Nmap Fundamentals** mission
  (`/terminal/mission/nmap-fundamentals`, `terminal.mission_page` — no
  new route, no new mission) is linked from `hands-on-practice`. Its
  ten objectives (basic scan, port identification, targeted scanning,
  service/version detection, TCP connect scanning, UDP scanning, OS
  detection on a ping-blocking host, a final full-recon challenge) map
  directly onto this lesson's six exercises — a genuine rehearsal of
  the same investigation, not an adjacent guess. Added to
  `_LESSON_MISSION_LINKS` (`app/roadmap/services.py`).
- **Lab**: the real **Nmap: Your First Scan** lab (`nmap-basics`,
  `/labs/nmap-basics`, `labs.detail` — no new route, no new lab) is
  linked from `hands-on-practice` as the natural entry-level pairing
  for the lesson's basic-scan and port-discovery material. Two further
  real labs exist and are referenced by name in the lesson text as
  natural next steps (`nmap-services` for service enumeration,
  `nmap-advanced` for OS detection) but are **not** wired as links —
  the lesson→lab mapping is one `lab_slug` per lesson (the same
  structural shape every prior module's link worked within), so only
  the closest single match is wired rather than picked arbitrarily.
  Added to `_LESSON_LAB_LINKS` (`app/roadmap/services.py`).
- **Free-practice terminal**: `nmap` is deliberately **not** added to
  `_TERMINAL_PRACTICE_MODULES`. Audited directly against
  `app/core/terminal/services.py`'s `start_shell()`: the bare `/terminal`
  sandbox never attaches a simulated network (only a mission's runner
  does — the same reasoning that excluded `computer-networking`,
  `web-fundamentals`, and `virtualization`), so the `nmap` command would
  report "no network configured for this session" there. Sending
  students to the bare sandbox would be actively misleading; the real
  mission link is the correct, working alternative.
- `introduction` and `core-concepts` intentionally get no lab/mission
  CTA — both are conceptual-plus-command-reference lessons; the actual
  hands-on investigation, and the real link to practice it, live in
  `hands-on-practice`, consistent with every prior module's discipline
  of not offering a practice CTA where a lesson doesn't call for one.

CyberMentor context needed no change: the generic `current_lab` hook
(YC-036.4) applies here unchanged and passes "Nmap — <lesson title>"
through to the mentor's system prompt.

### Future curriculum note (not built in this ticket, per scope)

Deliberately left out of this pass:

- **NSE script output in the simulator** — the real gap named above.
  Adding script-specific simulated output (e.g. a default-script HTTP
  title grab) would need new engine behavior in
  `app/core/terminal/network.py`, not attempted here per the explicit
  instruction against building new infrastructure in a content-only
  ticket.
- **Vulnerability research and validation** — the methodology in
  Hands-on Practice §13 names these as the next two stages after this
  module's scope; neither is taught here, consistent with this being a
  reconnaissance/enumeration module and with the platform's later,
  more advanced modules (Metasploit, the Red Team track) being the
  appropriate home for that material.
- **`nmap-services` and `nmap-advanced` as wired lesson links** — both
  real and referenced by name in the lesson text; not wired as
  `_LESSON_LAB_LINKS` entries because the current schema fits one
  `lab_slug` per lesson. A future enhancement to that data shape (a
  list instead of a single dict) would let all three real nmap labs be
  linked from one lesson without picking a single "best" one.
- **Automation/output-format depth (`-oN`/`-oX`/scripting a scan
  pipeline)** — mentioned by name in Core Concepts §15 as a capability
  that exists, not taught as a skill; out of scope for a foundational
  reconnaissance module.

None of these were silently added as new roadmap rows — they're
documented here as candidates for whoever scopes the next Intermediate
content pass (`wireshark` is the next lowest-order EMPTY module) or a
future platform-infrastructure ticket, per the explicit instruction
against inventing curriculum.

---

## XP Philosophy

- A lesson's XP scales with depth: preview/`introduction` = 25, core
  concepts = 50, hands-on = 100 — the practice step is worth 4× the
  reading step, consistent with "understanding over completion."
- A module additionally awards a `xp_reward` bonus (175 XP) once, on
  completing all 3 of its lessons — awarded exactly once per user
  (`bonus_awarded` flag), never re-awarded on lesson replay.
- Labs and terminal missions run on the same underlying `award_xp()`
  engine as the roadmap (`app/dashboard/services.py`), so XP earned
  anywhere on the platform contributes to one account-wide level, not a
  separate per-subsystem currency.
- XP is never written directly to `user.xp`; every award goes through
  `award_xp()`, which recalculates level as a side effect.

---

## Curriculum Rules

1. **Do not add a new module without evaluating where it belongs** — use
   the Track-letter mapping above to place it, and update this document
   in the same change.
2. **Do not add lessons randomly** — every lesson must belong to a
   specific module at a specific `display_order`; there is no "misc"
   bucket.
3. **Do not move lessons without checking prerequisites** — moving a
   lesson to a different module or reordering within a module changes
   what a student is assumed to already know; re-verify the dependency
   graph above before doing so.
4. **Do not delete lessons that have user progress** — `UserLessonProgress`
   rows reference `lesson_id`; deleting a lesson orphans that history.
   Deactivate (`is_active=False` on the parent module) instead, or
   migrate progress explicitly.
5. **Do not create duplicate subjects** — before adding a "Linux" or
   "Networking" module/category, check this document; `linux-fundamentals`
   and `computer-networking` already exist.
6. **Do not publish empty lessons** — a lesson row should not go live
   without a real `content_path` file behind it. (96 of today's lessons
   currently violate this as inherited debt — see Known Issues; new
   lessons must not add to that count.)
7. **Labs should reinforce lessons** — see Lab Mapping; a new lab should
   be added to that table in the same change that creates it.
8. **Missions should reinforce skills** — see Mission Mapping; same rule.
9. **Advanced content should have prerequisites** — Intermediate/Red
   Team/AI Security modules assume their category's earlier modules;
   don't add advanced-difficulty content to Beginner's category.
10. **Lesson content can improve without changing curriculum structure**
    — rewriting `core-concepts.md` for `nmap` is always fine and never
    requires touching this document or bumping `ROADMAP_VERSION`.

---

## Roadmap Status System

**Tracks / categories / modules:**

| Status | Meaning |
|---|---|
| `AVAILABLE` | Unlocked for this user (`UserModuleProgress.unlocked=True`, not yet completed) |
| `IN PROGRESS` *(curriculum-level, not a DB status)* | Real labs/missions exist but no roadmap lessons reference them yet — e.g. Track J below |
| `COMING SOON` | A module/category exists in the DB but its lesson content is still placeholder (applies to 69/96 of today's lessons — Python Programming (YC-036.3), Linux Fundamentals (YC-036.4), Computer Networking (YC-036.5), Web Fundamentals (YC-036.6), Cryptography Basics (YC-036.7), Git & GitHub (YC-036.8), Operating Systems (YC-036.9), Virtualization (YC-037.0) — the entire Beginner category — and Nmap (YC-037.1), first in Intermediate — 27 lessons total — are real) |
| `FUTURE` | No DB rows exist yet; listed only in this document's Future Curriculum section |

**Lessons** (per-user, computed by `services.module_status` /
`lesson_locked_for_user`):

| Status | Meaning |
|---|---|
| `AVAILABLE` | Module unlocked for this user, or this is a preview (`introduction`) lesson |
| `LOCKED` | Module not yet unlocked for this user, and not a preview lesson — server-enforced as of this ticket |
| `COMPLETED` | `UserLessonProgress.completed=True` for this user |

---

## Future Curriculum

Not created as empty DB rows — listed here only, per the explicit
instruction against hundreds of "Coming soon" placeholders.

- **Track J — Blue Team / SOC**: status **IN PROGRESS**, not FUTURE — 3
  legacy + 16 `soc-simulator` labs and a `digital-forensics` category (6
  labs) already exist and are reachable (`/labs/`), but no roadmap
  category/module currently references them. The orphan
  "Security Operations Center" roadmap category (id 5, 0 modules — see
  Known Issues) is the most likely eventual home.
- **Track K/L depth** — `ai-fundamentals`/AI Security modules exist but
  have no lab/mission counterpart at all (no LLM sandbox exists yet).
- **Capstone track** — no module, lab, or mission of this shape exists.
- **System Security** as its own track/category — currently split across
  `active-directory-basics`, `windows-privilege-escalation`,
  `linux-privilege-escalation` (Intermediate) with no unifying category.
- **Dedicated Pentesting-methodology modules** (scope, evidence,
  reporting) — `reconnaissance`/`enumeration`/`exploitation` exist;
  methodology/reporting content does not.
- **Metasploit / Windows privilege escalation / pivoting / persistence /
  evasion-techniques labs** — the roadmap modules exist; no lab or
  mission reinforces any of them yet.

---

## Known Issues (documented, not fixed in this pass — except where noted)

1. **Server-side lock enforcement — fixed in this ticket.** Previously,
   `GET /roadmap/<module>/<lesson>/` and the `complete` POST performed no
   lock check at all; a logged-in user could open and complete any
   lesson of any locked module directly by URL (and the roadmap overview
   page linked directly to every lesson, locked or not). Both routes now
   call `services.lesson_locked_for_user()` / `is_lesson_locked()` before
   rendering or awarding XP, and `roadmap.html`'s per-lesson row now
   shows a disabled "🔒 Locked" state instead of a working link when a
   non-preview lesson's module is locked, matching `module.html`'s
   existing pattern.
2. **Orphan "Security Operations Center" category** (id 5, 0 modules,
   `display_order=85`) — created by `app/simulators/soc/seed.py`, not by
   `app/roadmap/seed.py`; re-running `flask seed-roadmap` on a fresh DB
   produces only 4 categories. Left in the database (never delete
   progress-bearing or any other data per project rule); documented as
   the likely future home for Track J.
3. **69 of 96 lessons have no real content** (94 at the time of
   YC-036.2's audit, 91 after YC-036.3, 89 after YC-036.4, 87 after
   YC-036.5, 84 after YC-036.6, 81 after YC-036.7, 78 after YC-036.8,
   75 after YC-036.9, 72 after YC-037.0, 69 after YC-037.1).
   All 3 lessons each of `python-programming` (YC-036.3),
   `linux-fundamentals` (YC-036.4), `computer-networking` (YC-036.5),
   `web-fundamentals` (YC-036.6), `cryptography-basics` (YC-036.7),
   `git-github` (YC-036.8), `operating-systems` (YC-036.9),
   `virtualization` (YC-037.0), and `nmap` (YC-037.1) have
   genuine Markdown content; every
   other `content_path` resolves to nothing and renders "This lesson is
   coming soon." This is the single largest
   content-debt item and remains explicitly out of scope beyond these
   nine modules. **The Beginner category is complete** — all 8 of its
   modules / 24 of its lessons are real; Intermediate has its first
   real module (`nmap`, 1 of 8). The remaining 69 empty lessons span
   the rest of Intermediate, Red Team, and AI Security, tracked here
   for whoever picks up the next module's lessons (`wireshark` is the
   lowest-order EMPTY module remaining).
3b. **`computer-networking/introduction.md`'s content used to be a test
   fixture, not a stub — fixed in YC-036.5.** Previously a raw
   `<script>alert(1)</script>` payload (confirmed harmless at the time:
   `bleach` stripped it on render, so nothing unsafe ever reached a
   browser) rather than merely thin content. Replaced with real lesson
   content in YC-036.5 — `tests/test_roadmap_lock.py`'s
   `test_leftover_xss_payload_is_gone` pins that it doesn't come back.
   Line kept (rather than deleted) as a record of what this lesson used
   to contain, for anyone auditing the module's history.
4. **All 320 quiz questions are placeholder and trivially gameable** —
   generated by `quiz_seed.py` as `"{module} — question {i}: which option
   is correct?"`, correct answer always at position `((i-1) mod 4)+1`.
   Not fixed here; same rationale as #3.
5. **Duplicate `get_lesson_view_context` definition** in
   `app/roadmap/services.py` (first definition, plus its private helpers
   `render_lesson_markdown`/`_sanitise_lesson_html`, is fully shadowed by
   a second definition ~100 lines later and is dead code). Left alone in
   this pass to keep the diff minimal and scoped to the lock-enforcement
   fix; flagged for cleanup.
6. **Duplicate `(category_id, display_order)` in the `labs` table** —
   category 2 (networking) and category 4 (digital-forensics) each have
   two labs sharing orders 1/2/3 (legacy vs. interactive variants with
   near-identical titles). Documented, not restructured, in this pass.

---

## Roadmap Version

```python
ROADMAP_VERSION = "1.0"   # app/roadmap/services.py
```

Bump this only for a deliberate structural change (new track, reordered
modules, changed prerequisites) — never for a content edit. The number is
also threaded into `get_roadmap_context()`'s return value as
`roadmap_version` and shown on the roadmap page hero as "Curriculum
v1.0".
