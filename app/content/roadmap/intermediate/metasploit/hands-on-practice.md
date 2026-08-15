# Metasploit — Hands-on Practice

## 1. Authorization First

Everything below happens against **YushaCyber's authorized simulated training network** — the `10.10.10.0/24` hosts modelled in this platform's own terminal simulator. Nothing here touches a real machine.

**Do not repeat any of this against a system you do not own or do not have written permission to test.** That includes public addresses, "test" servers belonging to someone else, and your employer's systems without an authorization letter. Exploit modules deliberately trigger faults in running software; running one uninvited can take a service down whether or not it succeeds.

**What this lesson is:** structured practice in the reasoning that surrounds Metasploit — reading evidence, judging module applicability, configuring deliberately, analysing failure, validating a result, and writing a finding.

**What this lesson is not:** a walkthrough of breaking into a box, and not an introduction to credential access, persistence, lateral movement or evasion. Those belong to **Windows Privilege Escalation**, **Linux Privilege Escalation** and the **Red Team** track.

## 2. What Is Real Here, and What Is Not — Read This Before Anything Else

Being straight with you about the environment matters more than looking impressive.

**YushaCyber has no Metasploit simulator.** There is no `msfconsole` on this platform. The terminal's command set covers filesystem, networking, packet capture, HTTP and proxy commands — there is no `use`, no `set`, no `check`, no `exploit`, no `sessions`. No lab category and no terminal mission simulates the framework.

Therefore:

| In this lesson | Status |
|---|---|
| Every `nmap` block | **REAL OUTPUT** — captured by running this platform's own simulator against its own training network |
| The hosts, ports and versions you reason about | **REAL** — they come from that same simulated network's definition |
| The Network Reconnaissance mission in §11 | **REAL** — an existing terminal mission you can complete for XP |
| Every `msf6 >` console block | **ILLUSTRATIVE EXAMPLE — not captured from a live simulator.** Marked individually, every time |

You will not be shown an invented session and told it is output. Where something cannot be run here, the lesson says so and gives you the reasoning exercise instead — because the reasoning is the transferable skill. Anyone can type `exploit`; deciding whether to is the job.

## 3. The Environment

The authorized training network, from the platform's own simulator:

```
nmap -sn 10.10.10.0/24

Starting Nmap

Nmap scan report for 10.10.10.1
Host is up.

Nmap scan report for 10.10.10.10
Host is up.

Nmap scan report for 10.10.10.20
Host is up.

Nmap scan report for 10.10.10.30
Host is up.

Nmap scan report for 10.10.10.40
Host is up.

Nmap scan report for 10.10.10.53
Host is up.

Nmap done: 6 IP addresses (6 hosts up) scanned.
```

| Host | Role | Your interest |
|---|---|---|
| `10.10.10.20` | Your machine | Where you would run tooling from — and what `LHOST` would be |
| `10.10.10.1` | Gateway | Network infrastructure; not a target |
| `10.10.10.10` | Web server | Candidate |
| `10.10.10.30` | File server | Candidate |
| `10.10.10.40` | Training server | Candidate |
| `10.10.10.53` | DNS server | Candidate |

## 4. The Reasoning Shape

Every exercise below is answered in the same six parts. Use this shape every time — it is what makes your conclusions checkable by someone else.

```
OBSERVATION      what you saw
EVIDENCE         the exact output that supports it
INTERPRETATION   what it means — and what it does not
DECISION         what you will do next, and why
CONFIDENCE       high / medium / low, with the reason
WHAT WOULD CHANGE IT   the evidence that would overturn your conclusion
```

That last line is the one that separates analysis from assertion. If nothing could change your mind, you are not reasoning.

## 5. Practice 1 — Module Research

**Objective:** turn a service into a research question, not a module guess.

Real output from the training server:

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

**Do this:**

1. List the three services with product and version exactly as reported.
2. For each, write the research question you would need answered before any module is worth considering.
3. Identify the **precision problem** in this output and state its consequence in one sentence.
4. Decide which service you would research first, and justify it on evidence — not on which sounds most exciting.
5. Write the six-part record from §4.

