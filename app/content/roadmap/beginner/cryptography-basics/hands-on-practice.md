# Hands-on Practice: Cryptography, Threats, and the Full Security Lifecycle

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain the difference between hashing, encryption, and encoding, and pick the right one for a given problem
- explain why passwords are stored hashed and salted, and what that actually defends against
- explain what a digital signature and a certificate each prove, without the common "signing is just encrypting with a private key" oversimplification
- distinguish virus, worm, trojan, and ransomware by their defining behavior, not a one-line label
- explain why phishing and social engineering work, and name real defenses against them
- connect logging to detection, and walk a fictional incident through the full response lifecycle
- explain backups as a security control, and why having backups isn't the same as having *recoverable* backups
- state, precisely, what makes a security test authorized
- walk a complete, unfamiliar scenario through the entire Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery chain, unassisted

## 2. Why This Matters

This is the lesson where the reasoning chain from Introduction and the vocabulary from Core Concepts stop being separate ideas and become one connected way of looking at a real system. It's also the module's namesake territory: cryptography is one of the oldest and most misunderstood parts of security, and getting hashing, encryption, and encoding straight in your head now will save you from a mistake that shows up constantly in real-world security incidents — treating three fundamentally different tools as if they were interchangeable.

## 3. Hashing, Encryption, and Encoding — Three Different Things

These three words get used almost interchangeably by beginners, and that confusion causes real, damaging mistakes — "we encoded it" is not the same claim as "we encrypted it," and neither is the same claim as "we hashed it." Each one solves a genuinely different problem.

**Hashing** is a one-way transformation: it takes an input of any size and produces a fixed-size output (a "hash" or "digest"), and it's specifically designed so you cannot reverse the process to recover the original input from the hash alone. The same input always produces the same hash, and even a tiny change to the input produces a completely different hash. Hashing is used for **integrity checking** (does this file match the hash it's supposed to?) and for **storing passwords** (Section 4 goes deep on this) — anywhere you need to verify something matches, without needing to recover the original value at all.

**Encryption** is a two-way, reversible transformation: it takes readable data (**plaintext**) and a **key**, and produces unreadable data (**ciphertext**) — and critically, it's designed to be reversed back into the original plaintext, but only by someone holding the correct key. Encryption is used for **confidentiality**: protecting data so that anyone without the key sees only ciphertext, while anyone with the key can recover the exact original.

**Encoding** is neither of the above — it's simply a format conversion, representing the same data in a different form (Base64 is the most common example you'll actually encounter). Encoding is fully, trivially reversible by *anyone*, with no key required at all — it exists to make data safe to transmit or store in a particular format (Base64 turns binary data into plain text characters), not to protect it from anyone. **Encoding is not security.** A string that's merely Base64-encoded is not "protected" in any meaningful sense — anyone can decode it instantly, with no secret required, which makes "we encoded the password" a genuinely dangerous claim to accept at face value.

| | Reversible? | Needs a key? | Protects | Typical use |
|---|---|---|---|---|
| **Hashing** | No (one-way, by design) | No | Integrity / verification | Password storage, file integrity |
| **Encryption** | Yes, with the correct key | Yes | Confidentiality | Protecting data in transit or at rest |
| **Encoding** | Yes, by anyone | No | Nothing | Safe transmission/storage of data in a given format |

One precise point worth stating carefully: cryptographic hashes are **designed** to be one-way — there's no mathematical trick that reverses a good hash function directly. That's a different claim from "a hashed password can never be recovered." A weak or common password can still be *guessed*: an attacker with a list of common passwords can hash each guess and check for a match (this is why password strength still matters even when passwords are always stored hashed — Section 4 covers exactly this).

## 4. Password Security

**Password reuse is the single most damaging habit in everyday account security.** If one site you use is ever breached and its (hopefully hashed) passwords leak, and you've reused that same password anywhere else, an attacker doesn't need to break your hash at all — they simply try the *leaked* password against your other accounts. This is called **credential stuffing**, and it succeeds constantly, at scale, entirely because of reuse, not because of any cryptographic weakness.

**A password manager** generates and stores a long, unique, random password for every single site, so reuse simply never happens — you only need to remember one strong master password (or use another factor) to unlock the manager itself.

