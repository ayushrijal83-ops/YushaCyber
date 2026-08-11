# Hands-on Practice: Files, Permissions, Devices, and the OS in Practice

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what's actually happening at the OS level when a command like `ls` or `cat` runs
- explain identity, groups, and permissions as an OS-enforced security mechanism, not just a filesystem feature
- explain what a device driver is and why the OS needs one for every piece of hardware it talks to
- explain, at a conceptual level, how the OS provides networking to applications
- explain what a background service (daemon) is, and walk through the boot process that starts one
- connect every concept in this module to why it matters for cybersecurity work later on this platform
- work through a full scenario reasoning about processes, memory, permissions, and network access at once

## 2. Why This Matters

This is where the whole module lands somewhere concrete: every command you already know from Linux Fundamentals, every IP address and port from Computer Networking, and every script you wrote in Python Programming was actually running *on top of* everything Introduction and Core Concepts just explained. This lesson makes that connection explicit, then uses it to explain why an entire category of security work — privilege escalation, malware analysis, endpoint security, digital forensics — is fundamentally about attacking or defending the exact mechanisms taught in this module.

## 3. Filesystems as an OS-Managed Resource

Linux Fundamentals taught you to navigate and manipulate files — `cd`, `ls`, `cat`, `mkdir`, `rm`. This lesson isn't reteaching any of that; it's answering the question those lessons left open: **what is actually happening when you run them?**

Every one of those commands is a request to the OS's filesystem layer, which tracks, for every file: where its data physically sits on disk, its metadata (size, timestamps, owner, permissions), and the directory structure that organizes it all. When you run `ls`, you are not reading raw disk sectors yourself — you're asking the kernel, via a system call (Introduction, Section 5), to look up a directory's contents and hand you back the list. The filesystem is the OS's answer to a hard problem: dozens of processes might want to read and write files at the same time, and something has to keep that organized, consistent, and — critically for this platform's purposes — access-controlled.

## 4. Permissions and Security: Identity Enforced by the OS

Linux Fundamentals taught you `chmod` and how to read a permission string like `rwxr-xr-x`. This lesson explains the layer underneath that: **why the OS enforces any of it at all, and how it knows who's asking.**

Every process runs *as* some identity — a specific user — and the kernel checks that identity against a file's permissions on every single access attempt, not just once. Two commands you haven't used yet make this identity concrete:

```bash
id
```

```
uid=1000(student) gid=1000(student) groups=1000(student),27(sudo)
```

**What this means:** `uid` is your numeric user ID (the kernel's actual internal identifier — `student` is just the human-readable name mapped to it); `gid` is your primary group ID; `groups` lists every group you belong to, including secondary ones like `sudo` here. The kernel doesn't check permissions against a username string at all — it checks against these numeric IDs, underneath the readable names entirely.

```bash
groups
```

```
student sudo
```

**Why this is a security mechanism, not just a filesystem feature:** when you tried to write to a file you didn't own back in Linux Fundamentals, the kernel checked exactly this identity — your uid, your gid, your group memberships — against that file's stored owner, group, and permission bits, on that specific request, and denied it if they didn't match what the permission bits allowed. This is the OS actively enforcing a boundary, the same way it enforces the user-space/kernel-space boundary from Introduction — a normal user process cannot simply decide to have more access; the kernel is the sole authority making that call, every time, and there's no way for user-space code to skip the check.

**This is exactly why privilege matters, and why it's the foundation of privilege escalation** — a topic in the Intermediate track later in this platform. An attacker who compromises a process running as an ordinary user is bound by whatever that user's permissions actually allow; a process compromised while running with elevated privileges inherits far more. The gap between those two outcomes is entirely explained by this section.

## 5. Devices and I/O

The OS doesn't just manage files and memory — it also coordinates access to every physical device attached to the machine: the keyboard, mouse, display, disk, network interface, USB devices, printers. None of these are identical pieces of hardware even across two machines of the same type (different disk models, different network cards), which creates a real problem: how does the same OS talk to wildly different hardware without every application needing to know the specifics of every possible device?

The answer is a **device driver** — a piece of software, usually supplied by the hardware manufacturer or built into the OS, that translates between the OS's generic request ("write these bytes to storage") and the exact, specific instructions that particular piece of hardware understands. Applications, and even most of the OS itself, talk to a *generic* interface; the driver is what makes that generic request actually work on the real, specific device underneath. **Device drivers are not interchangeable or identical across operating systems** — a driver written for one OS's internal interface generally won't work on another, which is exactly why a hardware manufacturer has to ship separate drivers for Windows, Linux, and macOS versions of the same physical device.

## 6. Networking From the OS's Perspective

Computer Networking already taught you IP addresses, ports, TCP/UDP, and DNS — real, protocol-level knowledge. This lesson adds the missing piece: **where does all of that actually run?**

The OS's **network stack** is the part of the kernel responsible for implementing those protocols and managing the network interface card as a device (Section 5's device/driver relationship applies here too — a NIC needs a driver like any other hardware). When an application wants to send data over the network, it doesn't build raw packets itself; it makes a system call asking the kernel's network stack to handle it, the same request/response pattern from Introduction's Section 5 file-read example, just for network I/O instead of disk I/O. The OS is what actually owns a network port, tracks which process is using it, and enforces that two different processes can't silently claim the exact same port for the same purpose.

