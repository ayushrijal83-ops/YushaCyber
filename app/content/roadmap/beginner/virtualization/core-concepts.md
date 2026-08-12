# Virtualization Core Concepts

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain the difference between Type 1 and Type 2 hypervisors, and describe a real tradeoff rather than declaring one "better"
- explain what a vCPU is, and why "1 vCPU = 1 physical core" is wrong
- explain how a VM's memory relates to the host's physical memory, and how that is a *second* layer of translation on top of the virtual memory you already know
- explain what a virtual disk is and where a guest's data physically lives
- explain how a VM's network traffic reaches the outside world, and how NAT, bridged, and host-only modes differ
- reason about resource allocation, overcommitment, and contention on a real, finite machine
- describe where virtualization overhead comes from without exaggerating it

## 2. Why This Matters

This is the lesson where "a VM is a computer inside a computer" stops being enough. Every practical decision you will make about virtual machines — how much RAM to give one, how many to run at once, why one is crawling, why it can't reach the internet, why another machine on the network can't reach *it* — comes down to the mechanisms in this lesson. Get these right and virtualization stops being mysterious; it becomes a resource-allocation problem you can reason about.

## 3. Hypervisors: Two Families

Introduction defined the hypervisor as the layer that creates virtual hardware and allocates real resources. Hypervisors are conventionally split into two types by *what they run on*.

**Type 1 — runs directly on the physical hardware.** There is no general-purpose operating system underneath it. The hypervisor itself is what boots, and every operating system on the machine is a guest.

```
GUEST OS   GUEST OS   GUEST OS
    └──────────┼──────────┘
          HYPERVISOR              ← boots directly on the hardware
        PHYSICAL HARDWARE
```

Examples: VMware ESXi, Xen, Microsoft Hyper-V, and Proxmox VE / KVM on Linux. This is what runs in data centers and underneath cloud providers.

**Type 2 — runs on top of a host operating system.** You boot Windows, macOS, or Linux normally, then install virtualization software as an application. Its VMs are managed by that software, which is itself running on the host OS.

```
        GUEST OS      GUEST OS
            └────┬────┘
           HYPERVISOR            ← an application on the host OS
          HOST OPERATING SYSTEM
          PHYSICAL HARDWARE
```

Examples: VirtualBox, VMware Workstation and Fusion, Parallels Desktop. This is what a student runs on a laptop.

### The tradeoff, honestly

Neither type is universally better. They are built for different situations.

| | Type 1 | Type 2 |
|---|---|---|
| **Runs on** | Bare hardware | A host OS |
| **Competes with** | Nothing — it owns the machine | Everything else on your desktop |
| **Typical setting** | Servers, data centers, cloud | Laptops, workstations, labs |
| **Typical use** | Running many VMs continuously, as the machine's whole purpose | Running a few VMs alongside your normal work |
| **Setup cost** | Dedicates the machine; you need another computer to manage it | Install like any other application |
| **Host OS available while running?** | There isn't one | Yes — that's the point |

The instinct "Type 1 is faster, so Type 1 is better" misses what you'd give up: a Type 1 hypervisor on your laptop means your laptop no longer runs your web browser, your notes, or your music. For learning and lab work, that trade is usually a bad one, which is why Type 2 is the normal choice for a student and not a compromise you should feel bad about.

> **A caution about crisp classification.** The two-type model is a useful teaching frame, not a law. Hyper-V is a real example of the blur: once it's enabled on Windows, the hypervisor is what's underneath, and the Windows you're using becomes a privileged partition running on top of it — even though you interact with it like an application. KVM is another: it's a module inside the Linux kernel that turns a running Linux system into a hypervisor, which makes it defensible to describe as either type depending on which fact you emphasize. Learn the model, but don't argue with reality when it doesn't fit neatly.

## 4. Virtual Hardware

When you create a VM, you don't install hardware — you *configure* it. Every VM gets a set of virtual devices, and the guest OS detects them at boot exactly the way an OS detects real hardware.

```
PHYSICAL MACHINE                         VM A                    VM B
  CPU (8 logical threads)   ────────►    2 vCPUs                 4 vCPUs
  RAM (16 GB)               ────────►    4 GB virtual RAM        6 GB virtual RAM
  SSD (512 GB)              ────────►    60 GB virtual disk      80 GB virtual disk
  Network card              ────────►    virtual NIC             virtual NIC
```

Read the arrows as "provided from", not "carved out and reserved forever". The rest of this lesson is really four answers to the same question — *how, exactly, does the hypervisor provide each of these?* — plus one answer to *what happens when you ask for more than there is?*

## 5. CPU Virtualization

A **vCPU** (virtual CPU) is a virtual processor presented to a guest. A VM configured with 4 vCPUs boots a guest OS that detects four processors and schedules its processes across them, exactly as it would on physical hardware.

