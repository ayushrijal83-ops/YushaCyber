# Introduction to Virtualization

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what virtualization actually is, without reciting a definition
- explain the difference between a physical resource and a virtual one
- explain what a virtual machine is, in terms of what actually exists on the physical computer
- use the words **host** and **guest** correctly, and explain why the distinction matters
- describe what a hypervisor sits between, and why something has to sit there at all
- read the physical hardware → hypervisor → VM → guest OS → application stack as a description of a real mechanism, not a diagram to memorize

## 2. Why This Matters

Almost every practical environment in security is virtual. The vulnerable machine you attack in a CTF, the Kali box you attack it *from*, the malware sandbox an analyst detonates a sample in, the cloud servers running a company's production systems — all of them are virtual machines running on physical hardware they don't own outright and usually don't know anything about.

That means "run this in a VM" is advice you will receive constantly, and following it without understanding it is how people get hurt. A student who thinks a VM is a magic isolation box will run malware in one, take no other precautions, and be genuinely surprised when something goes wrong. A student who understands what the virtualization layer is actually doing — what it separates, what it shares, and where its guarantees come from — makes better decisions about the same setup.

This module is that understanding. It is not a click-through tutorial for one particular product; it is the model underneath all of them.

## 3. The Problem Virtualization Solves

Start from what you already know. In Operating Systems you learned that one OS manages one machine's hardware: its CPU, memory, disks, and devices. That is the traditional arrangement — **one physical computer, one operating system**:

```
HARDWARE  →  ONE OPERATING SYSTEM  →  applications
```

That arrangement has real problems the moment you want more than one thing from a machine:

- **Waste.** A physical server bought to run one application usually runs it at a fraction of its capacity. The rest of the CPU and memory sit idle, powered and paid for.
- **Fragility.** Everything on that machine shares one OS. One application that corrupts a shared file, exhausts memory, or crashes the kernel affects everything else on the box.
- **Inflexibility.** You want to test something on a different operating system, or on a clean system with nothing else installed. With one OS per machine, that means another machine.
- **Irreversibility.** You want to try something destructive and then undo it completely. On a physical install, "undo" means a reinstall.

Virtualization attacks all four at once by changing what an operating system runs on.

## 4. What Virtualization Actually Is

**Virtualization is the technique of using software to present computing resources that behave like hardware but are not the physical hardware underneath.**

Read that again with the emphasis on *behave like*. The point is not that the resource is fake — the CPU cycles a virtual machine consumes are real cycles on a real CPU, and the bytes it writes to its disk are real bytes on real storage. The point is that what the software *sees* is not what physically exists. A layer in between is answering its questions.

That gives us the module's central distinction:

| | Physical resource | Virtual resource |
|---|---|---|
| **What it is** | Actual hardware you could unplug | A software-provided interface that behaves like that hardware |
| **Example** | An 8-core CPU in a laptop | A VM configured with 4 vCPUs |
| **Example** | A 512 GB SSD | A 60 GB virtual disk, stored as a file on that SSD |
| **Example** | A network card | A virtual NIC the guest OS detects and configures |
| **Who provides it** | The manufacturer | The virtualization software |
| **How much exists** | A fixed, finite amount | As much as you configure — but always drawn from the finite physical amount |

That last row is the one students most often get wrong, and Core Concepts spends real time on it. Configuring virtual resources is not creating them.

## 5. The Virtual Machine

A **virtual machine (VM)** is a complete, self-contained computing environment created by virtualization software: virtual hardware plus whatever operating system and applications you install onto it.

The crucial part is that the VM's operating system is not written specially for this. It's an ordinary operating system — an ordinary Ubuntu, an ordinary Windows — installed the ordinary way, and it behaves as if it has a machine to itself. It detects a CPU, finds memory, discovers a disk, configures a network interface, and boots. Every one of those is being answered by software rather than by physical hardware, and the OS generally cannot tell the difference and doesn't need to.

So what actually exists on the physical computer when a VM is "running"? Two things, roughly:

- **Files on disk** — most importantly the *virtual disk file*, which holds the guest's entire filesystem, plus a configuration describing the virtual hardware (how many vCPUs, how much RAM, which network mode). A powered-off VM is exactly this and nothing more: files.
- **A running workload** — while powered on, the VM's execution is being carried out on real CPU and real memory, managed by the virtualization layer.

This is why a VM can be copied to a USB drive, emailed to a colleague, or downloaded from the internet. It is why "give everyone in the class the same lab machine" is a file transfer rather than eight hardware installs. And it is why deleting the wrong file can destroy a machine.

## 6. The Hypervisor

Something has to create those virtual resources, decide which VM's instructions run on the physical CPU right now, keep one VM's memory out of another's, and translate a guest's disk write into an actual write to the virtual disk file. That something is the **hypervisor** (also called a *virtual machine monitor*).

**What it does:** the hypervisor is the software layer that creates and manages virtual machines, presents virtual hardware to each of them, and allocates the physical machine's real resources among them.

Compare that to the definition you learned in Operating Systems: *the OS is the control layer that manages a computer's shared resources and decides, on behalf of every application, what they're allowed to do with them.* The shapes are deliberately similar. An OS shares one machine's resources among many processes; a hypervisor shares one machine's resources among many whole machines. Core Concepts covers the two families of hypervisor and the real tradeoff between them.

## 7. Host and Guest

These two words appear in every virtualization document, tool, and error message you will ever read. Getting them straight now costs you thirty seconds and saves you a lot of confusion later.

**Host** — the physical machine and its environment: the real hardware, and (in the common desktop case) the operating system installed directly on it. The host *provides* resources.

**Guest** — the operating system running *inside* a virtual machine. The guest *consumes* resources it was given.

```
HOST                                   the physical laptop, and the OS installed on it
  └── virtualization software
        └── VIRTUAL MACHINE            virtual CPU, RAM, disk, NIC
              └── GUEST OS             an ordinary OS, installed normally
                    └── APPLICATIONS
```

**Why the terminology matters — it is not just vocabulary:**

- **It tells you where you are.** Running `whoami` inside the guest tells you who you are *in the guest*. It says nothing about the account you're logged into on the host. Two different machines, two different identities, two different sets of permissions.
- **It tells you what a command can reach.** Deleting a file in the guest deletes a file inside the virtual disk. The host's own files are not in that filesystem at all, unless someone deliberately connected them (a shared folder — Hands-on Practice covers why that matters for security).
- **It tells you which system a problem belongs to.** "The VM has no network" and "the laptop has no network" are different failures with different fixes, and the second one causes the first.
- **It tells you what an attacker has.** If something malicious is running in the guest, it has compromised the guest. Whether that means anything for the host is an entirely separate question — one this module returns to seriously in Hands-on Practice.

A machine can be both, by the way. A physical server can be a host to ten VMs; one of those VMs can itself be running virtualization software and hosting VMs of its own. "Host" and "guest" describe a relationship between two layers, not permanent labels.

## 8. Reading the Stack

You will see this diagram everywhere. Read it as a chain of *who asks whom for what*, and it stops being a picture to memorize:

```
APPLICATIONS          a browser, a scanner, a Python script — running normally
      ↓ system calls
GUEST OPERATING SYSTEM    manages processes, memory, files for the VM
      ↓ operations on virtual hardware
VIRTUAL MACHINE           virtual CPU, virtual RAM, virtual disk, virtual NIC
      ↓ handled by
HYPERVISOR                creates the virtual hardware, allocates and schedules the real
      ↓ real instructions, real reads and writes
PHYSICAL HARDWARE         one actual CPU, actual RAM, actual disk, actual network card
```

Trace one concrete action through it. A Python script in the guest writes a line to a file:

1. The script calls the guest OS to write the file — a **system call**, exactly as in Operating Systems. The script has no idea it's in a VM.
2. The guest OS's filesystem layer decides where on *its disk* that data belongs and issues a write to what it believes is a disk.
3. That disk is virtual. The hypervisor receives the write.
4. The hypervisor translates it into a write inside the virtual disk *file*, which lives on the host's real storage.
5. The physical SSD stores real bytes.

