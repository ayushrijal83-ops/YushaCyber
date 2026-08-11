# Core Concepts: Assets, Threats, Vulnerabilities, and Controls

## 1. What You Will Learn

By the end of this lesson you should be able to:

- identify the assets in a given system, in categories, not just "data"
- distinguish threats from threat actors, and describe a threat actor by motivation, capability, resources, target, and opportunity instead of a stereotype
- keep vulnerability, exploit, attack, and risk as four separate ideas, and use each one correctly in a sentence
- explain why the same vulnerability can carry very different risk depending on context
- explain the difference between authentication, authorization, and accounting using this platform's own login example
- classify a security control by category and by function, and explain why real controls often belong to more than one category at once
- explain least privilege and defense in depth, and connect both to Linux permissions you've already used

## 2. Why This Matters

The Introduction gave you the chain: Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery. This lesson is where the first five links stop being abstract nouns and become a toolkit you can actually apply. Every later module in this platform assumes you can already tell a vulnerability apart from an exploit, and a threat apart from a threat actor — get sloppy with these words now, and every conversation about risk later gets harder than it needs to be.

## 3. Assets: What Are We Protecting?

Security decisions have to start somewhere concrete, and that starting point is always the asset — anything with value to an organization or person, worth protecting because losing it, having it altered, or having it exposed would cause real harm. "Data" is too vague; assets come in recognizable categories:

| Category | Examples |
|---|---|
| Accounts and credentials | usernames, passwords, session tokens, API keys |
| Data | customer records, financial data, source code, intellectual property |
| Infrastructure | servers, network devices, endpoints, cloud resources |
| Services | the *availability* of an application itself — an online store being reachable is an asset in its own right, separate from the data behind it |
| People | staff whose time, safety, or trust can be targeted (this is why social engineering is a real security topic, not a side note) |

You've already handled real assets on this platform without naming them as such: a file's contents and its permissions (Linux Fundamentals), a session cookie and a login credential (Web Fundamentals), a network's addressable hosts (Computer Networking) — every one of those is an asset a real attacker would specifically want.

**Why this matters first, before anything else:** you cannot reason about threats, vulnerabilities, or risk in the abstract — every one of those words only means something *relative to* a specific asset. "Is this a risk?" is not a complete question; "is this a risk *to the customer database*?" is.

## 4. Threats and Threat Actors

A **threat** is any potential source or event that could cause harm to an asset. Note the word "potential" — a threat doesn't have to be actively attacking anything right now to count; it just has to be capable of causing harm under the right conditions. Threats come from several genuinely different categories, and collapsing all of them into "a hacker" is one of the most common beginner mistakes in this field:

- **Malicious external attackers** — people outside the organization deliberately trying to cause harm.
- **Malicious insiders** — employees or contractors with legitimate access who misuse it deliberately.
- **Malware** — self-propagating or attacker-deployed software, which you'll study in more depth in Hands-on Practice.
- **Accidental actions** — an employee misconfiguring a server, emailing the wrong attachment, or losing a laptop; no malice at all, real harm regardless.
- **Environmental and natural events** — fire, flood, power loss — availability threats that have nothing to do with anyone attacking anything.
- **Supply-chain risks** — a vendor, library, or contractor your organization depends on becoming the actual point of compromise.

When the threat *is* a person, it's useful to describe them as a **threat actor** — and here too, resist the single stereotype. Real threat actor categories include cybercriminals (financially motivated), nation-state actors (well-resourced, often patient and targeted), hacktivists (ideologically motivated), malicious insiders (already covered above), opportunistic attackers (scanning broadly for whatever's easy, not targeting anyone specifically), and security researchers (who find and report weaknesses — not every category is adversarial). Instead of trying to memorize which category is "most dangerous," it's far more useful to describe any threat actor along five dimensions:

