# Introduction to Operating Systems

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain, concretely, what an operating system actually does between an application and the hardware it runs on
- explain the difference between user space and kernel space, and why that separation exists at all
- explain what a system call is, using a real file-read as the example
- explain the difference between a program and a process, in outline (Core Concepts goes deep on this)
- connect commands you already know (`whoami`, `cat`) to the OS layer actually doing the work behind them

## 2. Why This Matters

Every module so far has quietly depended on an operating system without naming it. When Linux Fundamentals had you run `ls`, `cat`, and `chmod`, something had to actually read the disk, check whether you were allowed to, and hand back an answer — that something is the OS, and it's been doing real work in every lesson you've completed. This module names it directly: not as trivia, but because the concepts here — process isolation, memory protection, permissions, privilege — are the exact foundation every later security topic on this platform (privilege escalation, malware behavior, endpoint security, digital forensics) is built on. You cannot reason about a compromised process or an exploited memory bug without first understanding what a process and memory boundary actually are.

## 3. What an Operating System Actually Does

An application never talks to hardware directly. A web browser doesn't know how to move the disk's read head, and a Python script doesn't know how to program a network card. Instead, every application sits on top of a layer that manages all of that on its behalf — the **operating system**.

```
USER
  ↓
APPLICATION            (browser, terminal, Python script)
  ↓
OPERATING SYSTEM        manages, on the application's behalf:
  • processes              — what's running, and when it gets CPU time
  • memory                 — where each program's data actually lives
  • files and storage      — organizing and protecting data on disk
  • devices and I/O        — keyboard, disk, network card, display
  • permissions            — who is allowed to do what
  • networking              — sending and receiving data over a network
  ↓
HARDWARE                (CPU, RAM, disk, network card)
```

The operating system's job, in one sentence: **it's the control layer that manages a computer's shared resources and decides, on behalf of every application, what they're allowed to do with them.** "Shared" is the key word — a single computer usually runs many applications at once, all of them wanting CPU time, memory, and disk access simultaneously, and none of them individually trusted to sort that out fairly or safely on their own.

## 4. User Space and Kernel Space

The OS enforces this control by drawing a hard line between two modes of operation.

**User space** is where ordinary applications run — your browser, your terminal, a Python script you write. Code running here is *not* allowed to touch hardware directly or access another application's memory.

**Kernel space** is where the core of the operating system itself runs — privileged code with direct access to hardware and the authority to manage every other running program. The **kernel** is this privileged core specifically, not a synonym for "the whole OS" — an operating system also includes plenty of user-space components (utilities, services, libraries) that aren't part of the kernel at all.

**Why this separation exists — three concrete reasons, not an abstract rule:**

- **Security.** If any application could freely read any other application's memory, a browser tab could read your password manager's contents. The boundary prevents that by default.
- **Stability.** If a single crashing application could take down the whole machine by corrupting shared hardware state, one buggy program would mean a full system crash, constantly. Isolating user-space programs from each other and from the kernel means one crash usually stays contained to that one program.
- **Controlled hardware access.** If every application could program the disk controller directly, two applications writing to the disk at the same time could corrupt each other's data with no coordination at all. The kernel is the single point that arbitrates hardware access, so it can enforce order.

## 5. System Calls: How User Space Actually Gets Anything Done

If user-space applications can't touch hardware directly, how does a program ever read a file, send data over the network, or print to your screen? By asking the kernel to do it — through a **system call**.

**What it does:** a system call is a formal request from a user-space program to the kernel, asking it to perform a privileged operation on the program's behalf. It's the *only* sanctioned door between user space and kernel space.

Trace this through something you've already done for real: running `cat welcome.txt` in Linux Fundamentals.

```
Application (cat)
    ↓  "I need the contents of this file"
system call (a request like "open this file, then read it")
    ↓
Kernel
    ↓  checks: does this file exist? is this user allowed to read it?
Resource (the actual disk, and the filesystem's record of that file)
    ↓
Result
    ↓
back to the application, which then prints what it received
```

`cat` never touches the disk itself. It asks the kernel, the kernel checks permissions and locates the data, and the kernel hands the result back. Every "simple" command you've run so far — `ls`, `cat`, `whoami` — is, underneath, a small sequence of system calls exactly like this one. This is not a detail specific to Linux either — every general-purpose operating system (Linux, Windows, macOS) enforces this same user-space/kernel-space boundary, though the exact system-call interface each one exposes is its own, and not identical across them.

## 6. A First Look: Programs vs. Processes

Recall from Linux Fundamentals: **a program** is the executable file the shell runs when you type a command — code sitting on disk, doing nothing until it's launched.

The moment you run it, something new exists: a **process** — a running instance of that program, with its own private memory, its own execution state, and its own identity that the OS tracks (and can start, pause, or stop independently of any other running copy of the same program). The program is the recipe; the process is an actual meal being cooked from it, right now, with its own pot and ingredients that no other cook can reach into.

This distinction is the entire subject of Core Concepts — for now, just hold onto the shape of it: **the file on disk and the running thing in memory are not the same object**, even when they share a name.

## 7. Common Mistakes

**Assuming "kernel" means "the entire operating system."** The kernel is the privileged core; an OS also includes user-space services, utilities, and libraries that never run in kernel mode at all.

**Thinking a system call is optional for "simple" operations.** There's no such thing as a user-space program reading a file, printing to the screen, or sending a packet without going through the kernel — the operation might feel instantaneous, but the request/response trip through the kernel still happened.

**Treating "program" and "process" as interchangeable.** You'll see exactly why this matters in Core Concepts — for now, notice that this lesson already stopped using them as synonyms.

## 8. Practice

In the YushaCyber terminal:

1. Run `whoami` (you've done this before, in Linux Fundamentals) and this time notice what's actually happening: your shell isn't storing your username itself — it's asking the kernel who you're currently authenticated as, every single time, via a system call.
2. Run `uname` and then `uname -a`. Read the difference in output, and note that this command's entire job is asking the kernel to report information about itself.
3. Without running anything: name one thing a program running in user space is *not* allowed to do on its own, and explain what has to happen instead.

## 9. Knowledge Check

1. In one sentence, what does an operating system actually manage on behalf of every running application?
2. Why does the separation between user space and kernel space exist — name at least two of the three reasons from Section 4?
3. What is a system call, and why is it described as the "only sanctioned door" between user space and kernel space?
4. Walk through what happens, step by step, when `cat` reads a file — using Section 5's diagram as a guide.
5. What's the difference between a program and a process, in your own words?

## 10. Key Takeaways

- The operating system is the control layer between applications and hardware — it manages processes, memory, files, devices, permissions, and networking so applications never have to.
- User space (ordinary applications) and kernel space (the OS's privileged core) are kept separate for security, stability, and controlled hardware access — not as an arbitrary rule.
- A system call is how a user-space program asks the kernel to do something privileged on its behalf — every file read, network send, or screen write goes through one.
- A program is an executable file on disk; a process is a running instance of it, with its own memory and execution state — they are not the same thing, even when they share a name.

## 11. What's Next

**Core Concepts** goes deep on processes: how they're created and terminated, why a system can run far more processes than it has CPU cores, what a thread is and how it differs from a process, and how memory — RAM, virtual memory, and the difference between "temporary" and "persistent" storage — actually works underneath every program you run.
