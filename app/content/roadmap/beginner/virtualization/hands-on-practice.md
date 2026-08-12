# Virtualization in Practice

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what a snapshot is, what it's good for, and why it is **not** a backup
- explain how VM images and templates make an environment reproducible
- state honestly what VM isolation gives you and what it does not
- explain how a container differs from a virtual machine, without calling it a "lightweight VM"
- explain why virtualization is the foundation of practically every security lab, CTF, and malware-analysis environment
- name the real security risks that come *with* virtualization, at the hypervisor, configuration, and management layers
- reason about a real machine's resources and design a working lab setup on it
- inspect real virtual machines on this platform and reason about their exposure

## 2. Why This Matters

Everything up to here has been mechanism. This lesson is judgment: the decisions you'll actually make when you build a lab, and the mistakes that quietly cost people their work or their safety. Two of them in particular — trusting a snapshot as a backup, and trusting a VM as an absolute security boundary — are made by intelligent people constantly, and both are the direct result of a plausible-sounding assumption nobody ever checked.

## 3. Snapshots

A **snapshot** captures a VM's state at a moment in time so you can return to that exact state later. Depending on whether the VM was running, it captures the virtual disk's contents and, optionally, the memory state — meaning "revert" can mean *back to that powered-off machine* or *back to that exact running moment*.

Practically, this is the single most useful thing a VM can do that a physical machine cannot, and it changes how you work:

- **Experiments.** Snapshot, change something drastic, see what breaks, revert. Total cost of a bad idea: a few seconds.
- **Labs.** Snapshot a clean, configured machine before an exercise; revert to it for the next run instead of rebuilding.
- **Testing.** Try an installation or configuration on a known-identical starting state, repeatedly.
- **Malware analysis.** Snapshot a clean analysis VM, detonate a sample, observe, revert to the clean state. Nothing you learned is lost; nothing the sample did survives.
- **Rollback.** Snapshot before a risky update, so "undo" is real.

The mechanism matters for the next section. Once you take a snapshot, the original disk contents generally stop being modified; new writes go into an additional file that records the *differences* since the snapshot. Reverting means discarding those differences. That's why snapshots are so fast — but it also means a VM with several snapshots is a **chain of dependent files**, each one only meaningful in combination with the ones before it.

## 4. A Snapshot Is Not a Backup

This is the section to remember.

**A snapshot is a point you can return to *within* the same VM, stored alongside it on the same storage.** A backup is an independent copy of your data, kept somewhere else, that can restore your data when the original is gone.

| | Snapshot | Backup |
|---|---|---|
| **Stored where** | With the VM, on the same host storage | Somewhere separate — another disk, another machine, another site |
| **Independent of the original?** | No — depends on the base disk and the chain | Yes, that's the entire point |
| **Survives the host's disk failing?** | No | Yes |
| **Survives the VM being deleted?** | No | Yes |
| **Survives ransomware encrypting the host?** | Generally no — it's reachable from the same host | If properly separated, yes |
| **Good for** | "Undo the last hour" | "The machine is gone; rebuild it" |
| **Cost over time** | Grows; degrades performance if kept long | Managed storage cost |

Three consequences worth internalizing:

1. **Storage behavior is not free.** Snapshot chains grow as the guest writes, and long-lived snapshots consume real host disk space and add work to every disk operation. "I'll just keep a snapshot from six months ago" is how a host runs out of storage and a VM crawls.
2. **A chain is fragile.** Delete or corrupt one file in the chain and the later ones may become unusable. One object's failure can take the machine with it.
3. **Snapshots and backups solve different problems, so you need both.** Snapshot before you experiment. Back up so the machine survives the storage it lives on. Neither substitutes for the other, and a strategy that includes only snapshots is a strategy with no answer for a dead disk.

## 5. Images and Templates

A **VM image** is a virtual machine's disk in a distributable form — a file you can copy and boot. A **template** is a VM prepared to be cloned repeatedly as the starting point for new machines.

Because Introduction's point holds — a powered-off VM is files — a fully installed, fully configured machine is something you can hand to someone else. That gives you:

- **Reproducibility.** Everyone in a class starts from a byte-identical machine. "It works on mine" becomes a diagnosable claim rather than a shrug.
- **Speed.** Deploying a configured machine is a copy-and-boot instead of an install-and-configure.
- **Consistency.** Twenty servers cloned from one template are genuinely the same, which makes both operating them and securing them tractable.
- **Disposability.** If the environment is a template away, breaking one is cheap.

This is why security distributions like Kali Linux and deliberately vulnerable practice machines are published as downloadable VM images: the whole point is that you get the *same* machine everyone else is working with.

