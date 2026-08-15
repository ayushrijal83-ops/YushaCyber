# Linux Privilege Escalation — Core Concepts

## 1. What You Will Learn

By the end of this lesson you should be able to:

- reason about **users, groups and ownership** as grants of authority
- read Linux **file permissions** and say what each bit permits and why it matters
- explain **SUID** and **SGID** correctly — including why the bit alone is not a vulnerability
- reason about a **sudo rule** instead of memorising exploit commands
- explain **Linux capabilities** as slices of root's power
- reason about **scheduled tasks**, **services**, **PATH resolution**, **writable files**, and **environment/configuration**
- explain **kernel** and **container** escalation surfaces at the right altitude
- apply the module's central distinction: a **finding is not a confirmed escalation path**
- **prioritise** findings, **validate** one safely, record **evidence**, and connect every surface to **remediation**

## 2. How to Read This Lesson

Each surface below is a place a **privilege boundary** lives (Introduction §11). For every one, hold the four questions: *who owns it, who can modify it, who executes it, with what privileges?* The surfaces are many; the question is always the same.

A note on honesty, kept throughout: this platform's terminal can run identity and permission commands (`id`, `groups`, `ls -l`, `chmod`, `chown`) for real, and Lesson 3 uses them. It has **no** `sudo`, SUID, `getcap`, `cron` or `systemctl`. So the sudo, SUID, capability, cron and service sections below teach *reasoning* with **clearly-labelled illustrative examples**, not captured output. That is deliberate: the reasoning is the transferable skill, and a fabricated root shell would teach the opposite of what this module is for.

## 3. Users, Groups and Ownership

Identity is the foundation every other boundary is built on.

- **`/etc/passwd`** lists accounts: username, UID, GID, home directory, shell. It is **world-readable by design** — it holds no passwords (those moved to `/etc/shadow` decades ago). Reading it tells you which accounts exist and, crucially, which are **UID 0**.
- **`/etc/group`** lists groups and their members. It is how you discover, for another account or your own, which groups grant which authority.

Here is the real `/etc/passwd` from the training host:

```
cat /etc/passwd
root:x:0:0:root:/root:/bin/bash
student:x:1000:1000::/home/student:/bin/bash
```

The security value is the UID field. `root` is `0`; `student` is `1000`. Any account with UID 0 *is* root regardless of its name — a second UID-0 account in `/etc/passwd` would itself be a serious finding.

**Group membership as authority.** Some groups are ordinary; some carry real power *depending on the system's configuration*:

| Group | What membership can mean (configuration-dependent) |
|---|---|
| `sudo` (or `wheel`) | May run commands through sudo — subject to the rules in `/etc/sudoers` |
| `docker` | Can talk to the container daemon, which typically runs as root — often effectively root-equivalent |
| `adm` | Can read many system logs — a horizontal/information exposure, not automatically root |
| `disk` | Raw access to disk devices — can read anything on them, bypassing file permissions |

The discipline: seeing a group in your `id` output is a **lead**, not a conclusion. `docker` membership is only root-equivalent *if the daemon is present and running*; `sudo` membership only helps *if a usable rule exists*. You investigate; you do not assume. This is the finding-vs-confirmed-path distinction (§14) in miniature.

> **Do not treat this as a route to extracting passwords.** Reading `/etc/passwd` to enumerate accounts and UIDs is legitimate; the goal is understanding the identity map, not harvesting secrets.

## 4. File Permissions

Every file and directory carries a 9-bit permission set plus an owner and a group.

```
-rw-r--r--   1  student  student   71  public.txt
│└┬┘└┬┘└┬┘      └──┬──┘  └──┬──┘
│ │  │  │          owner    group
│ │  │  └── others: r--   (read)
│ │  └───── group:  r--   (read)
│ └──────── owner:  rw-   (read, write)
└────────── type:   -     (regular file; d = directory)
```

| Bit | On a **file** | On a **directory** |
|---|---|---|
| **r** | read the contents | list the entries |
| **w** | modify the contents | create/delete/rename entries **within** it |
| **x** | execute it as a program | enter/traverse it (`cd` into it) |

Two consequences that trip people up:

- **Write on a directory is powerful.** If you can write to a directory, you can often delete or replace files *inside* it — even files you do not own — because the ability to remove a directory entry is a property of the directory, not the file. A world-writable directory that holds a script a privileged process runs is a classic boundary failure.
- **Write on a file only matters if something privileged reads or runs it.** A world-writable file that nothing important ever consumes is harmless. This is the heart of §14.

`chmod` changes the permission bits; `chown` changes ownership. Both are real on this platform, and Lesson 3 uses `chown` to demonstrate an ownership boundary being crossed legitimately.

**Why writable *privileged* files matter:** if a file is executed or read by a **root** process, and **you** can write to it, you can influence what root does. That is the combination — writable *and* privileged — that turns a permission into an escalation path.

## 5. SUID

Normally a program runs with **your** privileges. A program with the **SUID** bit set runs with the privileges of its **owner** instead.

In a long listing, SUID shows as an `s` in the owner's execute position:

```
Illustrative example — not captured output. This platform's terminal does
not simulate SUID bits or a real /usr/bin.

-rwsr-xr-x  1 root root  68208  /usr/bin/passwd
   ▲
   └── 's' here: runs as the OWNER (root), not as the caller
```

Why this exists at all: some legitimate tasks genuinely need elevated rights. `passwd` must edit `/etc/shadow`, which only root can write — so `passwd` is SUID-root, and while it runs it has root's power, *for the specific job of changing a password*.

**This is the section people get wrong, so state it precisely:**

> **The SUID bit is not a vulnerability.** It indicates an elevated *execution context*. Whether it is a *problem* depends entirely on what the program **does** with that context.

The right question is never "is this SUID?" It is:

> **Does this privileged program provide an *unintended* path to higher privileges?**

A program is dangerous when its intended function can be steered into doing something *outside* that function while holding root's power — for example, a SUID-root program that can be made to run an arbitrary command, read an arbitrary file, or write where it should not. A program is fine when it does exactly its one job and nothing more, even though it runs as root the whole time.

Enumeration, conceptually, means listing SUID programs and then **reasoning about each one's behaviour** — not pasting a command per binary. On a real system you would find SUID files with a permission search; on this platform there is no such surface to run against, so the skill here is the *reasoning*, and Lesson 3 gives you a SUID case to reason about rather than fabricated output.

## 6. SGID

**SGID** is the group-level analogue, and it behaves differently on files versus directories:

| SGID on a... | Effect |
|---|---|
| **file** (executable) | Runs with the privileges of the file's **group** (like SUID, but for the group identity) |
| **directory** | New files created inside **inherit the directory's group**, rather than the creator's primary group |

The directory behaviour is common and usually benign — it is how shared project directories keep a consistent group. The file behaviour matters for the same reason SUID does: an SGID-to-a-privileged-group program that can be steered outside its intended job may cross a boundary. Do not overcomplicate it: SGID is "SUID for groups," plus a convenient directory-inheritance trick.

## 7. Sudo

**sudo** runs a command with elevated privileges — *according to rules* defined in `/etc/sudoers`. It is the most-used and most-misconfigured elevation mechanism on Linux.

