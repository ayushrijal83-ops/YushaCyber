# Metasploit Core Concepts

## 1. What You Will Learn

By the end of this lesson you should be able to:

- walk the full workflow from **discovery** to **remediation** without skipping a step
- turn a real scan result into a **research question** rather than a module guess
- explain what a tester is looking for when they **search** for and **read** a module
- explain what a **check** does, what it proves, and what it does not
- configure a module's **target options** and say why each one matters
- explain the **callback** concept, and why some payloads need one
- restate the **exploit vs payload** distinction in operational terms
- explain why an exploit module can have **several target profiles**
- perform **failure analysis** — treat a failed run as evidence instead of a reason to guess
- state what **validates** a result, and what merely looks like validation
- record a finding as **evidence**, and connect it to **remediation**

## 2. The Workflow

Everything in this lesson hangs off one chain. Learn it as a whole, because the mistakes people make with Metasploit are almost always *skipped links*, not wrong commands.

```
DISCOVERY
    ↓  what hosts and ports exist                      (Nmap)
SERVICE IDENTIFICATION
    ↓  what software is behind the port                (Nmap -sV, banners)
VULNERABILITY RESEARCH
    ↓  is there a known flaw in THIS software+version
MODULE SELECTION
    ↓  does a module exist, and does it apply
TARGET / OPTION CONFIGURATION
    ↓  RHOSTS, RPORT, TARGET, module-specific options
PAYLOAD SELECTION
    ↓  what should run afterwards, and does it fit
CONTROLLED EXECUTION
    ↓  check first where supported, then run — once, deliberately
SESSION / RESULT
    ↓  what actually came back
VALIDATION
    ↓  what evidence proves the result is real
EVIDENCE
    ↓  what gets written down
REMEDIATION
       what the owner should change, and how to verify it
```

Two observations before we walk it:

- **The first three links contain no Metasploit at all.** They are Nmap, service identification and research. A tester who opens the console first has already lost the thread.
- **Execution is one link out of eleven.** The rest is deciding what to do and working out what happened.

## 3. Discovery → Service Identification

This is the handoff from the **Nmap** module. Here is a real scan of YushaCyber's authorized training network, captured from the platform's own simulator:

```
nmap -sV 10.10.10.40

Starting Nmap

Nmap scan report for 10.10.10.40

PORT     STATE    SERVICE    VERSION
22/tcp open ssh OpenSSH 8.x
3306/tcp open mysql MySQL 8.x
8080/tcp open http Apache 2.x

Nmap done.
```

Three services. Now the reasoning, which is the part worth learning:

**What this output supports:**

- Three TCP ports on this host accept connections.
- The service on 3306 identifies itself as MySQL; on 8080, as Apache; on 22, as OpenSSH.

**What it does not support:**

- That any of these is vulnerable. Nothing here is a vulnerability finding.
- That the versions are precise. `MySQL 8.x` is a *family*, not a build. This matters enormously — see below.
- That the banner is honest. Services can be configured to report something else, and a proxy can answer on behalf of something entirely different.

**The version-precision problem, stated plainly.** Look at what the scan actually gave you: `OpenSSH 8.x`, `MySQL 8.x`, `Apache 2.x`. Now consider what module selection requires: whether *this exact build* falls inside the range a vulnerability affects. `8.x` spans years of releases and dozens of patch levels.

So the correct conclusion from this scan is **not** "let's find a MySQL module." It is:

> *I have three candidate services and imprecise versions. Before any module is worth considering, I need to narrow the version — or accept that I am reasoning about a family and say so in the report.*

That sentence is the difference between a tester and someone typing commands. Nothing about it requires Metasploit to be open.

## 4. Vulnerability Research

Research sits between "I know what is running" and "I know what to try," and it answers three questions in order:

1. **Is there a publicly known vulnerability in this software?**
2. **Does it affect the version, build, platform and configuration in front of me?**
3. **Does exploiting it tell my client something they do not already know?**

The third question is the professional one, and it gets skipped constantly. If a client already knows their FTP server is ancient and has a project underway to replace it, exploiting it proves nothing and risks an outage for no gain. Testing is supposed to *reduce* uncertainty.

The vocabulary you will use for question 2:

| Term | What it is |
|---|---|
| **CVE** | A public identifier for one specific vulnerability, e.g. `CVE-2011-2523`. It names the flaw, not the exploit |
| **Advisory** | The vendor's or researcher's description: affected versions, conditions, fix |
| **Affected range** | The versions the flaw applies to. The single most important field for module applicability |
| **Preconditions** | What must be true besides the version — a feature enabled, a specific configuration, authentication, a reachable path |