Two cautions, both real:

- **Trust the source.** An image is an entire operating system prepared by someone else, and you are about to run it. Where it came from is a genuine security question, not a formality.
- **Clone drift and baked-in secrets.** Clones from a template share whatever was in the template — including any credentials, keys, or host identity left in it. Cloning a machine with a password in it produces twenty machines with that password in them.

## 6. Isolation — Honestly

Virtualization is the standard tool for containing risky work, and the reason is real: a guest OS runs its own kernel, its own processes, and its own filesystem, with no ordinary path from inside the guest to the host's memory or files. From the guest's perspective there is simply nothing there to reach.

That property is what makes all of these possible:

- **Isolated lab environments** — attack tools, unusual configurations, and deliberately broken software kept off your working machine
- **Malware-analysis preparation** — an environment you can afford to lose, and revert when you're done
- **Deliberately vulnerable machines** — running software with known holes, on purpose, without exposing anything you care about
- **Configuration testing** — changes that would be disruptive on a real system
- **Development environments** — a machine matching production rather than matching your laptop

Now the part that gets left out, and must not be:

> **VM isolation is a strong boundary, not an absolute guarantee.** How strong it is in your particular case depends on the virtualization software and its vulnerabilities, on how you configured the VM, on the security of the host underneath it, and on what you connected the VM to.

Every one of those is something you control or can check:

- **Implementation.** The hypervisor is software, and software has flaws. A vulnerability in the virtualization layer is a vulnerability in the boundary itself.
- **Configuration.** Shared folders, shared clipboard, drag-and-drop, and USB passthrough are deliberate holes you punch through the boundary for convenience. Each one is a path between guest and host that you enabled.
- **Host security.** The boundary protects the host from the guest. It does nothing about a host that was already compromised — and a compromised host sees everything in every VM on it.
- **Network reach.** A "contained" VM in bridged mode is on your real network with your real machines. Section 8 of Core Concepts was not a formality.

So the correct posture is not "it's a VM, therefore it's safe." It is: *a VM is the right tool, and it is one layer among several — configure it deliberately, keep the host patched, and don't hand it more reach than the task needs.*

## 7. Virtual Machines vs. Containers

You will see containers described as "lightweight VMs". That description is convenient and wrong, and it leads people to the wrong conclusions about what they're getting.

The difference is one thing, from which everything else follows: **a VM runs its own operating system kernel; a container shares the host's.**

```
VIRTUAL MACHINES                       CONTAINERS

  App    App                             App     App
  Guest OS (own kernel)                  ── no guest kernel ──
  Guest OS (own kernel)                  Container runtime
  Hypervisor                             HOST OS (one shared kernel)
  Physical hardware                      Physical hardware
```

A container is an *isolated application environment*: its own filesystem view, its own process view, its own network view, and limits on the resources it may use — but the processes inside it are ordinary processes of the host kernel, which is what starts, schedules, and enforces limits on them. On Linux this is built from kernel features (namespaces for the separate views, cgroups for the limits), not from a hypervisor.

What follows from that single difference:

| | Virtual machine | Container |
|---|---|---|
| **Kernel** | Its own | Shares the host's |
| **What's virtualized** | A machine | An application environment |
| **Startup** | Boots an OS — seconds to a minute | Starts processes — typically sub-second |
| **Size** | Gigabytes (a whole OS) | Often tens or hundreds of megabytes |
| **Different OS than the host?** | Yes — that's a core capability | No: it needs the host's kernel |
| **Isolation boundary** | Hypervisor + separate kernel | Host kernel features |
| **Fits best** | Different or full operating systems, strong separation | Packaging and running applications reproducibly, at density |

The practical rule:

- **Use a VM** when you need a *different* operating system, a full OS environment, or a stronger separation boundary — a Windows guest on a Linux host, a Kali machine, a malware sandbox.
- **Use a container** when you need the *same* kernel and want an application to run identically everywhere, start fast, and pack densely — a web service and its dependencies.

And because it clarifies rather than complicates: running Linux containers on Windows or macOS works by running them inside a Linux **virtual machine** on that host. The kernel has to come from somewhere, and if the host isn't providing a Linux kernel, virtualization supplies one. That's the strongest evidence that a container is not a small VM — it is a thing that *needs* a compatible kernel, borrowed from a VM when the host can't lend it.

## 8. Why This Matters for Security

**What virtualization enables.** Nearly every environment you will use to learn or practice security is virtual:

