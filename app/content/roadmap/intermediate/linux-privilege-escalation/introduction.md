# Introduction to Linux Privilege Escalation

## 1. What You Will Learn

By the end of this lesson you should be able to:

- define **privilege escalation** precisely, and say what it is *not*
- distinguish **vertical** from **horizontal** escalation, with an example of each
- explain the Linux identity model — **user**, **group**, **root** — well enough to reason about it
- explain *why* privilege escalation exists: it is a **misconfigured or vulnerable boundary**, not magic
- state, and mean, that **a shell is not root**
- explain why a professional **enumerates before exploiting**, and what enumeration actually asks
- read the output of the core identity commands and say what each one tells you about your position
- adopt the module's central mental model: the **privilege boundary**, examined with four questions

## 2. Why This Matters

By this point in the Intermediate track you can get *in*. **Nmap** finds services, **Burp** and **OWASP** break down web applications, **Metasploit** frames controlled, authorized initial access, and **Windows Privilege Escalation** taught the same reasoning on the other operating system. Almost none of that lands you as an administrator. It lands you as *somebody* — a low-privilege web service account, a limited user, a restricted shell.

Privilege escalation is the discipline of answering one question honestly:

> **From where I am now, does a legitimate path exist to higher privileges — and can I prove it without guessing?**

That word *prove* is the whole module. This is not a collection of magic commands you paste until a root prompt appears. It is a way of reading a system: finding the places where Linux's own rules about who-can-do-what have been set up incorrectly, understanding *why* each one is a boundary, and demonstrating — carefully, on an authorized target — that the boundary can be crossed. A tester who can do that produces a finding an administrator can act on. A tester who pastes commands until something works produces noise, and often an outage.

## 3. Authorization and Scope

Read this before anything else in the module.

**Everything you practise happens inside YushaCyber's authorized training environment** — a simulated Linux host modelled in this platform's terminal, which has never touched a real machine. Nothing here may be repeated against a system you do not own or do not have **written** permission to test.

This is not a footnote. Privilege escalation, by definition, tries to make a system grant you authority it was configured to withhold. On someone else's system that is not testing — it is intrusion, and the fact that a boundary was misconfigured is not a defence. Authorization is what separates a penetration test from a crime.

Two more scope statements, both honest:

- **This module teaches reasoning, not a payload catalogue.** It deliberately does **not** teach persistence, stealth or evasion, credential theft against real systems, or lateral movement. Those are separate, later, gated subjects. Escalating a boundary and then *hiding* that you did are different skills, and only the first belongs here.
- **The platform cannot simulate every surface**, and Lesson 3 says exactly which parts are real and which are illustrated. You will never be shown a fabricated root shell and told it was captured. Where the platform can run something, you run it; where it cannot, you get the reasoning and a clearly-labelled example.

## 4. What Privilege Escalation Is

**Privilege escalation is when a user obtains privileges beyond those they were intended to have.**

Take that apart:

- **"intended to have"** — every account on a Linux system is *supposed* to be able to do certain things and not others. That intention is expressed through ownership, permissions, group membership, sudo rules, and so on.
- **"obtains privileges beyond"** — escalation is the gap between what you were supposed to be able to do and what you can *actually* do, because one of those controls was configured incorrectly or contains a flaw.

So privilege escalation is not "hacking root." It is **finding and crossing a specific boundary that was not supposed to be crossable.** Sometimes that boundary leads all the way to root; often it leads one step sideways or one step up. Naming the specific boundary is the professional's job.

## 5. The Linux Identity Model

You cannot reason about crossing a boundary without knowing what the boundaries are made of. Three terms:

| Term | What it is |
|---|---|
| **User** | An identity the system recognises, with a numeric **UID**. Your processes run as your user. `student` here is UID 1000 |
| **Group** | A named collection of users, with a numeric **GID**. A user has one primary group and can be a member of many others. Permissions and privileges can be granted to a group, so *membership* grants authority |
| **root** | The superuser, **UID 0**. root bypasses normal permission checks. "Becoming root" is the strongest form of vertical escalation, but it is not the only meaningful one |

The single most important number on the system is the UID. Here is the real `/etc/passwd` from the training host:

```
cat /etc/passwd
root:x:0:0:root:/root:/bin/bash
student:x:1000:1000::/home/student:/bin/bash
```

Read the third field: `0` for root, `1000` for student. That `0` is the boundary the whole module circles. Everything root can do, it can do *because* its UID is 0 — not because of a password, but because the kernel treats UID 0 specially.