**A real historical example, used correctly.** In 2011 the distributed source archive for **vsftpd 2.3.4** was replaced with a backdoored copy; supplying a username containing a particular smiley sequence opened a shell on a high port (`CVE-2011-2523`). It is one of the most-demonstrated Metasploit modules in existence, precisely because it is trivially reliable.

Now look at the file server on the same authorized training network:

```
nmap -sV 10.10.10.30

Starting Nmap

Nmap scan report for 10.10.10.30

PORT     STATE    SERVICE    VERSION
21/tcp open ftp vsftpd 3.x
22/tcp open ssh OpenSSH 9.x
445/tcp open microsoft-ds Samba 4.x

Nmap done.
```

`vsftpd 3.x`. The backdoored release was 2.3.4. **The module does not apply**, and the reasoning takes one line: *the affected version is 2.3.4; this host reports the 3.x family; the finding is not applicable.*

That is a complete, defensible, professional result — reached without running anything. Lesson 3 makes you write it up.

## 5. Module Search — How a Tester Reasons

Searching is a *narrowing* step, not an answering step. Testers search on:

| Search on | When it helps | What it risks |
|---|---|---|
| **Product name** | You know the software but not the flaw | Broad results; many will not apply |
| **CVE** | Research already gave you a specific vulnerability | Nothing — this is the most precise search you can do |
| **Version** | You have a precise build | Versions are inconsistently recorded in module metadata; absence is not proof |
| **Service / protocol** | You only know "something SMB-ish is here" | Very broad; mostly useful for finding auxiliary modules |
| **Platform** | Narrowing by operating system | Only meaningful combined with something else |

Two disciplines that separate a professional from a scanner-with-hands:

- **Search results are candidates.** A list of twelve modules is a list of twelve things to *read*, not twelve things to run.
- **Never work down the list.** Trying modules in sequence until something happens is indiscriminate exploitation: it is noisy, it risks crashing services, it produces findings you cannot explain, and on a real engagement it is the behaviour that gets a test stopped. If your research did not point at a specific module, the answer is more research, not more attempts.

## 6. Reading the Module — `info`

Before a module is configured, it is read. Each field answers a specific question:

| Field | The question it answers |
|---|---|
| **Description** | What does this actually do, in the author's words? |
| **References** | Which CVE/advisory is this? — your link back to the research step |
| **Disclosure date** | How old is this flaw? A 2011 flaw on a maintained host is unlikely |
| **Targets** | Which builds/platforms does the author claim to support? (see §10) |
| **Options** | What does *this* module need — not what the last one needed |
| **Payload compatibility** | Which payloads can this exploit actually deliver? |
| **Rank / reliability** | The author's own assessment of how likely it is to work — and how likely it is to crash the target |
| **Check support** | Can I gather evidence without running the exploit? |

The **rank** field deserves a sentence of its own. A low-ranked module is often low-ranked because it is *unreliable in a way that damages the target* — it may leave the service dead. On a production engagement that is not a technical detail; it is the difference between a finding and an incident.

> **A module should be understood before it is executed.** If you cannot say, before pressing anything, what the module will attempt, which flaw it targets, and what failure would look like, you are not ready to run it.

## 7. The Check

Some modules implement a **check**: a test of whether the target *appears* vulnerable, without attempting exploitation.

Why it matters: it is the lowest-risk way to gather evidence. A check typically inspects a version, requests something benign, or probes for a behavioural signature.

What a check result actually means:

| Result | Reasonable reading |
|---|---|
| Appears vulnerable | Good supporting evidence. Not proof — the check may be inferring from a banner that lies |
| Appears not vulnerable | Useful evidence *against*. Not proof either |
| Cannot determine | Common and honest. The module could not gather what it needed |
| Not supported | Many modules have no check at all. Absence of a check is not absence of a vulnerability |

**False positives and false negatives, concretely:**

- A **false positive** happens when the check reads a version banner that has not been updated, while the underlying package has been patched by a distribution backport. The banner says vulnerable; the code is not.
- A **false negative** happens when the check probes for a behaviour the target hides — a firewall filters the probe, or the service is configured not to answer that request — so a genuinely vulnerable host reports clean.

Which is why: **`check` result ≠ guaranteed exploitation, in either direction.** It moves your confidence; it does not settle the question.

## 8. Target and Option Configuration

Configuration is where you point a general-purpose module at one specific authorized system. Every value is a decision.