- **Security labs** — an attacking machine and a target machine on one laptop, on a host-only network, reachable only to each other.
- **CTF environments** — challenge machines distributed as images or run as instances, identical for every competitor.
- **Malware research** — analysis in a machine you can revert, with no route to anything you care about.
- **Network testing** — several virtual hosts and virtual networks without buying a single cable.
- **Vulnerable machines** — running knowingly insecure software safely enough to learn from it.
- **Snapshots and rollback** — the reason you can afford to break things deliberately.
- **Infrastructure** — cloud servers are virtual machines; understanding VMs is understanding what a cloud provider actually rents you.

**What virtualization risks.** The same layer is also attack surface. This is foundational awareness, not a how-to:

- **Hypervisor vulnerabilities.** The virtualization layer is software. A flaw in it is a flaw in the boundary every VM on the host depends on — which is why hypervisor patches are treated with unusual seriousness.
- **VM escape.** The name for a guest breaking out of its isolation and affecting the hypervisor or host. It is rare, valuable, and heavily researched — and its existence is precisely why "it's in a VM" is a strong mitigation rather than a guarantee. *This module teaches what it is and why it matters. It does not teach how to do it, and you do not need that to reason correctly about risk.*
- **Insecure VM configuration.** Shared folders, clipboard sharing, USB passthrough, and unnecessary bridged networking each remove some of the separation you were relying on.
- **Exposed management interfaces.** Hypervisors and virtualization platforms are administered through consoles and APIs. Someone with access to that interface controls every VM on the platform — can start them, stop them, copy their disks, or read their consoles — without ever attacking a guest. This is a favourite target precisely because it skips the boundary entirely.
- **Weak credentials.** Especially on management interfaces and on cloned machines carrying a template's baked-in password.
- **Excessive resource allocation.** A resource-exhaustion problem: one VM permitted to consume everything can degrade every other VM on the host, and "the service is unavailable" is a security outcome, not merely an operations one.
- **Unpatched guests and hosts.** Every VM is a full operating system with a full patching obligation. A forgotten lab VM on your network is a real, running, unpatched machine — being virtual makes it easy to forget, not harmless.

Notice how much of this is Cybersecurity Fundamentals rather than anything exotic: identity, exposure, least privilege, patching, availability. Virtualization doesn't replace those questions. It adds one more layer to ask them about.

## 9. Linux as Host and as Guest

You have spent this roadmap learning Linux, and it can occupy either role:

- **Linux as host.** A Linux machine running KVM is a hypervisor with Windows or other Linux guests on top of it — the standard arrangement underneath most cloud infrastructure.
- **Linux as guest.** An Ubuntu or Kali VM on a Windows or macOS laptop — the standard student setup.

The important habit, and it goes back to Introduction's host/guest distinction: **commands you run inside the guest act on the guest.** When you run `ls`, `whoami`, `id`, or `chmod` inside a Kali VM:

- `ls` lists a directory in the *guest's* filesystem — which physically lives inside the virtual disk file on the host.
- `whoami` and `id` report your identity in the *guest*, unrelated to the account you're logged into on the host.
- `chmod` changes permissions the *guest's* kernel enforces. The host's kernel is not involved and doesn't know.
- Even `uname -a`, which asks the kernel about itself, reports the *guest's* kernel — because that's the kernel those processes are running on.

Nothing you learned in Linux Fundamentals changes. What changes is knowing precisely which machine you're changing.

## 10. Where This Sits on Top of Operating Systems

Operating Systems taught you what an OS provides: processes, memory, filesystems, permissions, devices, networking. This module's whole content is that a VM provides *virtual versions of exactly those*, and that the guest OS manages them believing they're real.

```
Guest process                  an ordinary process, unaware of any of this
      ↓  system call
Guest OS                       schedules it, gives it memory, checks its permissions,
                               serves its files, handles its network — all as usual
      ↓  operations on virtual devices
Virtual CPU / virtual memory / virtual disk / virtual NIC
      ↓
Hypervisor                     schedules vCPUs onto real cores, maps guest memory to
                               real memory, turns disk writes into writes in a file,
                               connects the virtual NIC per its network mode
      ↓
Physical resources             one CPU, one bank of RAM, one SSD, one network card
```

Every OS concept you know still applies inside the guest, unchanged. Virtualization adds a layer *below* the OS, not inside it — which is exactly why an unmodified Ubuntu installs and runs in a VM without knowing anything about it.

## 11. Practical Exercise A: Inspect a Real VM Configuration

Do this on your own machine, in whatever virtualization software you use. This platform's terminal has no hypervisor commands and none are invented here — the real thing is a few clicks away, and reading a VM's settings page is a skill worth having.

Open the settings of any VM you have (or a VM you create for the purpose) and find each of these. For each one, say which section of Core Concepts explains what you're looking at:

1. **Virtual CPU count.** How many vCPUs is it assigned? How many logical processors does your host actually have? Is the total across all your VMs more than that? (Core Concepts §5, §9.)
2. **Virtual RAM.** How much is assigned? What fraction of the host's total is that? What's left for the host itself? (Core Concepts §6, §9.)
3. **Virtual disk.** What size does the guest see, what file on the host holds it, and is it fixed or dynamically allocated? Compare the size the guest reports with the size of the file on the host — if they differ, explain why. (Core Concepts §7.)
4. **Network mode.** NAT, bridged, or host-only? Now predict, before testing: can this VM reach the internet? Can another device on your network reach it? (Core Concepts §8.)
5. **Shared folders / clipboard / USB passthrough.** Which of these are enabled? For each enabled one, state what boundary it opens. (Section 6 of this lesson.)
6. **Snapshots.** How many does this VM have, and how old is the oldest? What would you lose if the host's disk failed right now? (Sections 3–4.)

If you don't yet have virtualization software installed, work through the questions on the scenario in Section 13 instead — the reasoning is the point, not the clicking.

## 12. Practical Exercise B: Real Virtual Machines, on This Platform

This platform has a real, interactive lab that puts you in front of actual virtual machines: **Cloud Basics: Tour the Account**, in the Cloud Security labs. A cloud account is virtualization at scale — the "instances" you list there are virtual machines running on a provider's hardware, and the lab lets you inspect their configuration and network placement exactly as this module describes.

Work through the whole lab, but pay particular attention to three of its commands, which are this module's material directly. Here is what they actually return in that lab:

```
list-vms

NAME        STATE     SUBNET      SEC GROUP PUBLIC IP       SIZE
──────────────────────────────────────────────────────────────────
web-01      running   public-a    web-sg    203.0.113.10    small
web-02      running   public-a    web-sg    203.0.113.11    small
app-01      running   private-a   app-sg    —               medium
```

