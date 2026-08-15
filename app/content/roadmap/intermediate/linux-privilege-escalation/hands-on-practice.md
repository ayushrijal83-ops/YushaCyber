# Linux Privilege Escalation — Hands-on Practice

## 1. Authorization First

Everything below happens against **YushaCyber's authorized training environment** — the simulated Linux host in this platform's terminal and the **Linux Permissions** mission. Nothing here touches a real machine.

**Do not repeat any of this against a system you do not own or do not have written permission to test.** Privilege escalation deliberately makes a system grant authority it was configured to withhold; doing that uninvited is intrusion, not testing, and a misconfigured boundary is not a defence.

**What this lesson is:** structured practice in the *reasoning* of Linux privilege escalation — establishing your position, enumerating a host, examining boundaries with four questions, separating a finding from a confirmed path, validating minimally, and writing it up.

**What this lesson is not:** an exploit cookbook, and not an introduction to persistence, stealth, credential theft against real systems, or lateral movement. Those are later, gated subjects.

## 2. What Is Real Here, and What Is Illustrated — Read This First

Being exact about the environment matters more than looking impressive.

This platform's terminal runs **identity and permission commands for real**: `whoami`, `id`, `groups`, `uname`, `hostname`, `ls -l`, `cat`, `chmod`, `chown`, `find`, `grep`. Every block below tagged **REAL OUTPUT** was captured by actually running the command against the authorized training host.

It has **no** `sudo`, no SUID bits, no `getcap`, no `cron`, no `systemctl`, no `ps`. So the sudo, SUID and scheduled-task exercises teach *reasoning* with blocks tagged **ILLUSTRATIVE EXAMPLE**. Those are never presented as captured output.

| In this lesson | Status |
|---|---|
| `whoami` / `id` / `groups` / `uname` / `hostname` output | **REAL OUTPUT** — from the training host |
| `ls -l`, `cat`, `chmod`, `chown` in the Linux Permissions mission | **REAL OUTPUT** |
| The Linux Permissions mission itself (§15) | **REAL** — an existing terminal mission you can complete for XP |
| Any `sudo -l`, SUID listing, `getcap`, `crontab` block | **ILLUSTRATIVE EXAMPLE** — labelled every time; this platform does not implement these |

One honesty note called out where it happens: the mission lets you `chown` a root-owned file to yourself. **On real Linux `chown` is itself a root-only operation** — a normal user cannot take ownership of root's file. The mission permits it to demonstrate the *concept* that ownership is a boundary; §11 flags exactly where the simulation diverges from real Linux, because knowing that difference is part of the skill.

## 3. The Environment

You begin as an unprivileged user on the training host. Establish position — **REAL OUTPUT**:

```
whoami
student

id
uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)

hostname
yushacyber-lab
```

You are `student`, UID 1000 — not root. You are a member of the `sudo` group (a lead, per Core Concepts §7). The **Linux Permissions** mission provides a small directory of files with deliberately varied ownership and permission bits, which is what the exercises below examine.

## 4. The Reasoning Shape

Answer every exercise in the same six parts. This is what makes a conclusion checkable by someone else:

```
OBSERVATION          what you saw
EVIDENCE             the exact command + output that supports it
INTERPRETATION       what it means — and what it does NOT
DECISION             what you do next, and why
CONFIDENCE           high / medium / low, with the reason
WHAT WOULD CHANGE IT the evidence that would overturn your conclusion
```

That last line is the discipline. A conclusion nothing could overturn is an assertion, not analysis.

## 5. Exercise 1 — Identify Your Current Identity

**Objective:** fix your exact position before touching anything.

**REAL OUTPUT:**
```
whoami
student

id
uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)

groups
student sudo
```

**Do this:**
1. State your username, UID and primary group.
2. List **every** group you belong to.
3. Identify the one group here that is a **lead** worth investigating, and say why it is a lead and not a conclusion.
4. Write the six-part record.

**Worked partial answer:**
> OBSERVATION: I am `student`, UID 1000, primary group `student`, and also a member of `sudo`.
> EVIDENCE: `id` → `uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)`.
> INTERPRETATION: UID 1000 means I am not root. Membership in `sudo` *may* allow running commands via sudo — but only if a usable rule exists in `/etc/sudoers`, which I have not confirmed.
> DECISION: Note `sudo` membership as the highest-priority lead; enumerate the host before acting on it.
> CONFIDENCE: High for the identity facts; the `sudo` lead is unconfirmed.
> WHAT WOULD CHANGE IT: A `sudo -l` result showing no permitted commands would demote the lead to nothing.