## 7. Services and Daemons

Not every process is something a user directly launched. A **service** (on Linux, often called a **daemon**) is a program the OS starts and keeps running in the background, with no visible window, doing continuous work: a networking service that keeps your network connection configured, a logging service collecting system events, a scheduled service running periodic tasks. Recall Core Concepts' process lifecycle (Created → Ready → Running → Waiting) — a daemon follows exactly the same lifecycle as any other process; it simply has no GUI attached and typically starts automatically rather than being launched by a user typing a command.

**Why this matters for security specifically:** every running service is something listening or watching, and every service is also potential attack surface — a concept you already met in Cybersecurity Fundamentals. A service exposed to the network that shouldn't be, or left unpatched, is a real, common way systems get compromised — this is exactly why "what services are running, and why" is a real, ongoing question in operational security, not a one-time setup step.

## 8. The Boot Process

Here's how a service comes to be running in the first place, traced from power-on:

```
Power on
    ↓
Firmware        — low-level code built into the motherboard that
                   does minimal hardware setup and finds a bootloader
    ↓
Bootloader      — a small program whose only job is to locate and
                   load the operating system's kernel into memory
    ↓
Kernel          — takes over, initializes hardware access, and starts
                   the very first user-space process
    ↓
System services — the OS starts its background services and daemons
                   (Section 7) in a defined order
    ↓
Login/session   — the system is ready, and a user can log in and
                   start launching their own processes
```

Every process on a running system — services included — ultimately traces back through this chain. This is the concept, not an invitation to memorize BIOS/UEFI internals; the important takeaway is that services aren't magic background processes that simply "exist" — they're started, in order, as a defined part of this sequence, by the kernel or by an early system service responsible for starting the rest.

## 9. Bringing OS Security Together

Pull every idea in this module into one list, because each one is a real security foundation you'll build on later:

- **User accounts and privilege** (Section 4) — the identity every process runs as, and the boundary that limits what a compromised process can do.
- **Permissions** (Section 4) — the OS-enforced check on every file access, on every request, with no exceptions for user-space code.
- **Process isolation** (Introduction, Section 4; Core Concepts, Section 8) — why one compromised process doesn't automatically hand an attacker every other process's memory.
- **Memory protection** (Core Concepts, Section 8) — the virtual-memory mapping that keeps one process's data out of another's reach.
- **Service exposure** (Section 7) — every running service is a potential entry point, and knowing what's actually running is a real, ongoing security question.
- **Updates** — patches exist specifically to fix flaws in the kernel, drivers, and services covered in this module; an unpatched system is running known-flawed versions of exactly the components this lesson just explained.
- **Logs** — a record of what processes, users, and services actually did, which is how an incident gets investigated after the fact, echoing Cybersecurity Fundamentals' detection material.

This module deliberately stops at *understanding* these mechanisms — not exploiting them. Privilege escalation, malware analysis, endpoint security, and digital forensics, later in this platform, are all about what happens when one of these boundaries fails or gets deliberately broken; none of that is meaningful without first knowing, precisely, what the boundary actually is — which is what this module has been building toward.

## 10. Practical Exercises

Two real, existing pieces of this platform's infrastructure reinforce different halves of this lesson — use both.

**Processes, live.** In the YushaCyber terminal, `ps`, `top`, `kill`, and `jobs` aren't available in the free-practice sandbox, but the platform's real **Processes** lab puts you in a simulated environment built specifically for them: list running processes, monitor live resource usage, and stop a runaway process by its process ID — a direct, hands-on version of Core Concepts' process lifecycle (Section 4) and the fact that a process can be identified and terminated independently of any other.