Nothing in that chain is fake. Every layer does real work, and each layer is honest with the layer above it about what it is offering. The guest OS is not being tricked in some fragile way; it is being given a genuine, well-defined interface that happens to be implemented in software.

## 9. Common Mistakes

**Thinking a VM is "just an app in a window."** The window is your view of it. What's inside is a full operating system with its own processes, its own memory, its own filesystem, and its own user accounts — everything Operating Systems taught you, running separately from the host's copy of all the same things.

**Thinking virtual means fake or simulated.** A guest OS's work is executed on real hardware. Virtualization is about *presentation and allocation*, not pretending.

**Mixing up host and guest.** The most common beginner error by a wide margin, and the cause of a large fraction of confused "it doesn't work" moments: installing something on the wrong machine, editing a file on the wrong machine, or reading a network problem on the wrong machine.

**Assuming a VM is automatically safe.** Nothing in this lesson said "isolated and therefore secure." Isolation is a real property with real limits, and it gets a full, honest treatment in Hands-on Practice. Do not assume the conclusion before you've seen the argument.

**Assuming the hypervisor replaces the operating system.** The guest still has a full OS doing all of its usual work. The hypervisor sits *below* that OS, not instead of it.

## 10. Practice

No commands for this one — this lesson is about building a correct model, and the exercises are reasoning exercises. Work through them before moving on.

1. **Name the layers.** A student runs Windows on their laptop, installs virtualization software, and creates a VM with Ubuntu inside it, then opens Firefox in Ubuntu. Which is the host? Which is the guest? Where does the hypervisor sit? What layer is Firefox at?
2. **Follow a resource.** That Ubuntu VM was configured with a 40 GB disk. Where does the guest's data physically end up? What single object on the host holds it?
3. **Predict a result.** The student deletes a file inside the Ubuntu VM. Has anything on the Windows side been deleted? Explain your answer in terms of the stack in Section 8.
4. **Spot the confusion.** Someone says "my VM has no internet, so my laptop's Wi-Fi must be broken." What's wrong with that reasoning, and what would you check to find out which layer actually has the problem?
5. **Explain the vocabulary.** Without looking back at Section 7: what does *host* mean, what does *guest* mean, and give one concrete consequence of confusing the two.

## 11. Knowledge Check

1. In your own words, what is virtualization? (Answer in terms of what software is presenting, not in terms of a product name.)
2. What is the difference between a physical resource and a virtual one? Give an example of each from your own computer.
3. When a VM is powered off, what actually exists of it on the physical machine?
4. What does a hypervisor do, and what does it sit between?
5. What is the difference between a host and a guest, and why does confusing them cause real problems?
6. Why does a guest operating system generally not need to know that it's running in a VM?
7. Why is it wrong to say a virtual machine is "simulated" or "fake"?

## 12. Key Takeaways

- Virtualization uses software to present resources that behave like hardware but are not the physical hardware underneath — the work is real; the *presentation* is what's virtual.
- A virtual machine is a complete computing environment: virtual hardware plus an ordinary operating system installed onto it, which behaves as if it had a machine to itself.
- Powered off, a VM is files — chiefly a virtual disk file and a configuration. That is why VMs can be copied, shared, and downloaded.
- The hypervisor creates virtual hardware and allocates the physical machine's real resources among VMs — the same job an OS does for processes, one level down.
- The host provides resources; the guest consumes them. Confusing the two is the single most common beginner error in this subject.
- The physical hardware → hypervisor → VM → guest OS → applications stack describes a real chain of requests, each layer asking the one below it for something.

## 13. What's Next

**Core Concepts** goes underneath this model. You'll meet the two families of hypervisor and the genuine tradeoff between them; you'll see how virtual CPUs relate to physical cores (it is not one-to-one, and assuming it is causes real mistakes); how memory and disks are actually provided; how a VM's network traffic reaches the outside world in three quite different ways; and what happens when you promise several VMs more resources than the machine physically has.