**Worked partial answer — the precision problem.**

> OBSERVATION: All three versions are reported at family level — `8.x`, `8.x`, `2.x`.
> EVIDENCE: The VERSION column above.
> INTERPRETATION: A family spans years of releases and many patch levels. Module applicability depends on whether *this build* falls inside a vulnerability's affected range, and a family cannot answer that.
> DECISION: Treat every candidate as unconfirmed. Either narrow the version through further enumeration, or state in the finding that the assessment is at family level.
> CONFIDENCE: High — this is a property of the evidence, not a judgment about the host.
> WHAT WOULD CHANGE IT: A precise build string from deeper service enumeration or an authenticated inventory.

**What you cannot conclude from this scan:** that any service is vulnerable; that the banners are truthful; that MySQL on 3306 is reachable from anywhere other than where you scanned from; that the Apache on 8080 is the only web service on the host.

**Common mistake:** jumping from "MySQL is open" to searching for MySQL modules. Open is not vulnerable. Ports are not findings.

## 6. Practice 2 — Options

**Objective:** understand why each option exists before setting any of them.

Working from the evidence above, write down what each option would be for a hypothetical module against the web service on `10.10.10.40`, and — more importantly — *why it matters*:

| Option | Your value | Why does this option matter? |
|---|---|---|
| `RHOSTS` | | |
| `RPORT` | | |
| `TARGET` | | |
| `PAYLOAD` | | |
| `LHOST` | | |
| `LPORT` | | |

**Checks on your answers:**

- Did you set `RPORT` to **8080**? The scan found HTTP there, not on 80. Accepting a module's default port because it is the default is one of the most common configuration errors.
- Is `LHOST` an address the target can actually reach? On this network that is `10.10.10.20`, your own machine. An `LHOST` the target cannot route to produces an exploit that works and shows you nothing.
- Could you fill in `TARGET` honestly? You should not have been able to — you never established the build. Note that as an open question rather than guessing.
- Did you notice that `PAYLOAD`, `LHOST` and `LPORT` would be **meaningless** for a scanning auxiliary module? Required options depend on the module.

**Never** put a public address, a real organisation's host, or an address you have not been authorized to test into `RHOSTS`. Use the training hosts or documentation placeholders, as this lesson does throughout.

## 7. Practice 3 — The Check

**Objective:** reason about a check's value without one available to run.

This platform cannot run a check — there is no framework here (§2). The reasoning is the exercise, and it transfers exactly.

**Illustrative example — not captured from a live simulator. YushaCyber has no Metasploit simulator; this shows the *shape* of the interaction only.**

```
msf6 exploit(...) > check
[*] 10.10.10.40:8080 - The target appears to be vulnerable.
```

**Do this — write all three lines, for both possible results:**

```
Expected:    ...what you predicted before running the check, and on what basis
Observed:    ...exactly what came back
Conclusion:  ...what this does and does not establish
```

**The trap to avoid.** "Appears vulnerable" is a claim by one program about a target that may be misrepresenting itself. Your Conclusion line should read closer to:

> Conclusion: the check found a signature consistent with the affected version. This raises confidence but does not establish exploitability — a backported patch would leave the same signature. Corroboration required.

Now write the mirror case. If the check said "does not appear to be vulnerable," what could still be true? (At minimum: a filtered probe, a service configured not to answer, or a check that only inspects a banner the administrator has changed.)

**Remember:** many modules have no check at all. Its absence tells you nothing about the target.

## 8. Practice 4 — Controlled Execution

**Objective:** understand what controlled execution requires — and why it is not available here.

**Nothing in this lesson executes an exploit.** There is no Metasploit engine on this platform, and inventing one in text would teach you to trust output that was never produced. So this practice is a readiness exercise instead.

Before any authorized exploitation attempt, you should be able to answer **all** of these. If any answer is missing, you are not ready to run anything:

| # | Question |
|---|---|
| 1 | Is this host explicitly inside the authorized scope, in writing? |
| 2 | Which specific vulnerability am I testing, by CVE or advisory? |
| 3 | What evidence connects that vulnerability to *this* build? |
| 4 | Have I read the module — its description, references, targets and rank? |
| 5 | Does the module's rank indicate a risk of crashing the service? |
| 6 | Is this an acceptable time to risk a disruption, and who has been told? |
| 7 | Which target profile am I selecting, and on what evidence? |
| 8 | Is my payload compatible with the exploit, platform and architecture? |
| 9 | Can the target reach my `LHOST:LPORT`? |
| 10 | What exactly do I *expect* to happen? |
| 11 | What will I accept as evidence of success? |
| 12 | What will I do if the service does not come back? |

**Do this:** answer all twelve for the MySQL service on `10.10.10.40`, using only the evidence this lesson has actually produced. You will find several you cannot answer. **Write down which ones and why** — that list *is* the result of this exercise. A tester who knows precisely which of the twelve they cannot answer is doing the job correctly; one who runs the module anyway is not.

## 9. Practice 5 — Result Validation

**Objective:** separate what a console said from what you can defend.

For each claim, write down what evidence would be *sufficient*, and what evidence would be *misleading*:

| Claim | Sufficient evidence? | Misleading evidence? |
|---|---|---|
| "The service is reachable" | | |
| "The vulnerability is present" | | |
| "The exploit executed" | | |
| "A session was established" | | |
| "The access has administrative privilege" | | |

Then answer these five directly:

1. Did the exploit actually succeed, or did the module merely report success?
2. What independent observation corroborates it?
3. Did a session appear — and does it *respond* to interaction, or is it just listed?
4. Did the expected state change occur on the target?
5. Could the console message be misleading? Name one specific way.

**The point.** A module reports what its own code concluded, and its code can be wrong in both directions: reporting success on a partial condition, or reporting failure when the payload did in fact run. Corroboration always comes from a second, independent observation. This is the same discipline **Burp Suite** taught you about status codes and **Active Directory Basics** taught you about effective access.

## 10. Practice 6 — The Failed Exploit

**Objective:** treat failure as evidence. This is the most valuable exercise in the lesson.

Here is the file server, real output from the platform's simulator:

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

**The scenario.** A well-known Metasploit module targets the backdoored **vsftpd 2.3.4** release — in 2011 the distributed source archive was replaced with a modified copy containing a backdoor (`CVE-2011-2523`). It is one of the most reliable demonstration modules in existence. A student sees `vsftpd` on port 21, finds the module, runs it, and it fails.

**Answer these:**

1. Why did it fail? Point at the exact evidence in the output above.
2. At which link in the workflow chain did the student go wrong — and note that it was **before** they opened the console.
3. Why should the tester now **stop**, rather than trying the next FTP module in the search results?
4. What would you write in the report about port 21 on this host?
5. What evidence would change your conclusion?

**Expected reasoning:**

> The affected release is 2.3.4. This host reports the `3.x` family. The module is not applicable, and this was determinable from the scan output before anything was run — the failure occurred at **vulnerability research**, not at execution. Trying further FTP modules would be indiscriminate: it tests no stated hypothesis, generates noise, risks disrupting a service, and produces results that cannot be explained afterwards. The correct next step is to validate the assumption — confirm the version through a second source — and, if it holds, record port 21 as "FTP service identified, no applicable known vulnerability at the identified version" rather than as either a finding or nothing at all. What would change it: a precise build string placing the service inside an affected range, or evidence that the banner is inaccurate.

**A second failure to reason about.** Here is a real result from the same simulator against an address with nothing on it:

```
nmap -sV 10.10.10.99

Starting Nmap
Note: Host seems down. If it is really up, but blocking pings, try -Pn
Nmap done: 0 hosts up.
```

If your module had been configured with `RHOSTS 10.10.10.99`, every attempt would fail — and none of those failures would tell you anything about any vulnerability. **Which of the ten failure causes from Core Concepts §12 is this, and how would you distinguish it from "the target is patched" using only the console?** (Answer: it is a wrong-target/network-path failure, and you distinguish it by the fact that nothing ever connected — the failure happened before any protocol interaction, which looks completely different from a module that talked to a service and was rebuffed.)