**What you cannot conclude:** that `sudo` membership makes you root. It is a question, not an answer.

## 6. Exercise 2 — Enumerate the Host

**Objective:** build the picture that frames what is plausible.

**REAL OUTPUT:**
```
uname -a
Linux yushacyber-lab 5.15.0 #1 SMP x86_64 GNU/Linux

hostname
yushacyber-lab

cat /etc/passwd
root:x:0:0:root:/root:/bin/bash
student:x:1000:1000::/home/student:/bin/bash
```

**Do this:**
1. Record OS, kernel version and architecture.
2. Record the hostname (findings must name their host).
3. From `/etc/passwd`, list every account and its UID. Which account is root, and how do you know from this output alone?
4. The kernel is `5.15.0`. Write the one-sentence rule about what a kernel version does and does not prove.

**Checks:**
- Did you identify root by its **UID (0)** in the third field, not by its name? A second UID-0 account would itself be a finding.
- Your kernel sentence should say a version is a **lead**, never proof — exploitability depends on the specific build, mitigations and patch level.

**What you cannot conclude:** that kernel `5.15.0` is exploitable. You have a lead to research against vendor advisories, nothing more.

## 7. Exercise 3 — Analyse Permissions

**Objective:** apply the four boundary questions to real objects.

Inside the mission's `permissions` directory — **REAL OUTPUT:**
```
cd permissions

ls -l
total 3
----------  1 student student     50  Jan  5 08:00  challenge.txt
-rw-------  1 root root     84  Jan  5 08:00  private.txt
-rw-r--r--  1 student student     71  Jan  5 08:00  public.txt
```

And the boundary in action — **REAL OUTPUT:**
```
cat public.txt
Anyone can read this file. Permissions are your first line of defense.

cat private.txt
cat: private.txt: Permission denied
```

**Do this — for `private.txt`, walk the four questions:**

| Question | Answer for `private.txt` |
|---|---|
| Who owns it? | |
| Who can modify it? | |
| Who executes it? | |
| With what privileges? | |

Then decide: **is this boundary sound or broken?** Justify it with the `cat private.txt` result.

**Worked answer:**
> Owner: root. Modifiable by: root only (`-rw-------` — nothing for group or others). Executed by: nobody, it is data. Privileges: N/A.
> This boundary is **sound**. `private.txt` is root-owned and root-only; as `student` I cannot even read it, and the system enforced that — `cat private.txt` returned `Permission denied`. There is no escalation here. Recognising a *sound* boundary is a real, professional outcome — "no finding" is a valid result.

**Now `challenge.txt`** (`---------- student student`, mode 000): you *own* it but its bits grant nobody anything. Ask the four questions and explain why you can still change its permissions even though the bits say `---` (hint: ownership, not the current bits, controls who may `chmod`).

**The key lesson:** most of enumeration is examining boundaries and concluding "this one is fine." The `private.txt` denial is a boundary working correctly — exactly what you want to be able to recognise before you go hunting for one that is broken.

## 8. Exercise 4 — Analyse Sudo

**Objective:** reason about a sudo rule. This platform has no `sudo`, so the reasoning is the exercise — it transfers exactly.

Your real `id` output showed `sudo`-group membership. On a real host the next step is `sudo -l`:

```
ILLUSTRATIVE EXAMPLE — not captured output. This platform's terminal does
not implement sudo or /etc/sudoers.

$ sudo -l
User student may run the following commands on this host:
    (root) NOPASSWD: /usr/bin/find
```

**Do this — walk the four sudo questions:**
1. What command is allowed?
2. As whom may it run?
3. Under what conditions?
4. Can the permitted program act **outside** its intended task while elevated?

**Expected reasoning:**
> `find` is permitted as root with no password. `find` is not only a search tool — it can execute a command for each result. A program that can run arbitrary commands, permitted as root, means "run `find` as root" becomes "run anything as root." This is a **confirmed-if-validated vertical escalation path** via a misconfigured sudo rule. Finding, in one sentence: *the sudoers rule grants `find` as root, and `find` can execute arbitrary commands, so the rule effectively grants a root shell.* Remediation: least privilege — do not grant escape-capable programs via sudo; require a password; narrow the command.

**Do not** reduce this to a memorised one-liner. The finding is the *reasoning* about what the program can do — that reasoning transfers to any permitted program; a memorised incantation does not.

## 9. Exercise 5 — Analyse SUID

**Objective:** reason about an SUID program without confusing the bit for the vulnerability.