| Dimension | Question |
|---|---|
| Motivation | Why would they do this — money, ideology, curiosity, access? |
| Capability | What skill and technical ability do they actually have? |
| Resources | Time, funding, tooling — how much can they bring to bear? |
| Target | Are they after this asset specifically, or is it incidental? |
| Opportunity | Is there currently a way in, or would they have to create one? |

A nation-state actor with high capability and resources but no interest in a small hobby blog is a much smaller real-world concern to that blog's owner than an opportunistic attacker running automated scans against every server on the Internet, including that blog's — capability alone doesn't determine relevance; motivation and target do.

## 5. Vulnerability, Exploit, Attack, and Risk — Four Different Words

These four terms get blurred together constantly in casual conversation, and keeping them distinct is one of the most practically useful habits you can build this early. Walk through one concrete example:

*A public-facing server is running a web application framework with a known, unpatched security bug that lets an attacker read files outside the intended directory.*

- **Vulnerability** — the outdated, unpatched framework itself. This is the weakness: a flaw or gap that *could* be taken advantage of. On its own, a vulnerability is a fact about the system, not yet an event.
- **Exploit** — the specific technique, code, or sequence of steps that actually takes advantage of that weakness. An exploit is what turns "there is a weakness" into "here is how you'd actually abuse it."
- **Attack** — an exploit, actually carried out against a real target, by a real threat actor, right now. The exploit is the method; the attack is the method being used.
- **Risk** — the resulting possibility of harm, considering how likely this attack is and how bad it would be if it succeeded. Risk is what an organization decides whether to act on — it's the output of combining the vulnerability with a threat actor capable of exploiting it.

Say it as one sentence and the chain becomes obvious: *a vulnerability, combined with a threat capable of exploitation, creates risk; an exploit is the tool that turns capability into an actual attack.* Never collapse these into one interchangeable word — "we have a vulnerability" and "we're under attack" are describing two completely different points on this chain, with very different appropriate responses.

## 6. Risk: Likelihood and Impact, Not a Universal Formula

Risk is usually described as a function of two things: **likelihood** (how probable is this, realistically?) and **impact** (how bad would it be if it happened?). It's tempting to want a single formula everyone uses — but real organizations weigh likelihood and impact differently depending on their own context, tolerance, and priorities, so treat "risk = likelihood × impact" as a useful mental shorthand, not a universal calculation every organization performs identically.

What doesn't vary is that the *same vulnerability* can carry very different risk in different contexts. Compare two systems, both running the exact same outdated, vulnerable software from the example above:

- **System A**: a critical production database, holding real customer financial records, directly exposed to the public Internet.
- **System B**: an isolated test machine on a lab network with no Internet access at all, containing only synthetic, made-up test data.

Identical vulnerability. Wildly different risk. System A has both high likelihood (anything Internet-facing gets probed constantly by opportunistic scanning) and high impact (real financial data, a production service). System B has low likelihood (nothing can reach it to exploit it) and low impact (nothing of value would be exposed even if it somehow were). This is exactly why "we have a vulnerability" is never, by itself, enough information to decide what to do — the *same* weakness genuinely warrants an emergency patch on System A and can reasonably wait on System B, and a security program that treats every vulnerability identically, regardless of context, wastes effort on the low-risk ones while the high-risk ones wait in the same queue.

## 7. Attack Surface

An **attack surface** is the complete set of points where an unauthorized party could try to get in or extract something — every exposed component is one more place something could go wrong. For a typical organization, that includes open network ports, exposed services, web applications and APIs, user accounts (especially ones reachable from outside), cloud resources, endpoints (laptops, phones), and third-party integrations.

You already have the vocabulary for a piece of this from Computer Networking: a listening port is, quite literally, one square inch of attack surface — it means a real service is running and reachable, and every reachable service is one more thing that has to be correctly configured and kept patched. More exposed components does not automatically mean *insecure* — but it does mean *more opportunities* for something to be misconfigured, forgotten, or left unpatched. This is the conceptual foundation for reconnaissance and enumeration (tools like Nmap, later in this platform): before you can defend or test anything, you have to know what's actually exposed in the first place. This lesson stops at the concept — mapping a real attack surface with real scanning tools is Nmap's job, not this one's.