## 11. Practice 7 — The Professional Finding

**Objective:** produce the actual deliverable.

Use this template. Every field must be supported by evidence this lesson actually produced.

```
Finding:
Affected service:
Vulnerability:
Evidence:
Metasploit module:
Observed behaviour:
Impact:
Root cause:
Recommended remediation:
Validation after remediation:
```

### Worked finding — built only from real evidence

```
Finding:              FTP service identified on the file server; no applicable
                      known vulnerability at the identified version.

Affected service:     10.10.10.30 (authorized training file server), TCP/21, vsftpd 3.x

Vulnerability:        None applicable. The candidate considered was the backdoored
                      vsftpd 2.3.4 distribution (CVE-2011-2523).

Evidence:             nmap -sV 10.10.10.30 reports "21/tcp open ftp vsftpd 3.x".
                      The affected release is 2.3.4; the identified family is 3.x.

Metasploit module:    None executed. The candidate module was assessed as
                      not applicable during research and was not run.

Observed behaviour:   No exploitation attempted. Version evidence alone was
                      sufficient to close the candidate.

Impact:               No impact from this candidate. FTP remains a cleartext
                      protocol, so the service is worth reviewing on
                      exposure grounds independent of any vulnerability.

Root cause:           n/a for the candidate. For the exposure observation: a
                      legacy file-transfer service remains enabled.

Recommended
remediation:          Confirm whether FTP is still required. If not, disable it.
                      If it is, restrict its reachable network range and move to
                      an encrypted transfer protocol.

Validation after
remediation:          Re-scan 10.10.10.30. Port 21 should be closed or reachable
                      only from the authorized source range.
```

Note what that finding demonstrates: **a professional result with nothing exploited.** Most of a real report looks like this.

### Your turn — two more

**Finding 2 (guided).** Write up port 8080 on `10.10.10.40`. Your Evidence line is the real `-sV` output from §5. Your Vulnerability line must honestly reflect that the version could not be narrowed past `Apache 2.x`, and your Observed-behaviour line must say that no module was executed. The hard part is writing an Impact line that is useful without overstating what you know.

**Finding 3 (unguided — the hardest).** Write up TCP/3306 on `10.10.10.40`. Nothing here is broken as far as your evidence shows, and there is no exploitation to describe. The professional question is a different one: *should a database service be reachable at all from the position you scanned from?* That is a finding about **exposure**, and it needs no vulnerability to be legitimate. It is the hardest of the three precisely because nothing looks wrong.

## 12. Common Mistakes

| Mistake | Why it is wrong |
|---|---|
| Opening the console first | Discovery, service identification and research all come before module selection |
| Treating an open port as a finding | Open means a service answered. That is inventory, not vulnerability |
| Searching for modules before researching the vulnerability | Produces a candidate list you have no basis for choosing from |
| Working down the search results | Indiscriminate exploitation: noisy, risky, and produces unexplainable results |
| Accepting the default `RPORT` | Your evidence found HTTP on 8080. Defaults describe convention, not this host |
| Guessing at `TARGET` | Wrong profile fails against genuinely vulnerable hosts and frequently crashes the service |
| Reading "success" as success | A module reports its own conclusion. Corroborate with an independent observation |
| Calling a session "full compromise" | A session runs at whatever privilege the payload landed with. Report what you actually have |
| Skipping the expected-result line | Without a prediction, a failure teaches you nothing specific |
| Stopping at "we got in" | The deliverable is impact, remediation, and a way to verify the fix |

## 13. Real Practice on This Platform

**What you can actually run here.** The **Network Reconnaissance** terminal mission runs on exactly the network this lesson quotes throughout — the same `10.10.10.0/24` hosts, the same services, the same version strings. Its eleven objectives walk the first three links of the workflow chain end to end:

- sweep the network for live hosts
- investigate the servers individually
- enumerate the training server's full port range
- confirm which services are behind those ports
- run service/version detection
- compare hosts to gauge relative attack surface
- identify the high-interest ports (SSH, FTP, MySQL, SMB, exposed HTTP)
- build an attack-surface inventory in a findings file
- identify the primary target and justify it
- document the services identified
- confirm the conclusion against the whole body of evidence