## 6. Why Privilege Escalation Exists

Linux enforces "who can do what" through a stack of mechanisms:

- **users and groups** — identity
- **file permissions and ownership** — who may read, write, execute what
- **SUID / SGID** — programs that run as their owner rather than their caller
- **sudo** — controlled, rule-based elevation
- **capabilities** — fine-grained slices of root's power
- **scheduled tasks and services** — code that runs, often as root, on a schedule or at boot
- **the kernel itself** — the final arbiter of every permission check

Every one of those is a place a boundary is *defined*. And every one of them is a place a boundary can be defined *wrongly*: an SUID bit on a program that should not have one, a sudo rule that is too broad, a root-run script anyone can edit, a capability granted to the wrong process, an unpatched kernel flaw.

**Privilege escalation exists because these boundaries are configured by humans, and humans misconfigure them.** That reframing matters: you are not looking for a secret exploit, you are looking for a boundary someone set up incorrectly. Which is exactly why enumeration — carefully reading the configuration — is the core skill, not an exploit list.

## 7. A Shell Is Not Root

This deserves its own section because it is the misconception that wastes the most time.

Getting a shell tells you that you can execute commands **as some user**. It says nothing about *which* user, or what that user can do. Consider the real identity output from the training host:

```
whoami
student

id
uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)
```

You have a shell. You are `student`, UID 1000 — not root. Everything you can do is bounded by what UID 1000 is permitted. That is the *starting line* of privilege escalation, not the finish.

Notice one real detail in that `id` output, though: `groups=...,27(sudo)`. This account is a member of the **sudo** group. That is not "you are root" — it is a *lead*, a boundary worth examining, because membership in that group may grant a path to elevation depending on how the system's sudo rules are written. Lesson 2 is where you learn to reason about exactly that. For now, the point is the discipline: a shell gives you a **position**, and the job is to understand that position precisely before doing anything with it.

## 8. Vertical vs Horizontal Escalation

Two shapes, and testers who blur them write imprecise findings.

| | Vertical | Horizontal |
|---|---|---|
| **Direction** | To a *higher* privilege level | To a *different* identity at the *same* level |
| **Example** | `student` (UID 1000) → `root` (UID 0) | `student` → another regular user, `developer` |
| **Why it matters** | Gains authority over the whole system | Gains access to another user's data, keys, or reachable services — often a stepping stone |
| **Typical boundary** | SUID-root program, broad sudo rule, root-run writable script, kernel flaw | A file readable by a group you are in, a shared directory, another user's exposed credential |

```
Vertical:                     Horizontal:

   root  (UID 0)                 student ──▶ developer
     ▲                           (UID 1000)   (UID 1001)
     │                            same privilege level,
   student (UID 1000)             different identity
```

Both are legitimate findings. Horizontal is easy to dismiss and shouldn't be: reaching `developer` might hand you an SSH key, a database password, or access to a service that *then* offers a vertical step. Professionals report the specific movement — "horizontal from `student` to `developer` via a group-readable key" — not a vague "we escalated."

## 9. Enumerate Before You Exploit

The instinct of a beginner is to find the machine's OS version and search for an exploit. That is backwards, and it is how testers crash services and miss the actual finding.

**A professional enumerates first.** Enumeration is not busywork before the real work — enumeration *is* how boundaries are discovered. You cannot cross a boundary you have not found, and boundaries are found by patiently reading the system's configuration.

Enumeration is a set of questions, each with a reason:

| Question | Why you ask it |
|---|---|
| Who am I? | Your UID/GID is the position everything else is measured from |
| What groups am I in? | Group membership can grant authority (note the `sudo` group above) |
| What OS and kernel is this? | Frames what is plausible — but a version is a lead, never a conclusion |
| What is running, and as whom? | A process running as root is a boundary; if you can influence it, it may be crossable |
| What can I read, write, execute? | Writable *and* privileged is the combination that matters |
| What runs on a schedule, and as whom? | A root-run scheduled task you can influence is a classic boundary failure |
| What may I run with elevated rights? | `sudo -l`, SUID programs, capabilities — the explicitly-elevated surface |

Notice that none of these is "run an exploit." Each is a question about the system's configuration, and the answers *together* build a map of boundaries. Lesson 2 turns each question into a concept; Lesson 3 has you ask them against a real training host.

## 10. The Core Enumeration Commands