## 8. Authentication, Authorization, and Accounting (AAA)

You've already met two of these three ideas — this is where they get named properly, and a third one joins them.

**Authentication answers: "Who are you?"** It's the process of proving identity — a username and password, a fingerprint, a hardware key.

**Authorization answers: "What are you allowed to do?"** Being authenticated doesn't automatically grant every possible permission — it establishes *who* you are, and a separate check decides what *that identity* is allowed to do.

**Accounting** (sometimes called auditing) answers: **"What did you actually do?"** — the record of activity, kept after the fact. Accounting is why systems keep logs: authentication and authorization tell you what's *supposed* to happen at the moment of a request; accounting is the trail that lets someone reconstruct what *actually* happened afterward, which is the only way an incident can ever be investigated properly. You'll meet this again as the foundation of logging, and eventually SOC work, further into this platform.

Recall the exact example from Web Fundamentals' Hands-on Practice lesson, because it demonstrates authentication and authorization as two genuinely separate checks, not one:

```
GET /admin HTTP/1.1

HTTP/1.1 401 Unauthorized
```

No session cookie at all — the server doesn't know who's asking. This is an **authentication** failure.

```
GET /admin HTTP/1.1
Cookie: session_id=student-session

HTTP/1.1 403 Forbidden

{"error": "Forbidden", "message": "You are authenticated, but not authorized to access this resource."}
```

Now there's a valid session — the server knows exactly who's asking, a logged-in training account — and still refuses, because being logged in is not the same as being allowed into `/admin`. This is an **authorization** failure. Successfully logging in only ever proves authentication; it never, by itself, proves that every subsequent action is authorized — a point that becomes directly relevant the moment you start thinking about access control as its own attack surface.

## 9. Security Controls

A **control** is anything that reduces risk — by lowering likelihood, lowering impact, or both. Controls are usually described along two independent axes, and it's worth understanding both rather than memorizing one flat list.

**By category** — *what kind of thing the control is:*

- **Administrative** — policies, training, and procedures (a password policy, security-awareness training, a background-check requirement).
- **Technical** — mechanisms enforced by technology (multi-factor authentication, firewalls, encryption, access control lists).
- **Physical** — controls over the physical world (locked server rooms, badge access, security cameras).

**By function** — *what point in the timeline the control acts at:*

- **Preventive** — stops an incident before it happens (MFA blocking a login with only a stolen password).
- **Detective** — notices something happened (security logs, intrusion detection alerts).
- **Corrective** — restores or fixes things after an incident (an incident-response runbook, restoring from backup).

These two axes are independent, and real controls very often sit at the intersection of both rather than fitting one single box: **multi-factor authentication is technical *and* preventive**; **security logging is technical *and* detective**; **a documented incident-recovery procedure is administrative *and* corrective**. Don't force every control into exactly one category — the honest, useful description is often "technical, mostly preventive, with a detective side effect" (MFA failure attempts, for instance, are themselves a signal worth logging).

## 10. Defense in Depth and Least Privilege

Two principles govern how good controls actually get combined in practice.

**Defense in depth** means layering multiple, different controls so that one failure doesn't equal total compromise. A single control failing is normal and expected over a long enough timeline — the point of layering is that an attacker who gets past one layer still has to get past the next one, and the one after that:

```
Strong, unique password
    +
Multi-factor authentication
    +
Least privilege (below)
    +
Network segmentation
    +
Endpoint protection
    +
Logging and monitoring
    +
Tested backups
```

No single item on that list is unbreakable. The design assumption isn't "nothing will ever fail" — it's "no single failure should be catastrophic on its own."