```
ILLUSTRATIVE EXAMPLE — not captured output. This platform's terminal does
not simulate SUID bits.

-rwsr-xr-x  1 root root   68208  /usr/bin/passwd
-rwsr-xr-x  1 root root   35048  /usr/bin/custombackup
```

**Do this — for each program, answer:**
1. Who owns it, and what does the `s` bit mean here?
2. Why might SUID legitimately be present?
3. Is the elevated context *expected* for this program's job?
4. Can its behaviour cross a privilege boundary?

**Expected reasoning:**
> `passwd` is SUID-root because changing a password requires writing `/etc/shadow`, which only root may do. Its elevated context is *expected and bounded* — it does one job. It is not, on its own, a finding.
> `custombackup` is a non-standard SUID-root program. The elevated context may or may not be justified, and "custom" means it has not had decades of scrutiny. The question to investigate: can it be made to do something outside "backup" — run a command, read/write an arbitrary path — while holding root? Until that is answered it is an **interesting finding**, not a **confirmed path**.

The discipline: the SUID bit indicates an elevated *execution context*, never a vulnerability by itself. The finding lives in the program's *behaviour*.

## 10. Exercise 6 — Scheduled Task / Service

**Objective:** reason about time- and boot-triggered privileged execution.

```
ILLUSTRATIVE EXAMPLE — not captured output. This platform's terminal does
not implement cron or systemd.

# /etc/crontab
*/5 * * * * root /opt/scripts/backup.sh

$ ls -l /opt/scripts/backup.sh
-rwxrwxrwx 1 root root 214 backup.sh
```

**Do this — answer:**
1. Who runs the job?
2. Who controls the script it executes?
3. Can an unprivileged user influence what root runs?
4. Is this a sound boundary or a broken one?

**Expected reasoning:**
> The job runs as **root** every five minutes. The script `backup.sh` is **world-writable** (`-rwxrwxrwx`), so any user — including `student` — can change its contents. Therefore an unprivileged user controls what root executes on a timer. The boundary between `student` and root has a hole. This is a **confirmed-if-validated vertical escalation path**. Contrast: if the same job ran a root-owned, root-only-writable script (`-rwxr-xr-x root root`), the boundary would be **sound**. The single deciding fact is "who can modify it?"

Keep any real hands-on cron work inside authorized labs. The mechanism above is illustrative — the platform does not run privileged jobs, and building a persistence workflow is out of scope.

## 11. Exercise 7 — Validate One Finding (and where the simulation diverges)

**Objective:** demonstrate a boundary being crossed — minimally — and be honest about what the demonstration proves.

The mission includes a real, crossable boundary: `private.txt` is root-owned and you cannot read it. The mission's next objective is to take ownership. **REAL OUTPUT:**

```
cat private.txt
cat: private.txt: Permission denied

chown student private.txt

ls -l private.txt
-rw-------  1 student student     84  Jan  5 08:00  private.txt

cat private.txt
Only the owner should be able to read this. If you can see this, ownership matters.
```

Before you write this up as an escalation, **stop and think about what it actually proves** — this is the most important habit in the lesson:

> **On real Linux, `chown` is a root-only operation.** A normal user *cannot* take ownership of a file owned by root. The mission permits it to teach the *concept* that ownership governs access — and it does teach that concept truthfully: once you owned the file, you could read it, so ownership was the boundary. But the *act* of taking ownership is a **simulation affordance, not a real escalation**. On a real host this exact step would fail with `chown: changing ownership of 'private.txt': Operation not permitted`.

So the honest finding here is **not** "student escalated to read a root file." It is:

> OBSERVATION: `private.txt` (root-owned, mode 600) correctly denied `student` read access.
> EVIDENCE: `cat private.txt` → `Permission denied` (REAL).
> INTERPRETATION: The file-ownership boundary is **sound**. The subsequent `chown` demonstrates the *concept* that ownership controls access, but relies on a simulation affordance — real Linux would reject a non-root `chown`, so this is not a real escalation path on a real host.
> DECISION: Record the boundary as sound; note the simulation's divergence from real `chown` semantics.
> CONFIDENCE: High.
> WHAT WOULD CHANGE IT: On a real host, evidence that `student` could chown root's file (which would itself indicate a serious misconfiguration or a broken system).

That is the discipline the whole module is built on: **know real Linux semantics, and do not let a lab's affordances tell you a boundary is broken when it is not.** A confirmed escalation path (the sudo-`find` and world-writable-cron examples above) is one you could reproduce on a real, authorized host — not one that only works because the simulator allows it.

## 12. The Failed Escalation

**Objective:** internalise that a finding can exist with no successful escalation — the most valuable habit for accuracy.