**Multi-factor authentication (MFA)** adds a second, independent proof of identity beyond the password alone — typically something you *know* (the password), combined with something you *have* (a phone, a hardware key) or something you *are* (a fingerprint). MFA is exactly the "technical, preventive" control from Core Concepts, Section 9 — it directly stops the most common outcome of a leaked or guessed password: even a correct password alone is no longer enough to log in.

**On the server side**, real systems never store a password as plain, readable text — they store it **hashed**, and specifically **salted**: a random, unique value (the "salt") is generated per account and mixed in before hashing, so that even two users with the identical password end up with two completely different stored hashes. Salting exists specifically to defeat **rainbow tables** — precomputed lists of hashes for common passwords — because a precomputed table built for one salt is useless against a differently-salted hash, even for the exact same password. When a user logs in, the server hashes the password they just typed (with that account's salt) and compares it to the stored hash — it never needs to "decrypt" anything, because there's nothing reversible to decrypt in the first place; this is hashing's one-way property from Section 3, doing real security work.

## 5. Digital Signatures and Certificates, Conceptually

**A digital signature is not "encryption with a private key" — that's a common oversimplification, and it's worth understanding the actual mechanism instead.** A signature is built from hashing and asymmetric key cryptography together: the signer hashes the message (Section 3's one-way hash), then uses their **private key** — a secret only they hold — to produce a signature over that hash. Anyone holding the signer's matching **public key** — freely shareable, unlike the private key — can verify that the signature really was produced by the corresponding private key, over that exact message content.

```
Signing (done once, by the sender):
    message → hash(message) → sign with PRIVATE key → signature

Verifying (done by anyone, using the sender's public key):
    message → hash(message) ─┐
                              ├─→ do these match? → valid / invalid
    signature → verify with PUBLIC key ─┘
```

A valid signature proves three separate things at once, and it's worth naming all three:

- **Authentication** — the message really did come from whoever holds that private key.
- **Integrity** — the message hasn't been altered since it was signed (any change to the message changes its hash, which breaks the signature check).
- **Non-repudiation** — because only the holder of the private key could have produced a valid signature, the signer can't credibly claim later that they never signed it.

**Certificates** solve a different, related problem: how do you know a given public key actually belongs to the entity it claims to? A **certificate authority (CA)** — a trusted third party — verifies an entity's identity (for a website, typically that they genuinely control the domain) and then *signs* a certificate binding that entity's public key to their identity, using the CA's own private key. Your browser ships with a built-in list of root CAs it trusts; when it connects to a website over HTTPS, it checks that the site's certificate is signed by a CA (or a chain leading back to one) it already trusts — this is the **trust chain**, and it's precisely what Web Fundamentals' Hands-on Practice was referring to when it said TLS provides "server authentication": the certificate is the mechanism, and a CA's signature on it is why your browser is willing to believe it. This is also exactly why "the connection is HTTPS" only ever tells you *who you're actually talking to and that the channel is encrypted* — it says nothing about whether that server's application is itself secure, a distinction Web Fundamentals already made explicit and worth carrying forward here.

## 6. Malware Fundamentals

"Malware" is a category, not one thing — and the differences between its common types are about **behavior**, not severity. Real-world samples don't always fit one label perfectly, but the defining behaviors are worth knowing precisely:

- **Virus** — malicious code that attaches itself to a legitimate host program or file, and spreads only when that host is executed or shared. A virus needs a carrier; it doesn't move on its own.
- **Worm** — the defining trait is **self-propagation**: a worm spreads across a network on its own, actively seeking out and infecting other systems, with no human action and no host file required.
- **Trojan** — malicious functionality disguised as, or bundled inside, something that looks legitimate and useful. The defining trait is deception at the point of delivery, not any particular technical behavior once it's running.
- **Ransomware** — malware whose goal is extortion, typically by denying the victim access to their own data (most commonly by encrypting it) until a payment is made. This is precisely why ransomware is, first and foremost, an **availability** attack in CIA-triad terms, even though it often also involves stealing (a confidentiality breach) data before encrypting it, as extra leverage.
- **Spyware** — covertly collects information about a user or system, without their knowledge, and sends it elsewhere.
- **Botnet** — a network of compromised devices ("bots"), controlled remotely by an attacker, typically used collectively for further attacks (like flooding a target with traffic).
- **Rootkit** — malware specifically designed to hide its own presence and maintain privileged access, resisting detection and removal.

Don't over-index on perfectly classifying a real sample — professionals themselves argue about edge cases constantly, because real malware often combines behaviors (a trojan can deliver ransomware; a worm can install a rootkit). What matters at this stage is recognizing the defining behavior each name actually points to, so a description like "this spreads on its own across the network" tells you something specific and useful (worm-like), not just "bad software."

## 7. Phishing and Social Engineering

**Social engineering** is the general term for manipulating a person — not a system — into doing something that undermines security: revealing a credential, granting access, or taking an action they otherwise wouldn't. **Phishing** is its most common form: a fraudulent message, usually email, designed to trick the recipient into clicking a malicious link, opening a malicious attachment, or entering credentials into a fake page. **Spear phishing** is phishing targeted at a specific individual or organization, using researched, personalized details to be more convincing than a generic mass message. Related techniques include **pretexting** (fabricating a plausible scenario or false identity to extract information — "I'm calling from IT, I need to verify your password") and **baiting** (offering something tempting — a "free" download, a USB drive left where someone will find it — to get a victim to take the harmful action themselves).

**Why these attacks work is worth understanding, not just the fact that they do:** they exploit trust, urgency, and authority — a message that appears to come from a boss, a bank, or IT support, demanding immediate action, short-circuits the careful verification a person would normally apply. This isn't a failure of intelligence; it's a deliberate exploitation of normal human decision-making under time pressure.

**Real signals worth training yourself to notice:** a sender address that looks *almost* right but isn't; urgency or threats ("your account will be suspended in 1 hour"); a request that bypasses a normal process (a "CEO" emailing a wire-transfer request directly instead of through the usual approval chain); a link whose actual destination (visible by hovering, not clicking) doesn't match what it claims to be; a request for information a legitimate party would never actually need to ask for (like a full password).

**How organizations actually defend against this** is layered, matching Core Concepts' defense-in-depth principle directly: security-awareness training (administrative, preventive), email filtering that catches known-bad senders and links (technical, preventive), MFA so a phished password alone isn't enough to log in (technical, preventive), and verification procedures for high-risk actions like wire transfers — call the person back on a known number, don't just trust the email (administrative, preventive/corrective). No single layer catches everything; the combination is the actual defense.

## 8. Detection, Incident Response, and Recovery

**Logs are records of events** — an authentication log records every login attempt, a web log records every request a server received, a firewall log records what traffic was allowed or blocked. On their own, logs are just data. **Detection** is what happens when logs (or another signal) are actually reviewed — by a person or a tool — and something abnormal is recognized: the chain is *event → log → detection → investigation*, and skipping any link in it (generating logs nobody ever looks at, for instance) means detection never actually happens no matter how much data was technically recorded.

When detection succeeds, it feeds into **incident response** — a structured lifecycle, not an improvised scramble:

1. **Preparation** — having a plan, tools, and trained people *before* anything happens.
2. **Detection and Analysis** — recognizing that something abnormal occurred, and figuring out what it actually is.
3. **Containment** — stopping the incident from getting worse, right now, even before the full picture is known.
4. **Eradication** — removing the actual cause (malware, a compromised account, an attacker's persistence mechanism).
5. **Recovery** — restoring normal, trusted operation.
6. **Lessons Learned** — reviewing what happened and improving, so the same gap doesn't get exploited again.

Walk a small, fictional example through this exact lifecycle: a SOC analyst notices a login to an employee's account from a country that employee has never traveled to (**Detection and Analysis**). The analyst immediately disables that account's active sessions and forces a password reset (**Containment** — stopping further damage before the investigation is even finished). Reviewing the account's recent activity, the analyst finds and removes a mail-forwarding rule the attacker silently added, which would have quietly copied all future email to an external address (**Eradication** — removing the actual foothold, not just the symptom). The employee is issued a new password and re-enrolled in MFA, and normal access is restored (**Recovery**). Afterward, the team reviews how the account was compromised in the first place (a reused, previously leaked password — Section 4), and rolls out mandatory MFA for every account that doesn't already have it (**Lessons Learned** — turning one incident into a permanent improvement, not just a one-time fix).

**Backups** belong in this picture too, as a genuine security control, not just an IT convenience — they're what makes real recovery from ransomware or destructive attacks possible without paying an attacker or losing data permanently. But there's a distinction worth stating precisely: **having backups is not the same as having *recoverable* backups.** A backup that's never been tested for restoration might be corrupted, incomplete, or simply fail the moment it's actually needed — which is exactly why testing restores (not just running the backup job) is part of the control, not an optional extra. A backup that's constantly connected to the same network as the system it protects is also a weaker control against ransomware specifically, since ransomware that reaches the backup too can encrypt it right alongside the original — this is why offline or immutable backup copies matter for genuine ransomware resilience, not backups in general.

## 9. Ethics and Authorization

Every technique named in this lesson — and everything offensive you'll eventually learn elsewhere on this platform — sits on top of one non-negotiable line, and it's worth being completely explicit about it before you go any further in this field: **the fact that you are technically capable of doing something is never the same fact as being authorized to do it.**

**Authorized security testing** has specific, recognizable properties: a clearly **defined scope** (exactly which systems are in bounds, and which are explicitly not), **explicit permission** from someone with the actual authority to grant it, a **controlled environment** where the consequences of something going wrong are understood and contained, and **documented objectives** stating what the test is actually trying to determine. Every lab, mission, and terminal exercise on this platform exists specifically because it satisfies all four of these — a simulated, isolated environment, built and authorized for exactly this purpose.

**Unauthorized testing — even when well-intentioned, even against a system you personally have some legitimate access to, even "just to see if it works"** — can cause real harm, can violate the law, and can compromise systems and data that were never offered up for testing in the first place. "I found a way in" and "I was allowed to look for a way in" are two completely different statements, and only the second one describes legitimate security work. Hold onto this distinction deliberately as you move into more technical, more capable modules ahead — the tools get more powerful; the line around when you're allowed to use them against a real target doesn't move.

## 10. Capstone Scenario: YushaBank

**YushaBank** stores its customers' financial data in a web application. Its infrastructure includes: a public-facing web server, a backend database holding customer records, several employee accounts with normal access, one administrator account with full system access, and nightly backups of the database.

Before reading further, work through the security mindset questions from Introduction, Section 6, against this scenario yourself:

1. What are the assets here?
2. Who might target YushaBank, and why?
3. Where are the likely weaknesses?
4. What controls would reduce the risk at each weak point?
5. How would YushaBank detect something going wrong?
6. If something did go wrong, what would response and recovery look like?

Now walk it through the full chain, and compare your own reasoning to this one — there isn't a single "correct" answer to a scenario like this, but a strong answer touches each link in order, the way this one does:

**Asset** — the customer financial database is the highest-value asset by far (confidentiality of financial records, integrity of account balances); the web application's *availability* is its own separate asset (customers need to be able to log in and transact); the administrator account is an asset in the sense that whoever controls it effectively controls everything else.

**Threat** — cybercriminals financially motivated to steal financial data or extort the bank directly; an opportunistic attacker running automated scans against every bank-like site they can find, YushaBank included, without targeting it specifically; a malicious or careless insider with legitimate database access; a phishing email targeting an employee, per Section 7.

**Vulnerability** — a possible weak point: the administrator account protected by only a password, with no MFA. This is a real weakness — not yet an event.

**Risk** — combine that vulnerability with the threats above: an attacker who successfully phishes or guesses the administrator's password gains full system access, with high impact (the entire customer database) and non-trivial likelihood (admin accounts are always a priority target, precisely because of the access they grant).

**Control** — least privilege (do employee accounts genuinely need database-wide access, or only what their specific role requires?), MFA on every account, especially the administrator's, defense in depth layering several of these together, and a password policy paired with a password manager to prevent reuse.

**Detection** — authentication logs recording every login, especially to the administrator account, reviewed for anomalies like unfamiliar locations or times — precisely the "event → log → detection" chain from Section 8.

**Response** — if a suspicious administrator login is detected: contain it immediately (disable the session, force a password reset), consistent with the fictional incident walked through in Section 8.

**Recovery** — restore from the nightly backups if data integrity is in question, but only after confirming (per Section 8) that those backups are actually clean and restorable, and only after the attacker's access has genuinely been removed — restoring data while an attacker still has a foothold accomplishes nothing.

Notice what this walkthrough actually demonstrates: every single lesson in this module — CIA triad, assets, threats, vulnerabilities, risk, controls, cryptography, malware, phishing, detection, incident response, backups, ethics — is one coherent way of reasoning about **one scenario**, not a list of unrelated facts. That's the actual point of this entire module.

## 11. Common Mistakes

**Saying "we encoded it" when the real claim needed is "we encrypted it."** Encoding provides zero protection against anyone who wants to read the data — confusing the two in a real security decision is a serious, common error.

**Assuming a hashed password can never be recovered, full stop.** The hash function itself is one-way by design, but a weak or common password can still be guessed and confirmed against the hash — password strength still matters.

**Describing a digital signature as "just encryption with a private key."** It's built from hashing plus asymmetric keys together, and proves authentication, integrity, and non-repudiation as three distinct guarantees — not a simple encryption operation run in reverse.

**Assuming "we have backups" answers the recovery question by itself.** An untested, never-restored backup — or one sitting on the same network ransomware can reach — may not actually be recoverable when it matters most.

**Treating "I could access it" as the same thing as "I was authorized to access it."** This is the one mistake in this entire module with real legal and ethical consequences, not just a technical one — hold the line described in Section 9 deliberately, every time.

## 12. Knowledge Check

1. What is the difference between hashing, encryption, and encoding — and why is encoding not, by itself, a form of security?
2. Why does salting a password hash defeat a precomputed rainbow table, even against the exact same password?
3. What three separate things does a valid digital signature prove?
4. What is the defining behavioral difference between a worm and a virus?
5. Why is phishing described as an attack on a person, not a system — and name two layered defenses against it.
6. Put the six phases of incident response in order, and explain in one sentence what containment accomplishes that eradication doesn't.
7. Why isn't "having backups" the same claim as "having recoverable backups"?
8. What four properties make a security test authorized?

## 13. Key Takeaways

- Hashing is one-way (integrity, password storage); encryption is reversible with a key (confidentiality); encoding is a reversible format conversion with no security value at all — three different tools for three different jobs.
- Salting defeats rainbow tables by making every account's hash unique even for identical passwords; hashing being one-way doesn't mean a weak password can't still be guessed.
- A digital signature proves authentication, integrity, and non-repudiation together, built from hashing and asymmetric keys — not simply "encryption in reverse." A certificate authority's signature is what lets a browser trust that a public key really belongs to the site it claims to.
- Malware categories (virus, worm, trojan, ransomware, and others) are distinguished by behavior — self-propagation, disguise, extortion via denial of access — not by severity or a single generic label.
- Phishing and social engineering exploit trust, urgency, and authority in people, not flaws in a system — layered defenses (training, filtering, MFA, verification procedures) are the real countermeasure.
- Detection depends on logs actually being reviewed, not merely generated; incident response follows a real lifecycle — preparation, detection/analysis, containment, eradication, recovery, lessons learned.
- Backups are a security control only if they're tested and genuinely restorable, and resilient backups against ransomware specifically need to be offline or immutable, not just present.
- Being technically capable of accessing something is never the same as being authorized to — every later offensive-security module in this platform assumes you already hold this line without being reminded.

## 14. What's Next

This is the last lesson in Cybersecurity Fundamentals — every module ahead of you in this platform is now an application of the exact chain you just practiced on YushaBank: Nmap and Wireshark map attack surface and observe traffic; Burp Suite and the OWASP Top 10 hunt for and exploit application-layer vulnerabilities; Active Directory, Red Team, and eventually SOC and Blue Team content pick up detection, response, and recovery from the defender's side. The roadmap's next module, **Virtualization**, shifts back to infrastructure — but the reasoning habit you built in this module doesn't reset; you'll keep reaching for "what's the asset, what's the threat, where's the weakness" every time a new topic in this platform asks you to think about security instead of just syntax.
