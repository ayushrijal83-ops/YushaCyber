# Core Concepts: Processes, Threads, and Memory

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain, with a concrete example, why opening one program can create more than one process
- describe a process's lifecycle and explain what a process state actually represents
- explain why a system with 4 CPU cores can still run 200 processes "at once"
- explain the difference between a process and a thread, and why applications use multiple threads
- explain the difference between RAM and persistent storage precisely, not just "temporary vs. permanent"
- explain what virtual memory actually is — and what it is not

## 2. Why This Matters

Introduction told you a process is "a running instance of a program." That's true but not yet useful — this lesson is where it becomes something you can actually reason with: why your system can run a browser, a terminal, and a Python script simultaneously without them interfering with each other, why closing one browser tab doesn't take down the other nineteen, and why a process crashing rarely brings down anything except itself. Every one of these is a direct, practical consequence of the concepts in this lesson.

## 3. Programs vs. Processes, Made Concrete

Take Introduction's distinction and put a real number on it: **launching an application can create one process, or several, and which one happens depends entirely on how that specific application is built** — there's no universal rule here, so don't memorize "N processes per app launch" as a fact; treat it as something to actually check.

A concrete, common example: modern browsers frequently run each tab (or group of tabs) as a **separate process**, deliberately — so that if one tab's page crashes or hangs, it takes down only that tab, not your entire browser or every other open tab. Open the same browser with three tabs and you may well find several distinct browser processes running, all from launching "one program." Compare that to a simpler command-line tool: running `cat` twice, in two different terminal windows, creates two separate processes too — but each is a small, independent process, not several processes cooperating to render one tab.

The lesson here isn't "browsers make three processes and `cat` makes one" — it's that **a process count is a fact about a specific running system at a specific moment, not a property you can derive from the program's name alone.**

## 4. The Process Lifecycle

Every process moves through a predictable set of states from the moment it's created to the moment it ends:

```
Created  →  Ready  →  Running  →  (Waiting) → Ready → Running → ...  →  Terminated
```

**Created** — the OS has set up a new process (allocated it memory, given it an identity) but hasn't started running its code yet.

**Ready** — the process is fully able to run and is simply waiting for the CPU to become available to it.

**Running** — the process is the one currently executing on a CPU core, right now.

**Waiting (sometimes called "blocked")** — the process can't proceed yet because it's waiting on something external: a file to finish loading from disk, a network response, user input. Crucially, a waiting process is *not* consuming CPU time — the OS moves it aside and gives the CPU to something else that's actually ready to run.

**Terminated** — the process has finished (or was stopped), and the OS reclaims whatever memory and resources it was using.

**Why this matters practically:** a process spends a surprising amount of its life in the Waiting state, not Running — a program that's mostly reading files or waiting on a network response is idle, from the CPU's point of view, most of the time. This is exactly what makes the next section possible.

## 5. Scheduling: How "Simultaneous" Actually Works

Here's the problem the OS has to solve: a typical system has far more runnable processes (your browser, a terminal, background services, this platform's own processes if you're running things locally) than it has CPU cores to run them on. Something has to decide, constantly, which process actually gets to run right now.

That something is the **scheduler**, a core part of the OS. Rather than running one process to completion before starting the next (which would make everything else on your system freeze while a single program ran), the scheduler gives each ready process a small **time slice** — a few milliseconds of CPU time — then swaps it out for the next ready process, and swaps that one out in turn, over and over, extremely fast. Moving a CPU core from running one process to running another is called a **context switch**: the OS saves exactly where the outgoing process was (so it can resume later without losing anything) and loads the incoming process's saved state.

This happens so fast — thousands of times per second — that dozens of processes genuinely appear to run at the same time to a human, even on a single CPU core. **Modern systems also have multiple CPU cores**, which means some processes really are running at the exact same physical instant, not just rapidly alternating — but the illusion of "everything is running at once" holds either way, because the scheduler and time-slicing mechanism work the same regardless of core count; more cores just mean more processes can be *genuinely* simultaneous rather than merely interleaved.