| Option | What you are deciding | What goes wrong |
|---|---|---|
| `RHOSTS` | Which host(s) this runs against | The most consequential option in the framework. A typo here means you tested something you were not authorized to test |
| `RPORT` | Which port the service is on | Modules default to the conventional port. Your evidence may say otherwise — the scan above found HTTP on **8080**, not 80 |
| `TARGET` | Which target profile to assume | Wrong profile is a top cause of failure against genuinely vulnerable hosts |
| `PAYLOAD` | What runs after success | Must be compatible with the exploit and the target platform |
| `LHOST` | Where a callback payload should connect back to | Wrong value = the exploit works and you see nothing |
| `LPORT` | Which local port receives it | Must be free, and reachable from the target |

**Use only authorized training values.** Throughout this module the targets are YushaCyber's simulated training hosts (`10.10.10.10`, `10.10.10.30`, `10.10.10.40`, `10.10.10.53`) or documentation placeholders. Never put a public address, a real customer's host, or "some server I found" into `RHOSTS`.

**Verify before executing.** Listing options and reading back what you set is a deliberate step, not a formality — it is the last point at which a mistyped `RHOSTS` is still harmless.

## 9. The Callback Concept

Some payloads connect *back* to the tester rather than waiting to be connected *to*. Conceptually:

```
   Authorized tester                     Authorized target
   ┌──────────────┐                      ┌──────────────┐
   │  listener on │  ◄──── connects ──── │  payload      │
   │  LHOST:LPORT │        back          │  runs here    │
   └──────────────┘                      └──────────────┘
```

Why this design exists: a target sitting behind a firewall often cannot be *reached* on an arbitrary new port, but is frequently allowed to make **outbound** connections. A connection initiated from the target's side therefore has a better chance of completing.

The alternative shape is a payload that listens on the target and waits for the tester to connect in. Both exist; which is appropriate depends on the network path between you and the target.

Two practical consequences, at the level this module teaches:

- **`LHOST` must be an address the target can actually reach.** In a lab this is usually your own interface address on the same network. Setting it to a value the target cannot route to is one of the most common reasons an exploit "fails" when it in fact worked.
- **Address translation and firewalls affect whether a callback completes.** If the tester's machine is behind address translation, the address the *target* needs is not necessarily the address the tester's own interface shows.

This module explains why callbacks succeed or fail so that you can interpret a result correctly. It does **not** teach techniques for getting traffic through controls that are deliberately blocking it — that is evasion, it belongs to the Red Team track, and it is out of scope here.

## 10. Why One Exploit Has Several Targets

A memory-corruption exploit frequently depends on details that vary between builds: where things sit in memory, which compiler options were used, which mitigations are present. So a module often ships several **target profiles** — each a set of assumptions about one build.

This is why the following is wrong:

> "This exploit works against Product X."

and this is right:

> "This exploit has target profiles for these specific builds of Product X, and a profile has to be chosen to match the target."

Consequences worth internalising:

- Running a module with the wrong profile against a genuinely vulnerable host commonly fails — and often *crashes the service*, because the exploit corrupted state without landing correctly.
- "It failed, so the host is patched" is an unsound conclusion if you never confirmed the profile matched.
- Some modules offer an automatic profile. Automatic means *the module guesses*, and a guess can be wrong.

## 11. Exploit vs Payload, Operationally

Lesson 1 defined these. Here is what the distinction buys you when something goes wrong:

| Observation | What it points at |
|---|---|
| The service crashed, nothing came back | **Exploit** problem — probably a target-profile mismatch |
| The module reports the vulnerability triggered, but no session | **Payload** or **network path** problem — the payload failed to run, or the callback never completed |
| The module reports the target is not vulnerable | **Applicability** problem — back to research |
| Connection refused / no route before anything ran | **Configuration** problem — `RHOSTS`/`RPORT`, or the host is not reachable at all |

Read that table again as a diagnostic tool. It is why "try a different payload" is usually the wrong first move: three of the four rows are not payload problems, and changing the payload cannot fix them.

## 12. Failure Analysis

**A failed execution is evidence.** It narrows the possibilities. Treating it as a dead end — and reaching for the next module in the list — throws that information away and replaces it with noise.

When a run fails, work through causes systematically:

| Cause | What you would check |
|---|---|
| **Wrong target host** | Is `RHOSTS` the host your evidence actually pointed at? |
| **Wrong port** | Does `RPORT` match your scan, or the module's default? |
| **Wrong target profile** | Does `TARGET` match the build you identified? |
| **Version mismatch** | Is the target's version genuinely inside the affected range? |
| **Target patched** | Backported fixes leave the banner unchanged — the version may be misleading |
| **Missing precondition** | Does the flaw need a feature enabled, a path, credentials, or a particular state? |
| **Network path** | Can you reach the service? Can the target reach `LHOST:LPORT`? |
| **Incompatible payload** | Is the payload valid for this exploit, platform and architecture? |
| **Application state** | Some flaws need the application in a particular condition |
| **Wrong module entirely** | Does the module target the product you actually found? |

Notice how many of these are answered by **looking**, not by trying again.

**The discipline, stated as a rule:** change **one** thing, and only because your evidence says so. If you cannot state which assumption you are testing, stop and go back to research. Randomised retries against a real system are noisy, potentially destructive, and produce results nobody can explain — including you.

## 13. Validation

The question after execution is not "did it say success?" It is **"what evidence supports the claim I am about to make?"**

| Claim | Evidence that supports it |
|---|---|
| The service is reachable | Your own scan and connection attempts |
| The vulnerability is present | A check result, a version inside the affected range, plus a reproducible behavioural signature |
| The exploit executed | The module's reported behaviour *plus* an observable change consistent with it |
| A session exists | The framework listing it, and it responding to interaction |
| The access has privilege *P* | Something you actually observed at that privilege — not an assumption |

**Why a console message alone is not proof.** A module reports what its own code concluded. It can conclude wrongly: it may report success on a partial condition, or report failure while the payload did in fact run. Corroboration comes from a *second* observation — an expected state change, a session that responds, or the target's own logs.

This is the same discipline **Burp Suite** taught you about response codes and **Active Directory Basics** taught you about effective access: the tool tells you what it saw, and you decide what it means.

## 14. Evidence

A finding that cannot be reproduced is an anecdote. Record these:

| Field | Content |
|---|---|
| **Target** | The authorized host and service, precisely |
| **Service** | Product and version as identified, with how you identified it |
| **Vulnerability** | The specific flaw, with its CVE or advisory |
| **Module** | The exact module used |
| **Options** | Every option you set — this is what makes it reproducible |
| **Expected result** | What you predicted before running it |
| **Observed result** | What actually happened, quoted, including failures |
| **Evidence** | What corroborates the observation |
| **Impact** | What this means for the system's owner, in their terms |
| **Remediation** | What to change, and how to confirm the change worked |

**Expected vs observed is the field people leave out, and it is the most valuable one.** Writing down your prediction *before* running the module is what turns a test into an experiment. When the two differ, you have learned something specific — which is exactly the input failure analysis needs.

## 15. Remediation

A test that ends at "we got in" is unfinished work. The client is not paying to be told they have a problem; they are paying to know what to do about it.

| Remediation | When it is the right answer |
|---|---|
| **Patch the software** | A known flaw with a vendor fix — the default answer |
| **Remove the service** | It should not have been running at all. The strongest fix, since it removes the whole class of future flaws too |
| **Restrict network exposure** | The service is needed, but not by everyone. Ties directly to the segmentation reasoning from Computer Networking |
| **Apply least privilege** | Reduces what a successful exploit reaches. The same principle taught in Cybersecurity Fundamentals and Active Directory Basics |
| **Harden the configuration** | Disable the vulnerable feature, require authentication, change insecure defaults |
| **Monitor and detect** | Exploitation attempts should be visible. This is the Blue Team half of the same finding |
| **Validate the remediation** | Re-test afterwards. A fix nobody verified is a plan, not a fix |

That last row closes the loop. The same evidence record that documented the finding is what makes re-testing possible — you reproduce the exact conditions and confirm the result changed.

## 16. Correcting Some Common Misconceptions

**WRONG:** "If exploitation fails, try other modules until one works."
**CORRECT:** Analyse the failure. Each cause in §12 is checkable. Randomised attempts are noisy, risk damaging the target, and produce results you cannot explain.

**WRONG:** "The check said vulnerable, so it is vulnerable."
**CORRECT:** A check is evidence, not proof. It can be fooled by a stale banner or a backported patch in either direction.

**WRONG:** "The exploit failed, so the target is patched."
**CORRECT:** That is one possible cause out of ten. Wrong port, wrong target profile, unreachable callback and missing preconditions all look identical from the console.

**WRONG:** "Metasploit is the start of the workflow."
**CORRECT:** It sits in the middle. Discovery, service identification and vulnerability research all come first, and evidence and remediation come after.

