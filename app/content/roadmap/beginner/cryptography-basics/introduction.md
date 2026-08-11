# Introduction to Cybersecurity

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what cybersecurity actually means, and how it relates to the narrower terms "application security," "network security," and "operational security"
- explain the CIA triad — confidentiality, integrity, availability — and identify which one (or more) a given incident actually breaks
- recite and apply the core security reasoning chain: Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery
- ask the same eight questions a working security professional asks about any system, on demand
- state the one rule that separates legitimate security work from a crime

## 2. Why This Matters

Every module you've completed so far taught you how a system is *supposed* to work: Linux commands, network addressing, HTTP requests. Every module still ahead of you — Nmap, Burp Suite, the OWASP Top 10, Active Directory, and eventually offensive and defensive specializations — teaches what happens when that "supposed to" breaks down, and how to find, exploit, detect, or prevent that breakdown. This lesson is the bridge between the two. It doesn't teach an attack or a tool. It teaches the way of thinking that every attack, every tool, and every defense in this platform is an *instance of*. Skim this module and the rest of the roadmap will still make sense technically — but you'll be memorizing separate topics instead of recognizing the same eight-step pattern showing up again and again.

## 3. What Is Cybersecurity, Exactly?

"Cybersecurity" gets used as a catch-all, but the field actually has a nested structure, and the boundaries matter once you start specializing.

**Information security** is the broadest umbrella: protecting information — in any form, digital or not — from unauthorized access, alteration, or loss. A locked filing cabinet of paper records is an information security concern, even though nothing about it is "cyber."

**Computer security** narrows that to information that lives on computers specifically: the confidentiality, integrity, and availability of data stored, processed, or transmitted by computing systems.

**Cybersecurity** is closest to computer security in practice, but leans specifically into the *networked* and *adversarial* angle — protecting systems, networks, and data from threats that arrive over a network connection, from another party actively trying to cause harm. This is the frame the rest of this platform uses.

Within cybersecurity, you'll keep meeting three narrower specialties, each of which the roadmap eventually gives its own dedicated modules:

- **Application security (AppSec)** — security of the software itself: is this specific web application, API, or program built and coded safely? (This is where OWASP Top 10 and Web Pentesting live.)
- **Network security** — security of the infrastructure that carries traffic between systems: firewalls, segmentation, monitoring the wire. (This is where Nmap, Wireshark, and network-layer attacks live.)
- **Operational security (OpSec)** — the practices and habits that keep sensitive information from leaking through *process*, not code: who has access to what, how decisions get made, what gets said where. A perfectly coded application can still be compromised because an employee reused a password or a support agent got socially engineered over the phone — that's an OpSec failure, not an AppSec one.

These aren't interchangeable, and they aren't fully separate either — a real breach is very often a chain that crosses two or three of them. Keep that in mind: the rest of this document treats "cybersecurity" as the umbrella term, and names the specific specialty only when the distinction actually matters.

## 4. The CIA Triad

Ask "is this system secure?" and you'll get vague answers, because security isn't one property — it's three, and they're genuinely different from each other. This is the CIA triad, and it's the single most load-bearing model in the entire field.

**Confidentiality** — only authorized people or systems can *read* the data. A confidentiality failure is unauthorized disclosure: someone sees something they shouldn't.

**Integrity** — only authorized people or systems can *change* the data, and any unauthorized change is detectable. An integrity failure is unauthorized (or undetected) modification: something was altered, deliberately or accidentally, and either shouldn't have been or wasn't supposed to happen invisibly.

**Availability** — authorized people or systems can *access* the data or service when they legitimately need to. An availability failure is denial of legitimate access: the data or system still exists, but you can't get to it when you're supposed to be able to.

Ground this in something concrete: a hospital's electronic medical record system.

- **Confidentiality** means a stranger — or an employee with no legitimate reason — cannot read a patient's diagnosis or medication history.
- **Integrity** means no one can quietly change a patient's recorded blood type or allergy list without that change being visible and attributable to someone.
- **Availability** means the doctor treating that patient right now can actually open the record — a records system that's "perfectly secure" but too slow or too locked-down to use in an emergency has failed just as badly as one that leaks data.

**The part beginners usually miss: one incident can break more than one property at once, and they don't always fail together.** A ransomware attack that encrypts the hospital's records is primarily an **availability** failure — the data likely hasn't been read (confidentiality intact) or altered (integrity intact), but staff simply cannot access it, and in a hospital that alone can be dangerous. Compare that to an attacker who quietly edits a patient's allergy list without encrypting anything — no availability impact at all, staff can open the record just fine, but it's now an **integrity** failure with potentially life-threatening consequences, and it may not even get *noticed* as an incident until harm has already occurred. Same asset, same triad, completely different failure — this is exactly why treating "security" as one undifferentiated blob is a mistake: the response to a confidentiality breach (who saw what, and do we need to notify anyone?) is not the response to an availability breach (how fast can we restore service?), and neither is the response to an integrity breach (what changed, when, and can we trust anything since?).