Here is the part people get wrong. **A vCPU is not a physical core reserved for that VM.** It is a unit of execution that the hypervisor schedules onto whatever physical CPU resources are available, when there is work to run.

That should feel familiar. In Operating Systems you learned that an OS runs far more processes than it has cores by giving each one short time slices and switching between them. The hypervisor does the same thing one level down:

```
Guest process          scheduled by the GUEST OS onto...
      ↓
vCPU                   scheduled by the HYPERVISOR onto...
      ↓
Physical CPU core      executes real instructions
```

Two layers of scheduling, each unaware of the other's decisions. The guest OS believes it controls when its processes run on "its" CPUs; in reality the hypervisor decides when those vCPUs get physical execution time at all.

Consequences that follow directly from this:

- **You can assign more total vCPUs across all VMs than the host has logical processors.** Three VMs with 4 vCPUs each on an 8-thread laptop is legal and often works fine, because VMs are idle most of the time.
- **They still compete.** When all three want to compute at once, they wait on each other. Nothing broke; there is simply more demand than supply.
- **More vCPUs is not automatically faster.** A VM with 8 vCPUs on a busy 8-thread host can be *slower* than the same VM with 2, because the hypervisor may have to find execution time for more virtual processors before the guest makes progress. "Give it everything" is not a strategy.

Modern processors help enormously here. **Hardware-assisted virtualization** (Intel VT-x, AMD-V) provides CPU-level support for running guest code directly on the processor, rather than the hypervisor having to interpret it in software. This is why VMs today run at close to native speed for ordinary compute, and it's why enabling virtualization support in firmware/BIOS is usually the first troubleshooting step when a VM refuses to start or runs unbearably slowly.

## 6. Memory Virtualization

Each VM is configured with an amount of RAM. The guest OS finds that much memory at boot and manages it normally — allocating it to processes, paging, everything Operating Systems taught you.

The key fact: **the memory the guest thinks is physical memory is itself an abstraction.** The hypervisor maintains a mapping from what the guest calls physical addresses to actual addresses in the host's real RAM.

Do not confuse this with the virtual memory you already learned. They are two different translations, stacked:

```
Guest process's virtual address
      ↓   translated by the GUEST OS's virtual memory system  (Operating Systems, Core Concepts §8)
"Guest physical" address        ← the guest believes this is real RAM. It is not.
      ↓   translated by the HYPERVISOR
Host physical address           ← actual bytes in actual RAM chips
```

Doing that second translation in software would be expensive, so modern CPUs implement it in hardware (Intel calls it Extended Page Tables, AMD calls it Nested Page Tables). You don't need the mechanism for this module; you need the shape — *two layers of address translation, and only the bottom one touches real memory.*

And the fact that everything else depends on:

**Assigning 8 GB of RAM to each of three VMs does not create 24 GB of RAM.** It creates three promises against one finite pool. On a 16 GB laptop, those promises cannot all be kept at once. What happens then is Section 9.

## 7. Virtual Disks

A **virtual disk** is a storage device presented to a guest, which the guest partitions, formats, and uses as an ordinary drive. Physically, it is normally a **file** (sometimes several) on the host's storage — a *disk image*.

```
Guest sees:     /dev/sda, 60 GB, ext4, mounted at /
Host sees:      one file, e.g. kali-lab.vdi, sitting in a folder
```

Common image formats, so you recognize them: `.vdi` (VirtualBox), `.vmdk` (VMware), `.vhdx` (Hyper-V), `.qcow2` (QEMU/KVM). Different products, same idea.

**Allocation.** When you create a 60 GB virtual disk you choose, in effect, between two behaviors:

- **Fixed / pre-allocated** — the full 60 GB file is created up front. It consumes 60 GB of host storage immediately, whether or not the guest has written anything.
- **Dynamically allocated / thin-provisioned** — the file starts small and grows as the guest writes. A freshly installed guest might occupy 12 GB even though the guest reports a 60 GB disk.

Dynamic allocation is convenient and it is also how people run out of disk space by surprise: five VMs with 60 GB disks on a 512 GB SSD look fine right up until they all fill up. The *promise* is 300 GB; the *host* has 512 GB minus everything else on it. Same arithmetic problem as memory, different resource.

**Persistence.** Data written by the guest lands in that image file and survives a guest reboot exactly as data on a physical disk would — the guest is not a temporary scratchpad by default. What makes VM storage feel different is that the whole disk is one host-level object: copy the file and you have copied the machine's entire filesystem; delete it and the machine's data is gone regardless of how carefully the guest was shut down.

## 8. Virtual Networking

Your VM has a virtual NIC. The host has one physical network card. Something has to connect them, and how it's connected changes what the VM can reach and what can reach it. This builds directly on Computer Networking — the same IP addresses, gateways, and NAT, one layer down.