**Identity and permissions, live.** The platform's real **Linux Permissions** mission walks you through exactly Section 4's material against a realistic filesystem: reading permission notation, checking your own identity, inspecting your group memberships, and working with ownership and `chmod` — the mission's own environment, not a new one.

In the free-practice terminal (`/terminal`) right now, you can also run this lesson's own commands for real: `id`, `groups`, `uname`, `uname -a`, and `whoami` all work exactly as shown in Sections 4 and Introduction's Section 8 — try each one and compare the output to what this lesson showed you.

## 11. Scenario: Trace the Whole Stack

A student opens a browser, starts a terminal, downloads a file, and launches a Python program. Work through each question yourself before reading on — this scenario is designed to make you use every section of this module together, the same way a real system actually does.

1. **What processes exist right now?** *(Core Concepts, Sections 3–4)*
2. **Where does the downloaded file actually live once the download finishes, and why does it survive if the browser is closed afterward?** *(Core Concepts, Section 7)*
3. **What manages the memory each of these programs is using while they run?** *(Core Concepts, Section 8)*
4. **What actually handled the network connection that fetched the downloaded file?** *(This lesson, Section 6)*
5. **What determines whether the Python program is allowed to read the file the browser just downloaded?** *(This lesson, Section 4)*
6. **The student closes the terminal. What happens to the Python process it was running, and does the downloaded file disappear with it?** *(Core Concepts, Sections 4 and 7 — answer these as two separate questions, since a process ending and a file being deleted are not automatically connected.)*

Work through each answer using the specific section referenced — if any answer doesn't come easily, that's the section worth rereading, not a sign to guess.

## 12. Common Mistakes

**Assuming `ls`/`cat` "just work" without asking why.** Section 3's whole point is that a system call and a permission check happen on every one of them, even though it feels instant.

**Treating permissions as a Linux-specific filesystem quirk.** They're an OS-enforced identity check, present in some form on every general-purpose operating system — Linux Fundamentals just happened to be where you first practiced the syntax for it.

**Assuming a device driver written for one OS works on another.** Section 5 is explicit: drivers are OS-specific translation layers, not universal.

**Believing a service "just runs" with no explanation.** Section 8 traces exactly how a service comes to be running — it's a defined step in the boot sequence, not something that appears from nowhere.

**Treating this module as attack material.** It deliberately isn't — Section 9 explains understanding as the prerequisite for the security topics that come later, not a shortcut to them.

## 13. Knowledge Check

1. When `ls` runs, what is actually happening at the OS level, and which earlier lesson's concept (system calls) explains it?
2. Why does the kernel check numeric uid/gid values instead of usernames when enforcing permissions?
3. Why can't a device driver written for one operating system be reused, unmodified, on a different one?
4. What is a daemon, and how does its process lifecycle differ from an application you launch yourself?
5. Put the boot sequence in order, from power-on to a usable login session.
6. Name three OS mechanisms from Section 9 that later become the foundation for privilege escalation, malware analysis, or digital forensics — and explain the connection for one of them.

## 14. Key Takeaways

- Every filesystem command you already know (`ls`, `cat`, `chmod`) is a system call to the OS's filesystem layer, checked against your process's identity on every single access — not a one-time check.
- `id` and `groups` reveal the numeric identity (uid/gid) the kernel actually enforces permissions against, underneath the readable username.
- A device driver translates between the OS's generic hardware request and a specific device's actual instructions — drivers are OS-specific, not portable across operating systems.
- The OS's network stack is what actually implements the protocols Computer Networking taught you and owns the network interface as a device, just like any other hardware.
- A service/daemon is an ordinary process with no GUI, started in a defined order during boot (firmware → bootloader → kernel → services → login) — not something that appears on its own.
- Every concept in this module — privilege, isolation, memory protection, service exposure, updates, logging — is the real foundation for privilege escalation, malware analysis, endpoint security, and digital forensics later in this platform.

## 15. What's Next

This is the last lesson in Operating Systems — you now understand the control layer every application, script, and command on this platform has been running on top of since Linux Fundamentals. The roadmap's next module, **Cryptography Basics**, shifts to a different layer entirely: how data is protected mathematically rather than through OS-enforced boundaries — but the reasoning habit stays the same, and you'll keep recognizing "who's allowed to do what, and how is that actually enforced" as a question this platform keeps asking in new contexts.