Read that as a virtualization inventory, not a cloud curiosity. Three virtual machines, each in a **state** from the lifecycle in Core Concepts §11, each with a **size** (the provider's shorthand for a vCPU/RAM allocation — Core Concepts §5–6), each attached to a virtual network segment, and each either reachable from the internet or not.

```
get-vm web-01

VM: web-01
  State:          running
  Size:           small
  Subnet:         public-a
  Security group: web-sg
  Public IP:      203.0.113.10  (internet-reachable via public IP)
  Nginx front end.
```

```
get-vm app-01

VM: app-01
  State:          running
  Size:           medium
  Subnet:         private-a
  Security group: app-sg
  Public IP:      —  (private — no public IP)
  Application server.
```

Answer these from that output before moving on:

1. Which of the three VMs is reachable from the internet, and which piece of the configuration tells you that?
2. `app-01` has no public IP. Relate that to one of the network modes in Core Concepts §8 — which one does "no route in from outside, but reachable within its own network" most resemble?
3. `web-01` and `app-01` have different sizes. In terms of Core Concepts §5–6, what is a "size" actually deciding, and why would a front-end and an application server reasonably differ?
4. All three run on hardware you will never see or touch. Which layer of Introduction §8's stack is the provider operating, and which layers are you responsible for?
5. The lab's `network` command shows the account's virtual network — a VPC with public and private subnets. That is virtual networking at the same conceptual level as Core Concepts §8. What is the cloud equivalent of choosing "bridged" versus "host-only" for a machine?

The lab's other commands (identities, storage, and its `audit` scan) go beyond this module into cloud security proper — worth doing, and directly relevant to Section 8's risk list, especially the parts about exposure and weak credentials.

## 13. Scenario: Build a Lab on a Real Laptop

A student has exactly one machine:

```
Windows 11 host
16 GB RAM
8 logical CPU threads
512 GB SSD (about 200 GB already used)
```

They want a **Kali Linux VM** for tooling and a **deliberately vulnerable Ubuntu VM** to practice against, while continuing to use Windows for everything else.

There is no single correct configuration here, and anyone who hands you one without asking what you're doing is guessing. Work through each decision and justify it:

1. **RAM.** How much for Kali, how much for the vulnerable VM, how much stays with Windows? Remember Windows plus a browser plus the virtualization software all need real memory, and that memory contention is the failure mode that hurts (Core Concepts §9). What happens if you assign 8 GB to each VM?
2. **CPU.** How many vCPUs each? Does giving Kali all 8 make it faster, and why or why not (Core Concepts §5)? Does it matter that both VMs are rarely busy at the same instant?
3. **Storage.** Two virtual disks on ~300 GB of free space. Fixed or dynamic, and what do you check regularly if you choose dynamic (Core Concepts §7)?
4. **Network mode.** The two VMs must reach each other. The vulnerable machine must not be reachable from the household or campus network. Kali needs to install updates sometimes. Which mode, or which combination, and what do you change when you need Kali online (Core Concepts §8)?
5. **Snapshots.** When exactly do you take one — and what's your answer to "the SSD died, where's the vulnerable VM's data?" (Sections 3–4.)
6. **Security.** The vulnerable VM is deliberately insecure and running. List three things about this setup that would make you uneasy, and what you'd do about each (Sections 6 and 8).
7. **Type 1 or Type 2?** They read that data centers use Type 1. What do you tell them (Core Concepts §3)?
8. **Would a container do instead?** For the vulnerable target specifically — argue both sides using Section 7, then commit to an answer and say what your answer depends on.

Compare your reasoning with a classmate's if you can. Differences will almost always come down to different assumptions about what the machine is *for*, which is exactly the point.

## 14. Common Mistakes

**Treating a snapshot as a backup.** The most consequential mistake in this lesson. Same storage, dependent on the original, gone when the disk is gone.

**Keeping snapshots forever.** They grow, they cost disk, they slow the VM, and a long chain is a fragile chain.

**Assuming a VM is absolutely secure.** It's a strong boundary that depends on the hypervisor's soundness, your configuration, the host's security, and what you connected it to.

**Enabling shared folders and clipboard "for convenience" in an analysis VM.** Those are deliberate paths through the boundary you set up specifically to avoid.

**Running a deliberately vulnerable machine in bridged mode.** You have put a knowingly insecure host on a real network with real machines.

**Calling a container a lightweight VM.** It shares the host's kernel. That single fact governs what it can and cannot do, including which operating systems it can run.

**Forgetting a VM exists.** An unpatched machine is unpatched whether or not it's virtual, and a forgotten one never gets updated.

**Trusting a downloaded image because it's "just a VM".** It's an entire operating system, prepared by someone else, that you are about to boot.

## 15. Knowledge Check

1. What is a snapshot, and name three situations where it's the right tool?
2. Why isn't a snapshot automatically a backup? Give at least three concrete differences.
3. What makes a VM image or template valuable, and what's one real risk of cloning from a template?
4. Why are VMs useful for security labs — and what, precisely, does VM isolation *not* guarantee?
5. Name three factors that determine how strong a given VM's isolation actually is.
6. Why aren't containers simply lightweight VMs? State the one structural difference and two consequences of it.
7. You need to run a Windows application on a Linux machine. VM or container, and why?
8. What is a VM escape, and why does knowing the concept change how you evaluate "I ran it in a VM"?
9. Why is an exposed hypervisor management interface such a serious problem, given that no individual VM was attacked?
10. You run `whoami` inside a Kali VM on a Windows laptop. Whose identity does it report, and why?

## 16. Key Takeaways

- A snapshot is a return point stored with the VM; a backup is an independent copy stored elsewhere. You need both, for different failures.
- Snapshot chains grow and are interdependent — long-lived snapshots cost storage, cost performance, and add fragility.
- Images and templates make environments reproducible and disposable, which is why security distributions and practice machines are distributed that way — and why image provenance and baked-in secrets are real concerns.
- VM isolation is a strong boundary whose strength depends on the hypervisor's soundness, your configuration, the host's security, and the VM's network reach. It is not an absolute guarantee.
- A container shares the host's kernel; a VM runs its own. Everything else — size, startup speed, which operating systems are possible — follows from that.
- Virtualization is what makes security labs, CTFs, malware analysis, and cloud infrastructure possible, and it brings its own attack surface: the hypervisor, the configuration, and above all the management interface.
- Commands inside a guest act on the guest. The host is a separate machine with separate identity, separate permissions, and a separate kernel.
- A VM provides virtual versions of exactly the resources Operating Systems taught you the OS manages — which is why an unmodified OS runs in one without knowing.

## 17. What's Next

This is the last lesson in Virtualization, and the last module in the Beginner track. You now have the model underneath every lab, VM, and cloud instance you'll use from here on: what a hypervisor does, what a vCPU and a virtual disk really are, how a VM reaches a network, what a snapshot protects you from and what it doesn't, and where the boundary you're relying on actually comes from.

Everything ahead — scanning networks with Nmap, capturing traffic in Wireshark, attacking web applications, working through Red Team technique — happens inside environments built exactly this way. When a lab tells you "the target is at 10.0.2.15 on a host-only network", you now know precisely what that sentence means, and precisely what it does and does not keep contained.