## 6. Threads: A Finer Unit of Execution

A **process** is a container: it owns a block of memory, a set of open files, and an identity the OS tracks. A **thread** is a unit of *execution* running inside that process — the actual sequence of instructions being carried out. Every process has at least one thread by default, but many real applications deliberately create several.

**Why an application would want multiple threads:** a web server commonly runs one thread per incoming connection (or pulls from a pool of them), so handling one slow client doesn't stall every other client waiting on the same server. A GUI application typically keeps one thread dedicated to responding to clicks and keeping the interface responsive, while other threads do slower work (loading a file, running a calculation) in the background — without multiple threads, that slow work would freeze the entire interface until it finished.

**Threads within one process share that process's memory** — this is the key structural difference from Section 3's separate processes, which do *not* share memory with each other by default. Shared memory makes threads lighter-weight and faster to communicate between, but it's also exactly why multi-threaded programming is harder to get right: two threads can step on the same piece of memory at the same time if the programmer isn't careful, in a way two separate processes simply can't.

**One precise distinction worth holding onto: concurrency is not the same as parallelism.** Concurrency means multiple threads (or processes) are *in progress* at once — which, per Section 5, can happen through fast interleaving on a single core, with no two of them literally executing at the exact same instant. Parallelism specifically means multiple threads are executing at the *exact same physical instant*, which requires multiple CPU cores. A single-core machine can absolutely run concurrent programs; it cannot run anything in true parallel, no matter how the software is written.

## 7. Memory Management: RAM vs. Storage

These two get casually conflated as "memory," but they're built for genuinely different jobs, and the distinction matters every time you reason about what happens when a program runs.

**RAM (Random Access Memory)** is fast, working memory that a running process's code and data actually live in *while it's executing*. It's built for speed, not permanence.

**Persistent storage** (an SSD or HDD) is where data is kept so it survives after a program — or the whole computer — stops running.

**The precise distinction, stated carefully (not just "temporary vs. permanent"):** RAM is *working memory* — the space a process actively computes in — while storage is a *durability guarantee*. A file you saved to disk is still there after a restart specifically because storage is designed to retain data with the power off; RAM is designed for extremely fast read/write access while a process is actively running, and does not carry that durability guarantee. This is exactly why closing an application, or restarting your machine, doesn't erase your files: whatever a program had loaded into RAM disappears (that memory is reclaimed the moment the process terminates, per Section 4), but anything it explicitly *saved to storage* was written somewhere built to keep it.

## 8. Virtual Memory

Here's a question worth sitting with: if a system is running 50 processes at once, and each one behaves as though it has its own private block of memory starting at address zero, how does that work without every process constantly colliding with every other one?

The answer is **virtual memory** — a memory-management abstraction the OS provides to every process. Each process is given its own **virtual address space**: from that process's point of view, it appears to have a large, private, contiguous block of memory entirely to itself. The OS (with hardware assistance) maintains a mapping from each process's virtual addresses to the actual **physical memory** (real RAM) where that data really lives, in small fixed-size chunks called **pages**. Two different processes can use the identical virtual address for completely different data, because the OS's mapping sends each one to a different physical location — this is precisely the memory isolation Introduction's Section 4 described as a security benefit, now visible as the actual mechanism behind it.

**One precise thing virtual memory is not: it is not simply "using the hard drive as extra RAM."** That's a common oversimplification worth correcting directly. Virtual memory is fundamentally about the *address-mapping abstraction* just described — giving every process its own consistent view of memory — which is useful and in effect at all times, regardless of how much physical RAM is actually free. Separately, when physical RAM genuinely runs short, the OS can move a page that isn't being used right now out to disk to free up RAM for something more active — this specific mechanism is called **paging** or **swapping**, and asking for a page that's currently out on disk (rather than in physical RAM) triggers what's called a **page fault**, which the OS handles by fetching that page back from disk before letting the process continue. Swapping is one real consequence of virtual memory under memory pressure — it is not what virtual memory fundamentally *is*.

## 9. Connecting to Python