Here are the identity commands the whole module rests on. Each is shown with its **real output from the authorized training host**, and — more importantly — the question it answers and why the answer matters. This is not a command dump: a command with no question behind it is trivia.

**Question: "Who am I?"**
```
whoami
student
```
The simplest possible orientation. You are `student`. Everything downstream is relative to this.

**Question: "What exactly is my identity — UID, GID, every group?"**
```
id
uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)
```
`id` is the single most useful enumeration command. It gives your UID (1000 — not 0, so not root), your primary group, and **every** supplementary group. The `sudo` group here is a concrete lead. Security relevance: group membership is a grant of authority, and `id` is how you see what you have been granted.

**Question: "Which groups do I belong to?"**
```
groups
student sudo
```
The same group information in a shorter form. Security relevance: some groups (`sudo`, and on other systems `docker`, `adm`, `disk`, and others) can, *depending on configuration*, provide a path to elevation. Membership is a question to investigate, not an answer.

**Question: "What system am I on — and what kernel?"**
```
uname -a
Linux yushacyber-lab 5.15.0 #1 SMP x86_64 GNU/Linux
```
The kernel version (`5.15.0`) and architecture (`x86_64`). Security relevance: the kernel is the final enforcer of every boundary, so a kernel flaw can cross any of them. **But** — and Lesson 2 hammers this — a version string is a *lead*, never proof. A matching version does not mean the flaw is present or exploitable here.

**Question: "What host is this?"**
```
hostname
yushacyber-lab
```
Orientation and, in a real engagement, evidence: findings must name the host they were found on.

Five commands, five questions, one purpose: **establish your position precisely before you touch anything.**

## 11. The Privilege Boundary — the Whole Module in One Idea

Everything in this module reduces to one mental model. A **privilege boundary** is any point where the system decides whether an action is allowed based on *who is asking*. A root-owned file. A root-run service. A scheduled job. A sudo rule. An SUID program. A capability.

For **every** such object, ask the same four questions:

```
┌─────────────────────────────────────────────┐
│  1. Who OWNS it?                              │
│  2. Who can MODIFY it?                        │
│  3. Who EXECUTES it?                          │
│  4. With WHAT privileges does it execute?     │
└─────────────────────────────────────────────┘
```

A boundary **fails** when the answers cross badly — most often when the answer to "who can modify it?" is *you*, and the answer to "with what privileges does it execute?" is *root*. If **you** can change what a **root** process does, the boundary between you and root has a hole in it.

Look at one real object from the training host through these questions:

```
ls -l
-rw-------  1 root root     84  Jan  5 08:00  private.txt
```

1. **Who owns it?** root.
2. **Who can modify it?** Only root — the permission bits are `rw-` for owner, nothing for group or others.
3. **Who executes it?** Nobody; it is data, not a program.
4. **With what privileges?** N/A.

This boundary is **sound**: root owns it, only root can touch it, and you (student) cannot even read it — which the system will enforce the moment you try. That is a correctly-configured boundary, and recognising a *sound* boundary is as important as recognising a broken one. Most of enumeration is examining boundaries and concluding "this one is fine." Lesson 3 shows you what happens when the same four questions are asked of a boundary that is *not* fine.

## 12. Correcting Some Common Misconceptions

**WRONG:** "Getting a shell means the system is compromised."
**CORRECT:** A shell gives you a *position* at some privilege level. What you can do is bounded by that level. `id` tells you where you actually stand.

**WRONG:** "Privilege escalation means immediately hacking root."
**CORRECT:** It means finding and validating a *specific* boundary that can be crossed. That might be vertical to root, or horizontal to another user. Naming the specific movement is the finding.

**WRONG:** "Enumeration is boring setup before the real work."
**CORRECT:** Enumeration *is* the real work. Boundaries are discovered by reading configuration; you cannot cross what you have not found.

**WRONG:** "Being in the `sudo` group means I'm root."
**CORRECT:** It is a lead. Whether it grants elevation depends entirely on how the system's sudo rules are written — which you investigate, not assume.

**WRONG:** "A newer kernel or a matching version tells me what to run."
**CORRECT:** A version is a lead. Exploitability depends on the specific build, configuration and patch level, none of which a version string proves.

## 13. Where This Sits in the Roadmap

```
Nmap / Wireshark / Burp / OWASP   →  find and understand services
Metasploit                        →  controlled, authorized initial access
Windows Privilege Escalation      →  crossing boundaries on Windows
Linux Privilege Escalation (here) →  crossing boundaries on Linux
      ↓
Red Team track                    →  chaining access at engagement scale
```