## 5. The Core Reasoning Chain

Here is the model this entire module — and much of this platform beyond it — is built around. Read it once as a whole, then walk through what each link actually means:

```
ASSET → THREAT → VULNERABILITY → RISK → CONTROL → DETECTION → RESPONSE → RECOVERY
```

**Asset** — what are we protecting? Not an abstraction: a specific database, a specific set of credentials, a specific server, a specific person's ability to do their job.

**Threat** — what *could* harm that asset? A threat is a potential source or event — a person, a piece of software, an accident, even a natural event — that could cause harm. Not every threat is a malicious hacker; you'll see the full range in Core Concepts.

**Vulnerability** — what specific weakness could a threat actually take advantage of? A threat without a vulnerability to exploit generally can't cause harm; a vulnerability with no threat capable of reaching it is a much smaller concern.

**Risk** — how likely is this, and how bad would it be if it happened? Risk is what you get from combining a real vulnerability with a real threat capable of exploiting it — it's the thing an organization actually has to decide what to do about.

**Control** — what can we do to reduce that risk? A control is anything — a technical setting, a policy, a physical lock — that lowers either the likelihood or the impact side of the risk equation.

**Detection** — if a control fails or gets bypassed, how would we even know? Prevention is never perfect; detection is the safety net that assumes it eventually won't be.

**Response** — once we know something happened, what do we actually do about it, right now?

**Recovery** — how do we get back to normal operation, and make sure the same thing doesn't just happen again?

Notice the shape of this: it isn't a list of unrelated security topics to memorize — it's a single line of reasoning, in order, that you can walk through for *any* system, from a student's email account to a bank's entire production infrastructure. Core Concepts (next lesson) spends real time on the Asset → Threat → Vulnerability → Risk half of this chain; Hands-on Practice picks up Control → Detection → Response → Recovery and closes the loop with a full worked scenario.

## 6. The Security Mindset

Everything above compresses into a short, repeatable set of questions. A working security professional — whether they end up in SOC, pentesting, forensics, or AI security — asks some version of this list constantly, almost without noticing they're doing it:

1. What are we protecting?
2. Who might target it?
3. What could go wrong?
4. Where is the weakness?
5. What is the impact if it goes wrong?
6. What controls already exist?
7. How would we detect it happening?
8. How would we respond, and recover?

This list *is* the Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery chain, just phrased as questions instead of nouns. Practicing it now, on small, low-stakes scenarios, is exactly how it becomes automatic later, on real ones.

## 7. Common Mistakes

**Treating "secure" as a single yes/no property.** A system can be strongly confidential but weak on availability (heavily locked down, but falls over under load), or the reverse (always up, but leaking data). Always ask "secure *against what*, specifically" — the CIA triad exists to force that specificity.

**Assuming every threat is a hacker in a hoodie.** An employee accidentally emailing a spreadsheet to the wrong address, a fire damaging a server room, and a vendor's software shipping with a bug are all real threats this field has to account for — Core Concepts covers the full range.

**Skipping straight to "control" without doing the earlier steps.** Buying a security tool or writing a policy before you've identified the actual asset, threat, and vulnerability is a common, expensive mistake — a control that doesn't address a real risk is just cost with no benefit.

## 8. Practice

Think through this small scenario before moving on — you won't be graded on it, but working through it now is what makes the next two lessons click:

*A university student keeps all of their coursework, including unpublished thesis research, in a personal email account protected by a password they've reused on several other websites.*

1. Name the asset in one sentence.
2. Name one plausible threat.
3. Which part of the CIA triad would be hit hardest if someone else read that email account's contents without permission? Which part would be hit hardest if someone deleted everything in it instead?

## 9. Knowledge Check

1. What is the difference between information security, computer security, and cybersecurity, as this lesson defines them?
2. In your own words, what question does each letter of the CIA triad answer?
3. Give an example of one incident that damages two different CIA properties at once, and explain which two.
4. Put the eight links of the core reasoning chain in order, starting from "Asset."
5. Why does "control" come *after* "risk," not before it, in that chain?

## 10. Key Takeaways

- Cybersecurity is the broad, networked/adversarial-focused umbrella; application security, network security, and operational security are narrower specialties inside it, not synonyms for it.
- The CIA triad — confidentiality, integrity, availability — is three distinct properties, not one; a single incident can damage one, two, or all three, independently.
- The core reasoning chain — Asset → Threat → Vulnerability → Risk → Control → Detection → Response → Recovery — is the throughline for this entire module, and for most of the security topics you'll meet later in this platform.
- The security mindset is a repeatable set of eight questions, not a personality trait — it's a habit you build by practicing it deliberately, starting now.

## 11. What's Next

**Core Concepts** picks up the first half of the reasoning chain in depth: how to actually identify assets, how threats and threat actors differ, how a vulnerability is not the same thing as an exploit or a risk, and how authentication, authorization, and security controls fit into the picture — building directly on the login and permission examples you already saw in Web Fundamentals and Linux Fundamentals.