That last group is not a scanning exercise — it is **evidence documentation**, the same discipline §11 asks of you. It is the closest thing on this platform to the pre-exploitation half of a real engagement, and it is where the evidence for every exercise above comes from.

**What you cannot run here, stated plainly:** there is no Metasploit simulator on YushaCyber, so `search`, `info`, `use`, `show options`, `set`, `check`, `run` and `sessions` cannot be practised on this platform. To practise the framework itself you need your own authorized lab — a virtual machine you built, on a network you own, with intentionally vulnerable targets you installed yourself. The **Virtualization** module in the Beginner track is the groundwork for building exactly that.

## 14. Where This Goes Next

```
Metasploit (here)              →  controlled validation of what you found
Windows Privilege Escalation   →  what limited access on Windows becomes
Linux Privilege Escalation     →  the same question on Linux
Red Team track                 →  reconnaissance → enumeration → exploitation,
                                  at engagement scale
Active Directory Attacks       →  the offensive half of the domain you learned to read
```

All of them assume what this module built: that you can take a service, research it honestly, judge whether a technique applies, execute deliberately or decline with a reason, validate what actually happened, and write it down so somebody can act on it.

## 15. Knowledge Check

1. **Why does this lesson refuse to show you a simulated Metasploit session?**
   Because there is no Metasploit simulator on this platform, and fabricated output would teach you to trust console text that no engine produced — the exact habit that makes a tester's findings worthless.

2. **What is the correct conclusion from `21/tcp open ftp vsftpd 3.x` when the module you found targets 2.3.4?**
   The module is not applicable: the affected release is 2.3.4 and the identified family is 3.x. That conclusion is reachable from the scan output alone, before anything is run.

3. **Why stop rather than try the next FTP module?**
   Because trying modules without a hypothesis tests nothing, generates noise, risks disrupting a live service, and produces results you cannot explain. The failure was at the research link; the fix belongs there too.

4. **Why must `RPORT` be checked against your own evidence?**
   Because modules default to conventional ports. The real scan in this lesson found HTTP on 8080, not 80 — a module left on its default would have been pointed at a port with nothing on it.

5. **What must `LHOST` be, and what happens if it is wrong?**
   An address the target can actually reach — on this network, `10.10.10.20`. If it is wrong, a callback payload never connects and the exploit looks like a failure even when it worked.

6. **Why is "the module said the target appears vulnerable" not proof?**
   Because the check inferred it, often from a banner. A backported patch leaves the banner unchanged, so the signature can be present on patched code. It raises confidence; it does not settle the question.

7. **What proves a session is real?**
   That it responds to interaction, and that an independent observation is consistent with it. Being listed is a claim by the framework about itself.

8. **Why can a finding be professional with nothing exploited?**
   Because the deliverable is a defensible statement about risk. "Service identified, candidate vulnerability assessed as not applicable, here is the evidence" is a complete result — and most of a real report looks exactly like that.

9. **What makes an exposure finding legitimate without any vulnerability?**
   Reachability itself. A database service that answers from a position it should never be reachable from is a finding about network exposure and least privilege, independent of whether any flaw exists in it.

10. **What are the two fields that make a finding reproducible?**
    The exact options set, and the expected-versus-observed pair. Together they let someone else re-run the same test and confirm whether the result changed after remediation.

11. **Why does every exercise here end with "what would change your conclusion"?**
    Because a conclusion nothing could overturn is an assertion, not analysis. Naming the evidence that would change your mind is what makes a finding honest and reviewable.

12. **Why is authorization the first section of this lesson rather than a footnote?**
    Because exploit modules deliberately trigger faults in software that is running and doing someone's work. The risk exists whether or not the attempt succeeds, which makes written permission a technical precondition, not paperwork.

---

**Module complete.** You can now describe what Metasploit is, distinguish exploits from payloads and sessions from compromise, judge whether a module applies to a target, configure one deliberately, analyse a failure instead of guessing, validate a result against evidence, and write a finding somebody can act on.