Initial access gets you a position. This module is about understanding that position and, where a boundary is genuinely broken, moving through it — carefully, on an authorized target, with evidence. That reasoning is what the Red Team track later assumes you already have.

## 14. Exercises

Reasoning exercises — nothing to run yet. Lesson 3 is where you work against a real training host.

**Exercise 1 — Define it in your own words.**
Without using the phrase "hack root," write a two-sentence definition of privilege escalation that a new teammate would understand. Include the words *boundary* and *intended*.

**Exercise 2 — Classify the movement.**
For each, say whether it is vertical or horizontal, and name the boundary:
(a) `student` reads `developer`'s private SSH key because it is group-readable
(b) `student` runs a program that executes as root and gets a root shell
(c) a web service account reaches another service account's config file

**Exercise 3 — Read your position.**
Given the real `id` output in §10, list three things you can honestly say about your position, and one lead worth investigating further.

**Exercise 4 — Apply the four questions.**
Pick the `private.txt` object from §11. Now imagine its permissions were `-rw-rw-rw-` (world-writable) instead of `-rw-------`, and that a root-run job reads it every minute. Re-answer the four boundary questions. Is the boundary still sound? Why or why not?

**Exercise 5 — Why enumerate first?**
A teammate wants to skip enumeration and immediately search the kernel version for an exploit. Give two concrete reasons this is the wrong first move.

## 15. Knowledge Check

1. **What is privilege escalation?**
   Obtaining privileges beyond those you were intended to have, by finding and crossing a boundary — expressed through ownership, permissions, groups, sudo, capabilities, and so on — that was configured incorrectly or contains a flaw. It is not synonymous with "becoming root."

2. **What is vertical privilege escalation?**
   Moving to a *higher* privilege level — for example `student` (UID 1000) to `root` (UID 0). It gains authority over more of the system.

3. **What is horizontal privilege escalation?**
   Moving to a *different* identity at the *same* privilege level — for example one regular user to another. It is often a stepping stone: the second identity may hold a key or reach a service that enables a later vertical step.

4. **Why is enumeration performed before exploitation?**
   Because boundaries are discovered by reading configuration, not by guessing. You cannot cross a boundary you have not found, and premature exploit attempts are noisy and can crash services.

5. **What does `id` reveal, and why is it the most useful enumeration command?**
   Your UID, primary GID, and every supplementary group. It fixes your exact position (UID 1000 here, so not root) and reveals group memberships — like `sudo` — that are concrete leads for elevation.

6. **Why does group membership matter?**
   Because permissions and privileges can be granted to a group, so membership *is* a grant of authority. Whether a given group (e.g. `sudo`) yields elevation depends on the system's configuration, which you investigate rather than assume.

7. **Why isn't "I have a shell" the same as "I have root"?**
   A shell lets you execute commands as *some* user at *some* privilege level. `whoami`/`id` tell you which. Here that is `student`, UID 1000 — the starting line, not the finish.

8. **What is the significance of UID 0?**
   UID 0 is root, and the kernel treats it specially — it bypasses normal permission checks. It is the boundary vertical escalation ultimately targets, and `/etc/passwd`'s third field is where you read a user's UID.

9. **What is a privilege boundary, and what four questions do you ask of one?**
   Any point where the system decides whether an action is allowed based on who is asking. For each: who owns it, who can modify it, who executes it, and with what privileges. A boundary fails when *you* can modify something that runs as *root*.

10. **Why is a kernel version only a lead?**
    Because exploitability depends on the specific build, configuration and patch level — not the version string alone. A matching version does not prove a flaw is present or usable on this host.

11. **Why must escalation only ever be attempted on authorized targets?**
    Because escalation deliberately makes a system grant authority it was configured to withhold. On a system you do not own or have written permission to test, that is intrusion, regardless of whether the boundary was misconfigured.

12. **Why should a tester distinguish an "interesting finding" from a "confirmed escalation path"?**
    Because many interesting configurations lead nowhere — a writable file that no privileged process ever reads changes nothing. Confirmation requires showing the boundary actually can be crossed. Lesson 2 makes this distinction its centrepiece.

---

**Next:** *Core Concepts* walks the major Linux escalation surfaces — permissions, SUID/SGID, sudo, capabilities, cron, services, PATH, kernel, containers — and, throughout, keeps the one distinction that separates a professional from a script: a *finding* is not a *confirmed path*.