Consider a writable file — say `/opt/app/notes.txt`, mode `-rw-rw-rw-`, that you can clearly modify.

**The reasoning:**
1. **Finding:** `student` can write `/opt/app/notes.txt`. True and worth noting.
2. **The decisive question:** who *consumes* this file, and with what privileges?
3. **Suppose the answer is: nothing.** No root process reads it, no scheduled job runs it, no service loads it. It is a text file some application wrote once.
4. **Conclusion:** writable, but **not** an escalation path. There is no privileged consumer, so modifying it changes nothing you care about.

Report this honestly: *"World-writable file `/opt/app/notes.txt`; no privileged consumer identified — a permissions-hygiene issue, not an escalation path."* Reporting it as "root compromise" would be wrong, and reporting nothing at all would miss a real (if minor) hygiene finding.

**Same discipline, applied to `private.txt` above:** the boundary held; there was no real escalation; the honest write-up says so. A tester who reports every writable file and every sound boundary as "root" loses credibility fast. **Enumeration is not exploitation, and an interesting configuration is not a confirmed path.**

## 13. Professional Finding

**Objective:** produce the deliverable. Every field must be supported by evidence — real where the platform provides it, clearly-labelled illustrative where it does not.

Template:
```
Title:
Affected component:
Current privilege:
Potential privileged context:
Root cause:
Evidence:
Impact:
Severity:
Remediation:
Validation after remediation:
```

### Worked finding (ILLUSTRATIVE — the world-writable cron case from §10)

```
Title:                 Weak Privilege Boundary — root cron job runs a
                       world-writable script

Affected component:    /opt/scripts/backup.sh, executed by /etc/crontab as root
                       every 5 minutes

Current privilege:     student (UID 1000), member of group sudo

Potential privileged
context:               root (UID 0) — the user the cron job runs as

Root cause:            The script executed by a root-owned cron job is
                       world-writable (-rwxrwxrwx). Any user can change what
                       root executes.

Evidence:              ILLUSTRATIVE — /etc/crontab shows "*/5 * * * * root
                       /opt/scripts/backup.sh"; ls -l shows -rwxrwxrwx root root.
                       (This platform does not implement cron; on a real
                       authorized host this would be captured output.)

Impact:                Full vertical escalation from an unprivileged user to
                       root, on a 5-minute timer, reliable and low-precondition.

Severity:              High — reliable path to root.

Remediation:           Restrict the script to root-only write
                       (chmod 755, chown root:root); protect its directory;
                       have the job call commands by absolute path.

Validation after
remediation:           Re-check: ls -l shows -rwxr-xr-x root root; an
                       unprivileged user can no longer modify the script;
                       re-run the escalation attempt and confirm it fails.
```

### Real finding from this platform (the sound boundary)

```
Title:                 File-ownership boundary — root-owned private file
                       correctly protected (NO escalation)

Affected component:    ~/permissions/private.txt

Current privilege:     student (UID 1000)

Potential privileged
context:               n/a — boundary held

Root cause:            n/a — correctly configured (root:root, mode 600)

Evidence:              REAL — cat private.txt → "cat: private.txt: Permission
                       denied"; ls -l → -rw------- root root private.txt

Impact:                None. The boundary enforced as intended.

Severity:              Informational.

Remediation:           None required. (Documented as a control that works.)

Validation:            n/a
```

Note what the two together demonstrate: **most professional findings are one of these two shapes** — a specific, reproducible, remediable boundary failure, or an honest "boundary held, no escalation." Neither is a copy-paste exploit.

## 14. Common Mistakes

| Mistake | Why it is wrong |
|---|---|
| Searching for a kernel exploit first | Boundaries are found by enumeration; a version is a lead, and kernel exploits are the most likely to crash the host |
| "I have a shell, so I'm compromised the box" | A shell is a *position*. `id` says UID 1000 here — the starting line |
| Treating `sudo`-group membership as root | It is a lead; whether it elevates depends on `/etc/sudoers` |
| "It's SUID, so it's vulnerable" | SUID is an elevated *context*; the finding is in the program's behaviour |
| Reporting every writable file as root | Writable matters only with a privileged consumer |
| Trusting a lab affordance as a real escalation | The `chown` step works in the simulator but would fail on real Linux — know the difference |
| Skipping the expected-vs-observed record | Without a stated expected boundary, a result proves nothing specific |
| Stopping at "we got root" | The deliverable is the finding: evidence, impact, remediation, retest |

## 15. Real Practice on This Platform

**What you can actually run here.** The **Linux Permissions** terminal mission (`/terminal/mission/linux-permissions`) runs the exact host these exercises quote. Its objectives walk the enumeration and permission/ownership half of this module directly:

- read permission notation with `ls -l`
- identify yourself with `whoami`, `id`, `groups`
- hit a real permission boundary — `cat private.txt` is denied
- change permissions with `chmod`
- change ownership with `chown` (the concept demonstration flagged in §11)

Those are the first, foundational rungs of privilege-escalation enumeration — *establish position, read boundaries, watch one enforce itself* — and they are **real** here. The identity commands (`whoami`/`id`/`groups`/`uname`/`hostname`) also work in the bare **free-practice terminal** (`/terminal`) with no mission attached, so you can rehearse Exercises 1 and 2 there directly.

**What you cannot run here, stated plainly:** there is no `sudo`, SUID, capability, cron or systemd simulation on YushaCyber, so Exercises 4, 5 and 6 are reasoning exercises with illustrative examples, not captured output. To practise those surfaces against a real, deliberately-vulnerable target you need your own **authorized** lab — a virtual machine you built, on a network you own. The **Virtualization** module (Beginner track) is the groundwork for exactly that.

## 16. Where This Goes Next

```
Linux Privilege Escalation (here) →  crossing Linux boundaries, with evidence
Reconnaissance / Enumeration      →  finding the surface at engagement scale
Exploitation                      →  gaining the initial position
Active Directory Attacks          →  the same reasoning across a Windows domain
Persistence / Evasion             →  keeping and hiding access (later, gated)
```

Every one assumes what this module built: that you can establish your position, enumerate a host, examine a boundary with four questions, tell a finding from a confirmed path, validate minimally on an authorized target, and write it up so an administrator can fix it.

## 17. Knowledge Check

1. **Why do you run `whoami`/`id`/`groups` before anything else?**
   To fix your exact position — UID, primary group, every supplementary group. Everything downstream is measured from it, and group memberships (like `sudo` here) are the first leads.

2. **The real `id` output shows `sudo`-group membership. Is that root?**
   No. It is a lead. Whether it grants elevation depends on the rules in `/etc/sudoers`, which must be investigated, not assumed.

3. **In the real `ls -l`, `private.txt` is `-rw------- root root`. Sound or broken?**
   Sound. It is root-owned and root-only; `student` cannot even read it, and the system enforces that (`Permission denied`). Recognising a working boundary is a real professional outcome.

4. **Why is the mission's `chown` step not a real escalation?**
   Because on real Linux `chown` is root-only — a normal user cannot take ownership of root's file. The mission permits it to teach that ownership is a boundary; the *act* is a simulation affordance, and on a real host it would fail with "Operation not permitted."

5. **What single fact decides whether a world-writable file is an escalation path?**
   Whether a privileged process consumes it. Writable-and-privileged is a path; writable-with-no-privileged-consumer is a hygiene note.

6. **How do you reason about a sudo rule like `(root) NOPASSWD: /usr/bin/find`?**
   Four questions: what command, as whom, under what conditions, and can it act outside its intended job while elevated? `find` can execute arbitrary commands, so permitted-as-root it grants a root shell.

7. **Why isn't a non-standard SUID-root program automatically a finding?**
   The SUID bit indicates elevated context, not a flaw. It becomes a finding only if the program can be steered outside its intended job while holding root.

8. **What makes a root cron job dangerous?**
   If the script it runs (or that script's directory) is writable by an unprivileged user, that user controls what root executes on a timer. A root-owned, root-only-writable script is sound.

9. **What does the kernel version `5.15.0` tell you?**
   That you have a lead to research against vendor advisories — nothing more. Exploitability depends on the build, mitigations and patch level, and kernel exploits risk crashing the host.

10. **What evidence proves privilege escalation?**
    A demonstrated change of privilege context (e.g. `id` reporting a higher UID after a minimal, safe validation), recorded with the expected-vs-observed boundary and the exact commands — reproducible on a real authorized host, not reliant on a simulator affordance.

11. **Why report a "boundary held, no escalation" finding at all?**
    Because honesty and completeness are the deliverable. Documenting a working control, and separating it from real weaknesses, is what makes the rest of the report credible.

12. **Why must all of this stay on authorized targets?**
    Because escalation makes a system grant authority it was configured to withhold. Off an authorized target that is intrusion — the misconfiguration is not a defence, and authorization is what makes it a test.

---

**Module complete.** You can now establish your position on a Linux host, enumerate it methodically, examine any privilege boundary with four questions, distinguish an interesting finding from a confirmed escalation path, validate one minimally and honestly on an authorized target, tell a real escalation from a simulator affordance, and write a finding an administrator can act on.