```
GUEST OS
   ↓  ordinary network traffic
VIRTUAL NIC             the interface the guest configures and sees
   ↓
VIRTUAL SWITCH / NETWORK LAYER      provided by the hypervisor — this is where the mode applies
   ↓
PHYSICAL NIC            the host's real network card
   ↓
NETWORK
```

The mode you choose determines what happens at that middle layer.

**NAT.** The hypervisor gives the VM an address on a private network it manages, and translates the VM's outbound traffic to appear as if it came from the host. This is exactly the NAT you met in Computer Networking, performed by the virtualization software rather than a home router.

- The VM can reach the internet.
- Other machines on your real network cannot reach the VM directly — there is no route to it, and nothing on the LAN has an address for it.
- Usually the default, and usually the right default.

**Bridged.** The virtual NIC is attached to the physical network as though the VM were a separate physical machine plugged into the same switch. It typically gets its own address from the same network the host is on.

- The VM is a peer on the real network: it can reach other machines, and they can reach it.
- Necessary when something on the LAN needs to connect *to* the VM.
- It also means the VM is exposed to the LAN with whatever services it happens to be running — a real consideration, not a footnote, and one Hands-on Practice returns to.

**Host-only.** The virtual NIC is attached to a network that exists only between the host and its VMs. No route out.

- The VM and host can talk to each other; VMs on the same host-only network can talk to each other.
- No internet, no LAN access, in either direction.
- The usual choice for a deliberately contained lab: two VMs that need to see each other and nothing else.

The practical upshot: **"my VM has no internet" and "nothing can reach my VM" are often not faults at all — they are the network mode doing precisely what it was configured to do.** Check the mode before you debug anything else.

## 9. Allocation, Overcommitment, and Contention

Now put Sections 5–7 together. The host has a fixed amount of everything:

```
Host:   8 logical CPU threads    16 GB RAM    512 GB SSD
```

Configuring VMs is dividing that up — except that the tools will happily let you promise more than exists. Promising more of a resource than physically exists is called **overcommitment**, and it isn't a mistake by itself. It's a bet that VMs won't all want everything at the same moment, and most of the time that bet is correct, because most VMs are idle most of the time.

What happens when the bet fails is **contention** — more demand than supply — and it looks different per resource:

- **CPU contention:** vCPUs wait for physical execution time. Everything gets slower; nothing fails outright.
- **Memory contention:** far more serious. Memory can't be time-sliced the way CPU can — a process needs its bytes *now*. The system responds by reclaiming memory (paging guest memory out to disk, or asking guests to give some back), and performance falls off a cliff, because disk is orders of magnitude slower than RAM. In the worst case a VM fails to start or the host becomes unusable.
- **Storage contention:** several guests issuing reads and writes to the same physical disk share its throughput; each one sees slower I/O.
- **Network contention:** all the VMs' traffic ultimately crosses one physical NIC and one internet connection.

Two rules of thumb that follow, neither of them magic numbers:

1. **Leave the host real headroom, especially memory.** The host OS still has to run — with its own processes, its own caches, and the virtualization software itself. A 16 GB laptop does not have 16 GB to give away.
2. **Assign what the guest actually needs, not the maximum you can.** Oversized VMs waste resources that another VM (or the host) has a genuine use for, and as Section 5 showed, oversized vCPU counts can actively hurt.

## 10. Performance: The Honest Version

Two exaggerations to avoid, in both directions.

**"Virtualization is basically free."** Not quite. There is real overhead: the hypervisor consumes CPU and memory itself; some operations, especially I/O, take an extra step through the virtualization layer; and every resource is shared with the host and the other VMs.

**"VMs are always much slower."** Also wrong, and more outdated. Hardware-assisted virtualization means guest CPU instructions largely execute directly on the physical processor. **Paravirtualized drivers** — guest drivers written to cooperate with the hypervisor rather than pretend to be legacy hardware, shipped as guest additions or tools packages — remove most of the remaining I/O cost. For typical workloads, modern virtualization is efficient enough that overhead is not the thing you'll notice.

What you *will* notice, and what people usually misdiagnose as "virtualization overhead", is contention: a VM that feels sluggish is far more often short of memory, or sharing eight threads with three other busy VMs, than it is suffering from the cost of the abstraction.

## 11. The VM Lifecycle

A VM moves through states you should be able to name, because tools use these words and they aren't quite the same as a physical machine's:

- **Created** — configured (vCPUs, RAM, virtual disk, network mode) but never started. Files exist; nothing runs.
- **Powered on / running** — consuming real CPU and real memory, guest OS booted.
- **Paused / suspended** — execution frozen. Its memory contents are preserved (written to disk on suspend) so it can resume exactly where it stopped, rather than booting again. Different from shutting down: the guest doesn't know it happened.
- **Powered off** — no execution, no memory in use. Only files remain.
- **Deleted** — the configuration and, if you say so, the virtual disk file. Deleting the disk deletes the machine's entire filesystem, and no guest-level care can undo it.