**WRONG:** "The version from `-sV` is the version."
**CORRECT:** It is what the service reported, at family-level precision in this platform's own output. Backported patches and deliberately altered banners both break the inference.

**WRONG:** "A successful test is the deliverable."
**CORRECT:** The deliverable is the finding: evidence, impact, remediation, and a way to verify the fix.

## 17. Exercises

**Exercise 1 — Read the evidence.**
Using the real scan of `10.10.10.40` in §3: write down (a) three things the output supports, (b) three things it does not support, and (c) the single most useful next question. Do not name a module.

**Exercise 2 — Applicability.**
The file server at `10.10.10.30` reports `vsftpd 3.x`. A well-known module targets the backdoored 2.3.4 release. State your conclusion and the reasoning in no more than three sentences, and say what evidence would change your mind.

**Exercise 3 — Which link broke?**
For each observation, name the most likely link in the §2 chain and the first thing you would check:
(a) "Connection refused" before anything ran
(b) the module reports the vulnerability triggered, but no session appears
(c) the target service stops responding entirely
(d) the module reports the target is not vulnerable, but your research says the version is affected

**Exercise 4 — Expected vs observed.**
Write the *expected result* line you would record before running a check against a service whose version you could not narrow beyond a family. Then write the two possible observed results and what each would let you conclude.

**Exercise 5 — Finish the job.**
Assume a finding is confirmed on the training network's MySQL service. Write three remediation recommendations in priority order, and state exactly how each one would be verified afterwards.

## 18. Knowledge Check

1. **What comes before Metasploit in the workflow?**
   Discovery, service identification and vulnerability research. Three of the first four links involve no framework at all. Opening the console first means selecting a module without knowing what you are selecting it for.

2. **Why doesn't finding a module prove the target is vulnerable?**
   A module proves a flaw existed in some version of some product. Whether it applies to the build in front of you depends on version, platform, configuration and preconditions — all of which have to be established separately.

3. **What is the purpose of a check?**
   To gather evidence about whether a target appears vulnerable *without* attempting exploitation. It is the lowest-risk evidence available, and its result moves your confidence rather than settling the question.

4. **Give one false positive and one false negative a check could produce.**
   False positive: a version banner unchanged by a distribution's backported patch, so the check reads "vulnerable" against patched code. False negative: a filtered probe or a service configured not to answer, so a genuinely vulnerable host reads clean.

5. **What does `RHOSTS` represent, and why is it the most consequential option?**
   The remote target host or hosts the module acts against. A wrong value means you tested a system you were not authorized to test — a scope and legal failure, not just a technical one.

6. **What does `RPORT` represent, and why not just accept the default?**
   The remote port of the target service. Modules default to the conventional port, but your evidence may say otherwise — the real scan in §3 found HTTP on 8080, not 80.

7. **Why do some payloads need `LHOST` and `LPORT`?**
   Because they connect *back* to the tester. `LHOST`/`LPORT` tell the payload where to reach the listener. The value must be an address the target can actually route to, which is not necessarily the address the tester's own interface shows.

8. **Why might an exploit work against one version of a product but not another?**
   Because exploits depend on build-specific details — memory layout, compiler options, mitigations, whether the vulnerable code path exists at all. This is why modules ship several target profiles rather than one.

9. **Why can an exploit fail even when the vulnerability genuinely exists?**
   Wrong target profile, wrong port, unreachable callback address, incompatible payload, missing precondition, wrong application state, or a mitigation the module does not handle. "Patched" is one possible cause among many.

10. **Why is a failed run useful?**
    It eliminates possibilities. Combined with your recorded expectation, it tells you which assumption was wrong — which is a specific, checkable next step rather than a reason to try something else at random.

11. **What evidence proves successful exploitation?**
    A corroborated observation: the module's report *plus* an independent signal — an expected state change, a session that actually responds to interaction, or the target's own logs. A console message alone is a claim by one program about itself.

12. **Why is remediation part of a penetration test rather than an afterthought?**
    Because the deliverable is a decision the owner can act on. A finding without remediation and a way to verify it leaves the client exactly where they started, only more worried.

13. **Why should a tester avoid working down a search-results list?**
    Because indiscriminate attempts are noisy, can crash production services, produce results nobody can explain, and abandon the research step that would have identified the right module in the first place.

---

**Next:** *Hands-on Practice* puts this to work — real evidence from YushaCyber's authorized training network, seven exercises in module reasoning, and a written finding at the end.