The key command is `sudo -l`: it lists what the current user is permitted to run through sudo. (This platform's terminal has no `sudo`, so the block below is illustrative.)

```
Illustrative example — not captured output. This platform's terminal does
not implement sudo or /etc/sudoers.

$ sudo -l
User student may run the following commands on this host:
    (root) NOPASSWD: /usr/bin/find
```

**Do not turn this into a copy-paste catalogue of "sudo X gives root" one-liners.** That teaches nothing and, worse, teaches the wrong instinct. Reason about the rule instead, with four questions:

| Question | For the example above |
|---|---|
| **What command is allowed?** | `/usr/bin/find` |
| **As whom may it run?** | root (`(root)`) |
| **Under what conditions?** | No password required (`NOPASSWD`) |
| **Can the allowed program do something *outside* its intended task while elevated?** | This is the whole question |

That last question is where the finding lives. Many everyday programs can be made to do far more than their headline purpose — a search tool that can execute a command for each result, an editor that can spawn a shell, a pager that can run commands, a language interpreter that can do anything. If such a program is allowed via sudo as root, then "run this program as root" quietly becomes "run *anything* as root."

So a dangerous sudo rule is one that grants, as a privileged user, a program whose capabilities exceed its apparent purpose. The professional writes the finding as *"the sudo rule permits `find` as root, and `find` can execute arbitrary commands, therefore the rule grants a root shell"* — the reasoning, not just the incantation. The fix, always, is **least privilege**: grant the narrowest possible command, avoid programs with escape hatches, and require a password.

## 8. Linux Capabilities

Historically Linux was binary: you were root (UID 0, all-powerful) or you were not. **Capabilities** break root's power into ~40 independent pieces, so a program can be granted *one* slice without being granted all of root.

A few, to make the idea concrete:

| Capability | The slice of root it grants |
|---|---|
| `CAP_NET_RAW` | Craft raw network packets (what `ping` needs) |
| `CAP_NET_ADMIN` | Configure networking — interfaces, routing, firewall rules |
| `CAP_DAC_OVERRIDE` | **Bypass file read/write/execute permission checks** |

Capabilities are a *good* security feature: giving `ping` just `CAP_NET_RAW` is far safer than making it SUID-root. The escalation angle is the mirror image: a capability on an **unexpected** program can be a boundary hole. `CAP_DAC_OVERRIDE` on a program you can influence effectively lets that program ignore file permissions — which is most of what root's file power *is*.

The reasoning is identical to SUID: the capability is not the vulnerability; the question is whether a program holding a powerful capability can be steered outside its intended job. On a real host you would enumerate capabilities with `getcap`; this platform does not simulate them, so — as with SUID — the skill is the reasoning, and nothing here fabricates `getcap` output. **Weaponised, real-world capability exploitation chains are deliberately out of scope**; the goal is to recognise a dangerous capability as a boundary worth investigating and reporting.

## 9. Scheduled Tasks (cron)

Systems run tasks on a schedule — backups, cleanups, log rotation — very often **as root**. A scheduled task is a boundary because *something runs, as a privileged user, without a human present.*

Ask the boundary questions of every scheduled job:

- **Who owns the job?** (Often root.)
- **Who can modify the script it runs?** — the decisive question.
- **Which user executes it?**
- **Is the script's path, or any directory in it, writable by you?**

The failure mode: a root-owned cron job that runs a script, where the **script itself** (or the directory containing it) is writable by an unprivileged user. Root runs the job on schedule; you control the script's contents; therefore you control what root does. The boundary between you and root has a hole, and it is *time-triggered* — you change the file, then wait for the schedule.

```
Illustrative example — not captured output. This platform's terminal does
not implement cron.

# /etc/crontab  (runs as root, every 5 minutes)
*/5 * * * * root /opt/scripts/backup.sh

$ ls -l /opt/scripts/backup.sh
-rwxrwxrwx 1 root root 214 backup.sh      ← world-writable, runs as root
```

That combination — root-executed, unprivileged-writable — is a confirmed-if-validated escalation path. A root-owned job running a root-owned, root-only-writable script is *sound*. Same surface, opposite conclusion, decided entirely by "who can modify it?" Keep every hands-on cron exercise inside authorized labs.

## 10. Services (systemd)

Long-running services are started and supervised by the init system (**systemd** on modern Linux) via **unit files**. Services frequently run as root or as dedicated service accounts.

The escalation angles mirror cron, because a service is also "code that runs, often privileged, without you":

- **Writable unit file** — if you can edit the file that defines *how a service starts*, you can change what runs when it (re)starts, as whatever user the service runs as.
- **Writable executable or config** — if the service is root but loads a binary or configuration file you can modify, you can influence privileged behaviour.
- **Weak service-account boundaries** — a service running as root when a limited service account would do enlarges the blast radius of any flaw in it.

The remediation vocabulary: run services under **dedicated, least-privileged service accounts**, not root; protect unit files, service binaries and configs so only root can modify them. As everywhere, the reasoning — *who controls what this privileged process loads?* — is the point, not a catalogue of unit-file tricks. This platform does not simulate systemd, so the reasoning is illustrated, not run.

## 11. PATH and Search Order

When a program runs a command **without an absolute path** — `backup` instead of `/usr/bin/backup` — the shell searches the directories in the `PATH` environment variable, **in order**, and runs the first match.

Now combine that with a privileged process:

- A **root** script calls `backup` (no absolute path).
- Its `PATH` includes a directory **you** can write to, listed *before* the real one.
- You place a file named `backup` in that directory.
- Root runs *your* file, as root.

That is a **PATH hijack**, and the root cause is a privileged process making unsafe assumptions about search order. The defensive lesson is concrete: privileged scripts should call commands by **absolute path** and set a known-safe `PATH`. The finding is written as *"the root cron job calls `backup` without an absolute path and its PATH includes the writable `/opt/bin`."* This platform does not run privileged scripts, so — again — the mechanism is illustrated, not a persistence workflow, and it is out of scope to build one.

## 12. Writable Files and Directories

This section exists to correct the single most common beginner error, so it is blunt:

> **A file being writable is not a vulnerability.**

Writability only matters in combination. Ask:

- **Who executes or reads it?**
- **Under what privileges?**
- **When?**
- **Can your modification actually influence privileged behaviour?**

A world-writable file in `/tmp` that no privileged process ever touches is *nothing*. A world-writable script that root runs every five minutes is a *confirmed-if-validated escalation path*. **Same permission bits; completely different findings — the difference is what consumes the file.** Internalising this is what turns an "interesting finding" into a defensible one, and it is exactly the distinction §14 formalises.

## 13. Environment, Kernel and Containers

Three surfaces to know at the right altitude.

**Environment and configuration.** Boundaries can be weakened by more than file bits: a secret left in a world-readable config or environment variable, a writable application config that a privileged process trusts, an insecure default. The reasoning is unchanged — *can something I control influence something privileged?* (Harvesting credentials from real systems is **not** taught here; recognising an exposed-secret *boundary* is.)

**Kernel vulnerabilities.** The kernel enforces every permission check, so a flaw *in the kernel* can cross any boundary — the strongest and riskiest class of escalation. The professional workflow is: note the kernel version and patch level, research whether known issues affect *this specific build*, and confirm against vendor advisories.

> A matching kernel version does **not** prove exploitability. The specific build, configuration, mitigations and patch level all decide it, and kernel exploits are precisely the ones most likely to crash the host. Weaponised kernel-exploit instructions are out of scope; the skill is disciplined version-and-patch reasoning.

**Containers.** A container is *not* automatically a lightweight VM — it shares the host kernel and is isolated by kernel features, not by a hardware boundary. Certain misconfigurations (an over-privileged container, a mounted host filesystem, a mounted container-runtime socket) weaken that isolation and can let container access reach the host. Detailed container-breakout technique belongs to later, gated content; here, the point is conceptual: *containers are a boundary, and a privileged container is a weakened one.*

## 14. Finding vs Confirmed Escalation Path

This is the most important idea in the module. Say it out loud:

> **A finding is not a confirmed escalation path.**

A **finding** is an observation: "user can modify `/opt/app/config.ini`." It is interesting. It is **not** the same as "user can become root." To get from one to the other you must answer:

1. **Who consumes `config.ini`?**
2. **With what privileges?**
3. **Can modifying it actually influence privileged execution?**
4. **Can that influence be demonstrated, safely, on an authorized target?**

```
FINDING:  "student can write /opt/app/config.ini"
                    │
        ┌───────────┴───────────┐
        ▼                        ▼
 root reads it on start   nothing privileged
 → boundary MAY fail      ever reads it
 → validate carefully     → NOT an escalation path
                            → report as hygiene, not escalation
```

Both branches are legitimate outcomes. A writable file that no privileged process consumes is real, and the honest report says "writable config, but not an escalation path — no privileged consumer found." Confusing the two — reporting every writable file as "root compromise" — is how testers lose credibility. The whole of Lesson 3's final exercises live on this distinction.

## 15. Prioritisation

Real enumeration produces *many* observations. You do not "try everything" — that is noisy, risky, and unprofessional. You prioritise, along axes like:

| Axis | The question |
|---|---|
| **Privilege gained** | Does this reach root, or one step sideways? |
| **Exploitability** | How much has to be true for it to work? |
| **Reliability** | Will it work once, or every time? |
| **Impact** | What does crossing this boundary actually give access to? |
| **Reachability** | Can you even reach the component from your position? |
| **Preconditions** | Does it need a service running, a schedule to fire, a specific state? |

A world-writable root cron script (reliable, root, low preconditions) outranks a theoretical kernel flaw (unreliable, high risk, may crash the host). Prioritisation is judgment, and it is what "try everything" replaces with luck.

## 16. Validation

When a finding *looks* like a path, validate it — minimally and safely:

1. **Identify the weakness** precisely.
2. **Understand why it exists** — which boundary, misconfigured how.
3. **Confirm the affected component** — the exact file, rule, job or service.
4. **Determine the expected boundary** — what *should* the privilege separation be?
5. **Perform minimal safe validation** — the smallest action that demonstrates the boundary can be crossed, nothing destructive.
6. **Confirm the actual privilege change** — show the new context (e.g. `id` now reporting a different UID), don't assume it.
7. **Record evidence** (§17).
8. **Stop.** You have proven the finding. Going further — persistence, damage, roaming — is out of scope and unprofessional.

"Minimal and safe" is doing the least that *proves* the boundary is broken. You are demonstrating a fact for a report, not seizing a system.

## 17. Evidence

A finding you cannot reproduce is an anecdote. Record:

| Field | Content |
|---|---|
| **Current user** | Who you were (`whoami` / `id`) before |
| **Current groups** | Your memberships |
| **Affected component** | The exact file / rule / job / service |
| **Ownership** | Who owns it |
| **Permissions** | The exact bits |
| **Configuration** | The relevant rule or unit content |
| **Expected privilege** | What the boundary was *supposed* to enforce |
| **Observed privilege** | What you could *actually* do |
| **Evidence** | The commands and their real output |
| **Impact** | What crossing it grants, in the owner's terms |
| **Remediation** | The fix, and how to verify it |

The pair that carries the most weight is **expected vs observed**. "The boundary should have kept `student` out of a root-only file; after crossing it, `id` reported UID 0" is a finding. "I got root" is a boast.

## 18. Remediation

Every surface connects to a defence. This is the half that makes a test worth paying for.

| Surface | Remediation |
|---|---|
| **SUID/SGID** | Remove the bit where it is not needed; audit remaining ones for escape-capable programs |
| **Sudo** | Least privilege — narrowest command, no escape-capable programs, require a password |
| **Writable privileged file** | Restrict ownership and permissions so only the privileged user can modify it |
| **Cron** | Protect scripts and their directories from unprivileged modification; use absolute paths |
| **Services** | Dedicated least-privileged service accounts; protect unit files, binaries and configs |
| **Capabilities** | Remove unnecessary capabilities; never grant powerful ones to steerable programs |
| **PATH** | Absolute paths in privileged scripts; a known-safe PATH |
| **Kernel** | Patch supported systems to a fixed level |
| **Groups** | Remove unnecessary privileged memberships (`sudo`, `docker`, `disk`, …) |

Notice the theme: nearly every fix is **least privilege** — grant the minimum, to the fewest, for the narrowest task. Escalation findings are, almost always, least-privilege failures. And the final step is always **retest**: re-run the exact validation and confirm the boundary now holds.

## 19. Correcting Some Common Misconceptions

**WRONG:** "Any writable file means root."
**CORRECT:** Writability only matters if a privileged process reads or runs the file. No privileged consumer, no escalation.

**WRONG:** "SUID automatically means vulnerable."
**CORRECT:** SUID indicates an elevated execution context. Vulnerability depends on whether the program can be steered outside its intended job while elevated.

**WRONG:** "sudo means root."
**CORRECT:** sudo grants exactly what its rules allow. `sudo -l` shows the rule; the finding depends on what the permitted program can be made to do.

**WRONG:** "A matching kernel version equals an exploit."
**CORRECT:** A version is a lead. Exploitability depends on the build, configuration, mitigations and patch level — none proven by the version string.

**WRONG:** "Enumeration is boring preparation."
**CORRECT:** Enumeration is how boundaries are discovered. It is the work, not the warm-up.

**WRONG:** "Getting a shell means complete compromise."
**CORRECT:** The shell's privilege level decides what is possible. `id` tells you where you stand.

**WRONG:** "Privilege escalation means hacking root immediately."
**CORRECT:** It means validating a specific boundary — possibly vertical to root, possibly horizontal to another user — and proving it.

## 20. Exercises

**Exercise 1 — Group leads.**
Your `id` shows membership in `sudo`, `adm` and `docker`. For each, state what it *might* grant and what you would check before claiming it grants anything.

**Exercise 2 — SUID reasoning.**
Two SUID-root programs: one only prints the current time; one can open an interactive editor. Which deserves investigation, and why? What is the precise question you are asking of it?

**Exercise 3 — Read the sudo rule.**
Given `(root) NOPASSWD: /usr/bin/find`, walk the four sudo questions and state the finding in one sentence of reasoning (not a command).

**Exercise 4 — Same bits, different finding.**
A file is `-rwxrwxrwx root root`. Describe one situation where this is a confirmed-if-validated escalation path and one where it is harmless. What single fact decides it?

**Exercise 5 — Prioritise.**
You have four findings: a world-writable root cron script; membership in `adm`; a kernel version with a *rumoured* flaw; a writable file in `/tmp` nothing reads. Rank them and justify the top and bottom.

**Exercise 6 — Validate and stop.**
You believe a writable root-run script is an escalation path. Write the minimal, safe validation that would *prove* it, the exact evidence you would capture, and the point at which you stop.

## 21. Knowledge Check

1. **What do Linux file permissions control?**
   For owner, group and others: read, write and execute — meaning contents-vs-listing, modify-vs-manage-entries, and run-vs-traverse for files vs directories. They are the primary expression of a file-level privilege boundary.

2. **What is SUID, and why isn't every SUID binary a vulnerability?**
   SUID makes a program run as its *owner* rather than its caller — often root. It is a vulnerability only if the program can be steered to do something outside its intended job while elevated. The bit indicates elevated context, not a flaw.

3. **What is the difference between SUID and SGID?**
   SUID runs a program with its owner's identity; SGID runs it with its *group's* identity, and on a directory causes new files to inherit the directory's group. "SUID for groups," plus directory group-inheritance.

4. **What does `sudo -l` help identify, and how should you reason about a rule?**
   It lists what you may run via sudo. Reason with four questions: what command, as whom, under what conditions, and can the permitted program act outside its intended task while elevated? The last one is where the finding is.

5. **Why can a dangerous sudo rule create an escalation path?**
   Because many programs can do far more than their headline purpose — execute commands, spawn shells, read/write arbitrary files. Permitting such a program as root turns "run this program as root" into "run anything as root."

6. **What are Linux capabilities?**
   Independent slices of root's power (~40 of them), so a program can hold one privilege without holding all of root. Powerful capabilities (e.g. `CAP_DAC_OVERRIDE`) on a steerable program are a boundary worth investigating.

7. **Why can a privileged scheduled task be dangerous?**
   A cron job often runs as root without a human present. If the script it runs — or its directory — is writable by an unprivileged user, that user controls what root executes, on a timer.

8. **Why can writable configuration become a privilege issue?**
   Only if a privileged process consumes it. If root reads a config on startup and you can write that config, you can influence privileged behaviour. Writable-and-privileged is the combination that matters.

9. **Why can unsafe PATH resolution matter?**
   If a privileged process runs a command without an absolute path and its PATH includes a directory you can write to, you can place a matching file that root runs instead of the intended program.

10. **Why doesn't a matching kernel version prove exploitability?**
    Because the specific build, configuration, mitigations and patch level determine whether a flaw is present and usable. The version is a lead; kernel exploits are also the ones most likely to crash the host.

11. **What evidence proves privilege escalation?**
    A demonstrated change of privilege context — for example `id` reporting a different (higher) UID after a minimal, safe validation — recorded alongside the expected-vs-observed boundary and the exact commands used. Not a claim, a reproduction.

12. **Why is remediation part of privilege-escalation testing, and what is the recurring fix?**
    Because the deliverable is a fix the owner can apply and verify, not a boast. The recurring remediation is least privilege — grant the minimum, to the fewest, for the narrowest task — followed by a retest of the exact validation.

---

**Next:** *Hands-on Practice* — real enumeration against an authorized training host, seven exercises that separate findings from confirmed paths, a deliberately *failed* escalation to reason about, and a professional finding written from real output.