Snapshots and templates — the two operations that make this lifecycle genuinely more powerful than a physical machine's — are the subject of Hands-on Practice.

## 12. Common Mistakes

**Believing 1 vCPU equals 1 dedicated physical core.** It's a schedulable unit, not a reservation. Section 5.

**Assigning maximum resources to every VM.** More vCPUs than the workload needs can slow it down, and memory promised to an idle VM is memory a busy one can't have.

**Thinking configured memory creates memory.** Three 8 GB VMs on a 16 GB laptop is a promise the machine cannot keep. Section 9.

**Confusing guest virtual memory with hypervisor memory virtualization.** Two distinct translation layers, stacked. Section 6.

**Debugging a network problem without checking the network mode first.** A host-only VM has no internet *by design*. A NAT VM being unreachable from your phone is not a bug.

**Assuming dynamic disks are free.** They grow. Five thinly provisioned 60 GB disks can genuinely fill a 512 GB SSD.

**Blaming "virtualization overhead" for every slow VM.** Usually it's contention, and contention has a cause you can find and fix.

## 13. Practice

Reasoning exercises — work them through before reading Hands-on Practice.

1. **Do the arithmetic.** A laptop has 8 logical CPU threads and 16 GB of RAM. You configure three VMs: 4 vCPUs / 8 GB, 2 vCPUs / 4 GB, and 2 vCPUs / 4 GB. Total vCPUs assigned? Total RAM assigned? Which of those two totals is the more dangerous overcommitment, and why does the answer differ per resource?
2. **Pick the mode.** For each, choose NAT, bridged, or host-only, and justify it in one sentence: (a) a Kali VM that needs to download tool updates from the internet; (b) a Kali VM that must attack a deliberately vulnerable VM on the same laptop, with neither touching the outside world; (c) a VM running a small web service that a colleague on the same office network needs to open in their browser.
3. **Find the layer.** A VM's disk-heavy task takes three times longer than the same task on the host. Name two distinct possible causes from this lesson, and say what you'd check first to tell them apart.
4. **Trace an address.** A process inside a guest reads a variable from memory. List, in order, the translations that happen before real RAM is touched. (Section 6.)
5. **Explain the tradeoff.** A student says "data centers use Type 1, so I should install Type 1 on my laptop." Give them the specific reason that's usually a bad idea — not "Type 2 is easier", but what they would concretely lose.

## 14. Knowledge Check

1. What is the difference between a Type 1 and a Type 2 hypervisor, and what does each one run on?
2. Why is "1 vCPU = 1 physical CPU core" wrong? What is a vCPU actually?
3. Explain the two layers of address translation between a guest process's memory access and a physical RAM chip.
4. Why doesn't assigning 8 GB of RAM to a VM create additional physical RAM? What actually happens when several VMs' promises exceed the host's memory?
5. Where does a guest's filesystem physically live on the host, and what's the practical difference between a fixed and a dynamically allocated virtual disk?
6. Why might NAT and bridged networking produce different behavior for the same VM running the same service?
7. What is overcommitment, why is it not automatically a mistake, and what is contention?
8. Name one real source of virtualization overhead and one technology that reduces it.

## 15. Key Takeaways

- Type 1 hypervisors run directly on hardware (servers, cloud); Type 2 run on a host OS (laptops, labs). Different tools for different situations, not a ranking.
- A vCPU is a schedulable unit the hypervisor places onto physical CPU time — two layers of scheduling, guest and hypervisor, neither aware of the other.
- A guest's "physical" memory is itself mapped to real host memory: guest virtual → guest physical → host physical. Only the last one is real RAM.
- A virtual disk is normally a file on the host. Copying it copies the machine; deleting it destroys the machine's data.
- Network mode decides reachability: NAT (out only, hidden), bridged (a peer on the real network, reachable), host-only (contained, no route out).
- Overcommitment is a bet that VMs won't all peak at once; contention is that bet failing. CPU contention slows things; memory contention breaks things.
- Modern virtualization is efficient — hardware assistance and paravirtualized drivers keep overhead low. Most "slow VM" problems are contention, not abstraction cost.

## 16. What's Next

**Hands-on Practice** turns this into judgment. You'll meet snapshots (and the important reason a snapshot is not a backup), VM images and templates, what isolation genuinely gives you and what it doesn't, how containers differ from VMs and why "lightweight VM" is the wrong way to think about them — and then you'll use all of it, on a real security-lab scenario and on this platform's real cloud lab, where you'll inspect actual virtual machines and reason about their exposure.
