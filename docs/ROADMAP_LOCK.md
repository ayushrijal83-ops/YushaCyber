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
  both real and reachable, but **no lesson currently links to a lab or
  mission** (verified: zero `url_for('labs...`, `missions...` references
  anywhere in `app/templates/roadmap/` or `app/content/`). The **Lab
  Mapping** and **Mission Mapping** sections below are the first
  documented cross-reference between them — a foundation for wiring real
  "Open Lab" / "Start Mission" links into `lesson.html` in a future
  ticket, not a change made in this one (see Section 24 of the driving
  spec: no new features in this pass).
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
| `COMING SOON` | A module/category exists in the DB but its lesson content is still placeholder (applies to 91/96 of today's lessons — Python Programming's 3 lessons are real as of YC-036.3) |
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
3. **91 of 96 lessons have no real content** (94 at the time of
   YC-036.2's audit). `linux-fundamentals/introduction` (real, 36 lines)
   and all 3 of `python-programming`'s lessons (real, written for
   YC-036.3) have genuine Markdown content; `computer-networking/
   introduction` is still a 4-line stub (in fact a leftover XSS-
   sanitization test payload, `<script>alert(1)</script>`, harmlessly
   stripped by `_sanitise_lesson_html`/bleach on render — see `#3b`
   below); every other `content_path` resolves to nothing and renders
   "This lesson is coming soon." This is the single largest content-debt
   item and remains explicitly out of scope beyond Python Programming —
   tracked here for whoever picks up the next module's lessons.
3b. **`computer-networking/introduction.md`'s content is a test
   fixture, not a stub** — worth its own line since it's not merely
   thin, it's actively the wrong kind of content (a raw
   `<script>alert(1)</script>` payload). Confirmed harmless: `bleach`
   strips it on render, so nothing unsafe reaches a browser. Left
   as-is, since replacing it is lesson-writing work (Rule 10 territory),
   not a structural fix — flagged clearly so it isn't mistaken for
   intentional content by whoever writes Computer Networking next.
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