You already ran Python scripts in Python Programming — now you have the vocabulary to describe what actually happened when you did:

```
Your .py source file           (a program — code on disk)
    ↓  you run: python script.py
The Python interpreter starts   → this creates a process
    ↓
That process gets its own virtual address space (Section 8),
    its own place in the scheduler's rotation (Section 5),
    and its own identity the OS tracks (Section 4's lifecycle)
    ↓
Every time your script opens a file, makes a network request,
    or reads an environment variable, it's issuing a system call
    (Introduction, Section 5) on your behalf
```

A Python script isn't a special case that bypasses any of this — it's an entirely ordinary process, subject to exactly the same scheduling, memory isolation, and system-call boundary as everything else covered in this lesson.

## 10. Common Mistakes

**Assuming one launched application always equals exactly one process.** Section 3 already showed this is false in general — check, don't assume.

**Believing a "waiting" process is still using CPU time.** It isn't — Section 4's whole point is that waiting processes step aside so something ready can actually run.

**Saying RAM is "temporary storage."** It's not storage at all in the durability sense — it's working memory with no persistence guarantee, which is a different property than "temporary."

**Describing virtual memory as "using the disk as RAM."** That's swapping, one specific consequence of memory pressure — not what virtual memory fundamentally provides, which is the address-space abstraction from Section 8.

**Assuming multiple threads means genuine parallel execution.** Only true on multiple cores; on one core, "multiple threads" still means concurrency achieved through the same time-slicing from Section 5, not literal simultaneity.

## 11. Practice

**Exercise 1 — Guided.** List three processes you'd expect to be running on an ordinary computer right now, none of which the user directly launched by name. (Hint: Introduction's diagram mentioned services.)

**Exercise 2 — Independent.** A process is currently downloading a large file over a slow connection. Which process state (Section 4) is it most likely spending most of its time in, and why isn't that wasteful for the rest of the system?

**Exercise 3 — Reasoning.** Two processes both use the exact same virtual address to store different data, with no conflict. Explain, using Section 8, why that's possible.

**Challenge.** A single-core laptop is "running" a music player, a web browser, and a file download at the same time, from the user's perspective. Explain what's actually happening, using both Section 5 (scheduling) and Section 6's concurrency-vs-parallelism distinction — and state plainly whether any of this is true parallelism on that specific machine.

## 12. Knowledge Check

1. Why can launching the same application twice create a different number of processes depending on the application?
2. Put the five process states in order, and explain what specifically makes "Waiting" different from "Ready."
3. What is a context switch, and why does the OS need to save state before performing one?
4. What's the structural difference between a process and a thread — specifically regarding memory?
5. Explain, precisely, why RAM losing its contents on restart is not the same fact as "files get deleted on restart."
6. What is a page fault, and what triggers one?

## 13. Key Takeaways

- Whether launching a program creates one process or several depends on how that specific application is built — never assume, check.
- A process moves through Created → Ready → Running → (Waiting) → ... → Terminated; a Waiting process isn't consuming CPU time, which is exactly what makes running many processes on few cores possible at all.
- The scheduler gives each ready process a short time slice and performs a context switch to move on — this interleaving is what makes many processes appear simultaneous even on one core.
- A thread is a unit of execution inside a process; threads in the same process share memory, which makes them lighter-weight than separate processes but also easier to get wrong. Concurrency (in progress at once) and parallelism (executing at the literal same instant) are not the same thing.
- RAM is fast working memory with no durability guarantee; persistent storage is built specifically to survive a restart — that's the real distinction, not just "temporary vs. permanent."
- Virtual memory gives every process its own private address space, mapped to physical RAM by the OS; swapping/paging (using disk when RAM is under pressure) is one consequence of that system, not what virtual memory fundamentally is.

## 14. What's Next

**Hands-on Practice** brings this down to the filesystem and permissions layer you already touched in Linux Fundamentals — now explained as OS-managed resources, not just commands to memorize — plus devices, networking from the OS's point of view, background services, the boot process, and a full scenario that asks you to reason through everything this module has covered at once.