**Least privilege** means a user, account, or process should have only the access it actually needs to do its job — nothing more. You've already applied this principle directly, even before this lesson named it: recall `chmod` from Linux Fundamentals' Hands-on Practice, and specifically why `chmod 777` (read, write, and execute for literally everyone) was called out as almost always the wrong fix. That warning *was* least privilege, applied at the filesystem level — a process or user granted broader access than it needs doesn't become more secure by accident; it becomes a larger prize if it's ever compromised, because an attacker who compromises it inherits whatever access it was needlessly given. The same principle scales up everywhere you'll go next: a database account used by a web application should be able to read and write only the tables it needs, not administer the entire database; a cloud IAM role should be scoped to exactly the resources a service touches, not granted account-wide access "to be safe." "Give it enough access to work, and not one permission more" is the same sentence at every layer of a real system.

## 11. Common Mistakes

**Saying "vulnerability" when you mean "risk," or "attack" when you mean "exploit."** These words point to different, adjacent links in the same chain — precision here isn't pedantry, it's what lets a team communicate about severity accurately.

**Assuming a control belongs to exactly one category.** MFA is not *only* preventive, and a firewall is not *only* technical in every possible discussion of it (the policy deciding what the firewall should block is administrative). Real controls overlap; force-fitting them into one box loses information.

**Confusing "authenticated" with "authorized."** A successful login proves identity, nothing more — every later access decision is a separate question, one this platform will keep returning to.

**Treating attack surface as inherently bad.** Some exposure is unavoidable — a public web server has to be reachable to do its job. The goal isn't zero attack surface; it's knowing exactly what your attack surface is and making sure every piece of it is intentional and maintained.

## 12. Practice

For each item below, classify it as primarily an **asset**, a **threat**, a **vulnerability**, or a **control** — and for the controls, name whether each is more preventive or more detective:

1. A company's customer payment database.
2. An employee who clicks a link in a fraudulent email without realizing it.
3. A web server still running a two-year-old, unpatched version of its software.
4. A firewall rule blocking inbound traffic on unused ports.
5. A log file recording every failed login attempt.

## 13. Knowledge Check

1. Why is "is this a risk?" an incomplete question without naming a specific asset?
2. Give one example each of a threat that is not a malicious external attacker.
3. In one sentence each, define vulnerability, exploit, attack, and risk — using the outdated-server example from Section 5 if it helps.
4. Why can the exact same vulnerability represent very different risk in two different systems?
5. What does accounting add on top of authentication and authorization, and why does an investigation depend on it specifically?
6. Give a real control and explain why it could reasonably be described as belonging to two categories at once.

## 14. Key Takeaways

- Assets come in recognizable categories (accounts, data, infrastructure, services, people) — naming the specific asset is always the first step, not an afterthought.
- A threat is a potential source of harm; a threat actor is a person behind one, better described by motivation/capability/resources/target/opportunity than by a single label.
- Vulnerability (the weakness), exploit (the method), attack (the method used for real), and risk (the resulting possibility of harm) are four distinct ideas, not synonyms.
- Risk depends on both likelihood and impact, and the same vulnerability can carry very different risk depending entirely on context.
- Authentication (who are you), authorization (what can you do), and accounting (what did you do) are three separate checks — passing one never guarantees the others.
- Controls are classified by category (administrative/technical/physical) and by function (preventive/detective/corrective) — most real controls span more than one box on purpose.
- Defense in depth layers controls so no single failure is catastrophic; least privilege limits what any one account or process can do if it's ever compromised — you've already applied both, without the names, in earlier modules.

## 15. What's Next

**Hands-on Practice** closes the loop: how cryptography (hashing, encryption, and encoding — three genuinely different things) protects data at rest and in transit, how malware and social engineering actually work, how detection and incident response pick up where prevention leaves off, why authorization to test a system is a hard legal and ethical line, and a full worked scenario that walks the entire Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery chain from end to end.
