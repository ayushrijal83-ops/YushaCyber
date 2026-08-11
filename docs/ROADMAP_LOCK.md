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
| `virtualization` | None yet (`cloud-security` category is adjacent, not a direct match) |
| `nmap` | `nmap-basics`, `nmap-services`, `nmap-advanced` (category `nmap`) |
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
| `COMING SOON` | A module/category exists in the DB but its lesson content is still placeholder (applies to 87/96 of today's lessons — Python Programming (YC-036.3), Linux Fundamentals (YC-036.4), and Computer Networking (YC-036.5) — 9 lessons total — are real) |
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
3. **84 of 96 lessons have no real content** (94 at the time of
   YC-036.2's audit, 91 after YC-036.3, 89 after YC-036.4, 87 after
   YC-036.5). All 3 lessons each of `python-programming` (YC-036.3),
   `linux-fundamentals` (YC-036.4), `computer-networking` (YC-036.5), and
   `web-fundamentals` (YC-036.6) have genuine Markdown content; every
   other `content_path` resolves to nothing and renders "This lesson is
   coming soon." This is the single largest
   content-debt item and remains explicitly out of scope beyond these
   three modules — tracked here for whoever picks up the next module's
   lessons.
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
