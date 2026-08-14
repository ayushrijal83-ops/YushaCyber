# Authentication, LDAP, Kerberos and Group Policy

## 1. What You Will Learn

By the end of this lesson you should be able to:

- separate **authentication** from **authorization** in a domain, and say which component decides each
- explain **Kerberos** at a working conceptual level: AS, TGS, **TGT**, **service ticket**, **KDC**
- say why a client obtains tickets instead of sending a password to every service
- describe where **NTLM** still fits, without either dismissing it or excusing it
- explain what **LDAP** is for, and why "LDAP authenticates Windows users" is the wrong sentence
- explain **Group Policy**, **GPOs**, and the real relationship between a GPO and an OU
- read an **ACL** and work out a user's *effective* access from group membership
- place **forest**, **tree**, **domain**, **OU**, **group** and **ACL** correctly as boundaries and containers
- apply least privilege, separation of duties and delegation as design principles rather than slogans

Everything quoted from the console below is real output from this platform's simulated **YUSHA.LOCAL** training domain. Where the platform cannot demonstrate something — LDAP, NTLM, forests and trusts — the lesson says so and labels its examples.

## 2. Authentication Is Not Authorization

You met this pair in **Web Fundamentals** and again in the **OWASP Top 10** module, where broken access control was the single most common category. It is the same distinction here, with different machinery underneath.

| | Question | Answered by, in a domain |
|---|---|---|
| **Authentication** | *Who are you?* | The **KDC** on a Domain Controller, via Kerberos |
| **Authorization** | *What may you do with this specific resource?* | The **resource**, by comparing your groups against its ACL |

Read that right-hand column twice, because the split is architectural and it is the key to the whole module: **the Domain Controller proves identity; the file server decides access.** Two different machines, two different decisions.

The concrete version. Alice authenticates successfully to the domain. That does **not** mean she can read:

- the Finance share — that depends on the Finance share's ACL
- HR records — that depends on the HR share's ACL
- anything a Domain Admin can reach — that depends on her being in that group, which she is not

The training domain demonstrates the split directly. Here is an account that *cannot even authenticate*:

```
ACCESS DENIED — 'mrai' cannot authenticate: the account is locked out.
(No Kerberos ticket → no access, whatever the ACL says.)
```

Note the order that failure happens in. Authentication is evaluated **first**; the ACL is never consulted, because there is no verified identity to compare it against. And here is an account that authenticates perfectly well and is *still* limited by authorization:

```
ACCESS GRANTED — 'skhadka' has READ on 'Finance-Reports' (\\FS-01\Finance-Reports).
  · via group 'IT Support' → READ
```

Sujal Khadka is the IT Manager. He authenticated. He gets **READ**, not WRITE, because that is what the resource grants the group he is in. Identity established, access constrained — the two decisions visibly separate.

## 3. Kerberos — the Model

**Kerberos is the primary authentication protocol of a modern Active Directory domain.** It is not Microsoft's invention (it comes from MIT) and it is not Windows-only, but AD's implementation of it is what authenticates domain logons and domain resource access by default.

The problem it solves is worth stating before the mechanism. In a network with one identity authority and many services, the naive design is: the client sends the user's password to each service, and each service checks it. That design is bad in three separate ways, and you should be able to name all three:

1. **Every service sees the password.** Compromise any one service and you have credentials good everywhere.
2. **Every service must be able to verify passwords**, which means every service needs access to credential material.
3. **The password crosses the network repeatedly**, multiplying exposure with every access.

Kerberos replaces that with **tickets**: time-limited, cryptographically protected proofs, issued by a trusted third party, which a service can validate *without* ever seeing the user's password and *without* asking the authority in real time.

The flow, in the shape you should be able to draw from memory:

```
Client
  │  (1) AS-REQ  — "I am this user, here is proof"
  ▼
Authentication Service          ┐
  │  (2) AS-REP  — a TGT        │
  ▼                             │  both live in the
Ticket Granting Service         │  KDC, on a Domain
  │  (3) TGS-REQ — "here's my   │  Controller
  │      TGT, I need a ticket   │
  │      for this service"      │
  │  (4) TGS-REP — service      │
  ▼      ticket                 ┘
Target Service
     (5) AP-REQ — client presents the service ticket
     (6) the service checks its own ACL against the identity
         and groups carried in that ticket
```

The three terms, precisely:

| Term | What it is |
|---|---|
| **KDC** — Key Distribution Center | The Kerberos authority. Conceptually two services: the **Authentication Service (AS)**, which issues TGTs, and the **Ticket Granting Service (TGS)**, which issues service tickets. In an AD domain, the KDC runs **on the Domain Controllers** — it is not a separate machine |
| **TGT** — Ticket Granting Ticket | Proof that the KDC authenticated you. Obtained once, at logon; time-limited. It is not usable *at* a service — its only purpose is to let you request service tickets without re-authenticating |
| **Service ticket** | Proof, presented to one specific service, that the KDC vouches for you. Carries your identity and group memberships. The service validates it and consults its own ACL |

## 4. Watching It Happen

This platform's simulator renders the exchange step by step. Real output for a healthy account:

```
KERBEROS AUTHENTICATION — Sujal Khadka (YUSHA.LOCAL)
────────────────────────────────────────────────────────
[1] AS-REQ   skhadka → DC-01 (KDC): "I am skhadka, here is proof (encrypted timestamp)"
[2] AS-REP   DC-01 → skhadka: TGT (Ticket-Granting Ticket), valid 10h
[3] TGS-REQ  skhadka → DC-01: "here is my TGT — I need a ticket for cifs/FS-01"
[4] TGS-REP  DC-01 → skhadka: service ticket for cifs/FS-01
[5] AP-REQ   skhadka → FS-01: presents the service ticket
[6] ACCESS   the SERVER now checks its ACL against the user's group SIDs carried in the ticket

✓ Authentication succeeded. Note the separation of duties:
  · the KDC proves WHO you are (authentication)
  · the resource's ACL decides WHAT you may do (authorization)
Run `access skhadka <share>` to see step [6] in action.
```

Five things in that output are worth reading slowly.

**Step [1] sends "proof", not the password.** The proof is derived from the user's credential — the simulator names it as an encrypted timestamp — and the KDC can verify it because it holds the corresponding key material. The password itself is not transmitted for the service to inspect.

**Step [2] issues a TGT valid for ten hours.** Time-limiting is deliberate: a stolen ticket is useful for a bounded period, unlike a stolen password.

**Step [3] names a service, not a machine.** `cifs/FS-01` is a *service principal name* — the file-sharing service on that host. Tickets are issued per service, so a ticket for one service is not a ticket for another.

**Step [5] goes to the service, not the DC.** This is the payoff. Once you hold the service ticket, the file server validates it **on its own**. The Domain Controller is not contacted again for that access — which is why a domain of thousands of machines does not melt its DCs, and why "the DC is momentarily unreachable" does not instantly break every open session.

**Step [6] is the authorization step, and it happens somewhere else.** The ticket carries the user's group memberships; the *server* compares them to its own ACL. The KDC has no opinion about the HR share.

Now failure. Real output for the locked-out account:

```
KERBEROS AUTHENTICATION — Manisha Rai (YUSHA.LOCAL)
────────────────────────────────────────────────────────
[1] AS-REQ   mrai → DC-01 (KDC): "I am mrai, here is proof (encrypted timestamp)"
[2] AS-REP   DC-01 → KDC_ERR_CLIENT_REVOKED

✗ REFUSED — the account is LOCKED OUT (14 failed attempts). The lockout policy is doing its job; unlock only after confirming the owner is in control of the credentials.
```

The exchange stops at step 2. No TGT, therefore no service ticket, therefore no access to anything — regardless of what any ACL says. That is authentication failing closed, which is what it should do.

## 5. Why Tickets, Restated

If you take one thing from this section, take this answer, because it is the question every interviewer asks:

> **Why does the client obtain a service ticket instead of sending the user's password to every service?**

Because the password would then be exposed to every service that received it, each of those services would need to be able to verify credentials, and the secret would cross the network once per access. Tickets invert all three: the service **never sees the password**, it validates the ticket using key material it already shares with the KDC, and the user's secret is used **once**, at logon, to obtain a TGT.

There is a fourth benefit worth knowing: the service ticket carries the user's **group memberships**, so the service can make its authorization decision immediately, without querying the directory on every access. That is also why group membership changes may not take effect until the user obtains fresh tickets — a real operational behaviour that confuses people who expect "I added them to the group, why can't they get in?"

## 6. NTLM

**NTLM** is an older Microsoft authentication protocol family. It predates AD's use of Kerberos, and it is still present in Windows environments today.

The balanced picture, because both extreme positions are wrong:

**Why it still exists.** Kerberos has requirements NTLM does not: it needs the client to be able to reach a KDC, it needs reasonably synchronised clocks, and it generally needs to identify the target by name rather than by raw IP address. When those conditions do not hold — connecting to a host by IP, a machine that is not domain-joined, an application or appliance that never implemented Kerberos, some cross-boundary cases — Windows may fall back to NTLM so the connection works at all. Compatibility is a real engineering requirement, not laziness.

**Why it is a concern.** NTLM is a challenge-response scheme with weaker properties than Kerberos: it does not provide mutual authentication in the way Kerberos does, its cryptographic underpinnings are dated, and — the operationally important part — the material it uses can be captured and, in certain conditions, replayed or attacked offline. A large part of why modern AD security guidance pushes toward Kerberos is to reduce the number of places NTLM is used at all.

**What good practice looks like:** prefer Kerberos wherever it can work; *monitor* where NTLM is actually being used (most organisations are surprised); reduce those cases deliberately; and restrict or disable NTLM only once you know what would break — turning it off blind is a reliable way to take an environment down.

> **WRONG:** "NTLM is always insecure and nobody uses it."
> **CORRECT:** NTLM is a legacy protocol with weaker security properties than Kerberos, still encountered as a fallback and for compatibility. Modern environments prefer Kerberos and work to reduce NTLM use — which is not the same as it being absent.

> **WRONG:** "Every Windows domain uses only one authentication protocol."
> **CORRECT:** Real environments routinely have more than one mechanism in play. Assuming a single protocol will mislead you when you investigate.

**This platform does not simulate NTLM.** The training domain's authentication flow is Kerberos only, so there is no NTLM output to quote and none is invented here.

## 7. LDAP

**LDAP** — the Lightweight Directory Access Protocol — is a protocol for **reading and modifying directory information**. It is an open standard, not a Microsoft one, and AD DS speaks it: it is how applications and administrative tools query the directory for objects and attributes.

Now the distinction this section exists for, because it is the single most common confusion in this whole subject:

| | LDAP | Kerberos |
|---|---|---|
| **Purpose** | Access directory data — search, read, modify | Authenticate identities |
| **Typical question** | "Which users are in the Engineering department?" | "Is this really Manisha Rai?" |
| **Returns** | Directory objects and their attributes | Tickets |
| **Role in a Windows logon** | Not the authenticating protocol | The authenticating protocol |

> **WRONG:** "LDAP is the authentication protocol for Windows domains."
> **CORRECT:** LDAP is a **directory access** protocol. Kerberos is the primary **domain authentication** protocol. They do different jobs, and both talk to Domain Controllers.

The reason people conflate them is that LDAP *does* have an authentication step of its own — a client must bind (identify itself) before it can query, and one way to bind is with a username and password. That authenticates the client **to the LDAP service, for the purpose of running directory queries.** It is not what happens when a user logs on to a domain-joined workstation, and it is not what issues the tickets that get them to a file share. Some non-Windows applications *do* use an LDAP bind as their own login check against AD — which is a real pattern, and still not the domain's logon mechanism.

**Illustrative example — not captured output. This platform has no LDAP simulator** (the training domain is a data structure, not a directory server), so nothing here is quoted from a running service. Conceptually, a query means:

```
Client                     "find every enabled user whose department
   │                        is Engineering; return their names and titles"
   │  LDAP query
   ▼
Domain Controller
   │  searches the directory from a starting container downward,
   │  matching objects against the filter
   ▼
Matching objects returned, with the attributes that were asked for
```

Three properties of that exchange matter for security:

1. **It is a search, and searches have a scope** — a starting point in the hierarchy and a depth. Where you start determines what you can find.
2. **Ordinary users can read a great deal of the directory.** That is by design; a directory that nobody may read is not much use. It also means "what can an authenticated but unprivileged account learn?" is a genuine question, and the answer is usually "more than the organisation expects".
3. **It should be protected in transit.** A bind that sends a password over an unencrypted channel is exactly the **Cryptographic Failures** problem from the OWASP module, in a different suit.

**What this platform gives you instead of LDAP** is the same *reasoning* through an administrative console: query the directory for users, groups, OUs, computers and shares, and read the attributes that come back. The protocol differs; the question — *what does the directory say?* — is identical, and it is the question that transfers.

## 8. Group Policy

**Group Policy** is how configuration is delivered to machines and users across a domain, centrally and repeatedly. A **Group Policy Object (GPO)** is a named collection of settings; it is *linked* to a scope; and clients apply the policy that targets them at startup, at logon, and periodically thereafter.

Two halves, and mixing them up causes real confusion:

- **Computer Configuration** — applies to the *machine*, whoever is logged on (or nobody). Security options, service configuration, firewall rules, machine-wide software settings.
- **User Configuration** — applies to the *user*, whichever machine they log on to. Desktop environment, drive mappings, user-scoped restrictions.

The training domain has three real GPOs. This is genuine console output:

```
GPO: Default Domain Policy
  Linked to : domain
  Kind      : security
  Password  : min 12 chars, complexity on, max age 90d
  Lockout   : 5 attempts / 15min window / 30min lock

GPO: Desktop Restrictions
  Linked to : interns, workstations
  Kind      : desktop
  Control Panel: denied
  Cmd Prompt: denied
  Usb Storage: denied
  Wallpaper : locked

GPO: Login Script
  Linked to : domain
  Kind      : script
  Script    : logon.bat
  Map H Drive: \\FS-01\Home\%username%
  Map S Drive: \\FS-01\Public
```

Read the `Linked to` line on each — that is the scope, and it is the whole subject of §9.

The security-relevant reach of Group Policy is much broader than the "wallpaper and drive letters" reputation it sometimes has. Real examples, several of them visible above:

| Setting area | Why it is security-relevant |
|---|---|
| **Password policy** | Sets the floor for every credential in the domain |
| **Account lockout** | Bounds online password guessing |
| **Endpoint protection configuration** | Ensures protection is on and configured the same way everywhere |
| **Firewall settings** | Consistent host-based network restrictions |
| **Software restrictions / execution control** | Constrains what may run |
| **Audit policy** | Decides what gets *logged* — which, per the OWASP module's A09, decides whether anyone could ever detect an incident |
| **User rights assignment** | Who may log on locally, log on over the network, back up files, and so on |

> **WRONG:** "Group Policy is only for cosmetic Windows settings."
> **CORRECT:** Group Policy can enforce significant security configuration — password and lockout policy, audit policy, firewall rules, execution control, user rights. A weak GPO is a weakness applied consistently across the whole scope, which is worse than a weakness on one machine.

One honest caveat, so you do not over-generalise: **not everything is configured through Group Policy.** Modern Windows environments also use device-management platforms, configuration-management tooling, and settings applied by the applications themselves. GPO is a major mechanism, not the only one.

## 9. GPOs and OUs — the Actual Relationship

This trips people constantly, so state it as three separate facts:

- An **OU** is a *container* for objects.
- A **GPO** is a *collection of settings*.
- A GPO can be **linked** to a scope: a **site**, a **domain**, or an **OU**.

> **WRONG:** "OU = GPO."
> **CORRECT:** They are different kinds of thing. A GPO is linked *to* an OU (or to a domain, or to a site). One GPO can be linked to several places; one OU can have several GPOs linked to it.

Which means **where an object sits determines which policy reaches it.** Look at the real output again:

- `Default Domain Policy` is linked to **domain** — it reaches everything in the domain.
- `Desktop Restrictions` is linked to **interns** and **workstations** — it reaches objects in those two OUs and nothing else.

So moving a user object between OUs can change the policy that applies to them. That is a legitimate and common administrative action — and it is precisely why "which OU is this object in?" is a question with consequences, even though the OU itself grants no permissions.

Two more mechanics worth knowing by name, since real environments use both: policy from several linked GPOs is **combined**, with a defined precedence when two GPOs set the same thing; and a GPO's application can be **filtered** so it reaches only some of the objects in its scope. You do not need the full precedence rules at this level — you need to know that "linked to that OU" is the *start* of the answer to "does this apply?", not the end of it.

## 10. Policy With Teeth

Group Policy is not advisory. The training domain's password policy, real output:

```
PASSWORD POLICY (Default Domain Policy)
  Minimum length      : 12 characters
  Complexity required : Yes — 3 of 4 character classes
  Maximum age         : 90 days
  Password history    : last 5 remembered

ACCOUNT LOCKOUT POLICY
  Lockout threshold   : 5 failed attempts
  Observation window  : 15 minutes
  Lockout duration    : 30 minutes
```

And here is that policy refusing an administrator — real output from attempting to set a weak password:

```
Set-ADAccountPassword : password for 'dtamang' REJECTED by policy:
  ✗ too short — policy requires at least 12 characters (got 5)
  ✗ not complex enough — needs at least 3 of: uppercase, lowercase, digits, symbols

Run `policy` to review the requirements.
```

Nothing changed. The policy is enforced at the point the password is set, by the directory itself, against an account with administrative rights. That is what "GPO enforces security configuration" means concretely — and it is also why the lockout policy above explains Manisha Rai's locked account in §4: 14 failed attempts against a threshold of 5 is a control that fired, not a malfunction.

## 11. ACLs, Security Principals and Effective Access

Authorization in Windows runs on **security principals** and **permissions**.

A **security principal** is anything that can be granted access and can be identified in a security decision: a user, a group, a computer. Each has a unique **security identifier (SID)** — an identifier the system actually uses, distinct from the display name, which is why renaming a user does not change their access and why deleting-and-recreating an account *does*.

An **ACL** (Access Control List) is the list of permissions attached to a resource. It is made of **ACEs** (Access Control Entries), each pairing a security principal with a right.

The training domain's HR share, real output:

```
Share       : HR-Confidential
Path        : \\FS-01\HR-Confidential
Server      : FS-01
Description : Salary reviews, disciplinary records, contracts.
Permissions :
  · HR               WRITE
  · Domain Users     READ   ⚠ everyone in the domain
  · Domain Admins    FULL
```

Three ACEs, each naming a **group** rather than a person — which is the correct pattern from Lesson 1 §9. Now the chain that actually decides one person's access:

```
Alice  ──►  member of group  ──►  group appears in the resource's ACL  ──►  right
```

Worked against real output. Dipesh Tamang is an accountant with no HR role at all:

```
ACCESS GRANTED — 'dtamang' has READ on 'HR-Confidential' (\\FS-01\HR-Confidential).
  · via group 'Domain Users' → READ
⚠ AUDIT FINDING: this access comes from 'Domain Users' — EVERY account in the domain can read this confidential share. That violates least privilege.
```

Trace it: Dipesh is in `Domain Users` (every account is), `Domain Users` has READ on the share, therefore Dipesh has READ. Nobody granted Dipesh anything. Nobody intended this. The ACE was presumably added once to make something work, and its scope is *the entire organisation*.

Now the HR Manager, who is supposed to have access:

```
ACCESS GRANTED — 'lbasnet' has WRITE on 'HR-Confidential' (\\FS-01\HR-Confidential).
  · via group 'HR' → WRITE
  · via group 'Domain Users' → READ
⚠ AUDIT FINDING: this access comes from 'Domain Users' — EVERY account in the domain can read this confidential share. That violates least privilege.
```

Two paths, and the **most permissive one wins**: she is granted WRITE via `HR` and READ via `Domain Users`, and her effective access is WRITE. This is the general behaviour of allow permissions from multiple groups — they accumulate. (Windows also supports explicit *deny* entries, which take precedence over allows; they are a real feature and a well-known source of confusion, which is why good practice leans on granting the right things rather than denying the wrong ones.)

And the intern, whose result should make you sit up:

```
ACCESS GRANTED — 'intern01' has FULL on 'HR-Confidential' (\\FS-01\HR-Confidential).
  · via group 'Domain Users' → READ
  · via group 'Domain Admins' → FULL
⚠ AUDIT FINDING: this access comes from 'Domain Users' — EVERY account in the domain can read this confidential share. That violates least privilege.
```

An intern with **FULL** control of the HR share, via Domain Admins. Neither the share's ACL nor the intern's user object looks wrong on its own — the share grants Domain Admins full control, which is normal, and the account is a perfectly ordinary enabled user. The problem is the *membership*, two objects away from the resource. That is what "effective access" means, and it is why you compute it rather than eyeball it.

## 12. Forest, Tree, Domain, OU — and What Is Actually a Boundary

The hierarchy, from the top:

```
FOREST          the outermost container; the real security boundary
   │            (shares a schema and a global catalogue)
   ▼
TREE            one or more domains sharing a contiguous DNS namespace
   │            (corp.example, eu.corp.example)
   ▼
DOMAIN          administrative + security boundary; its own directory
   │            partition, its own DCs, its own policy and accounts
   ▼
OU              container for organisation, policy scope, delegation
   │
   ▼
OBJECTS         users, groups, computers
```

**This is an organisational and administrative hierarchy, not a folder tree.** A domain is not "a big folder"; it is a partition of the directory with its own authentication authority. An OU is not "a small domain"; it holds no authority at all.

Now put the six terms the module has used side by side, because they are not interchangeable and the differences are the point:

| Term | What it is | Is it a security boundary? |
|---|---|---|
| **Forest** | Outermost container; shared schema | **Yes** — treated as the ultimate boundary in AD security design |
| **Domain** | Directory partition with its own DCs, accounts and policy | **Yes**, at the administrative level — with the caveat below |
| **Trust** | A configured relationship letting one domain/forest recognise another's identities | It *crosses* boundaries by design |
| **OU** | Container for organisation, policy scope, delegation | **No** |
| **Group** | Collection of security principals | No — it is how access is *granted*, not a boundary |
| **ACL** | Permissions on a resource | No — it is the *decision*, made at the resource |

The caveat on domains, stated because a lot of older material gets it wrong: a domain is an administrative boundary, but for security-design purposes the **forest** is treated as the boundary that matters. That is why merging two organisations' forests is a much bigger decision than adding a domain to an existing one.

## 13. Trusts

A **trust** is a configured relationship that lets identities from one domain or forest be recognised in another security context.

The essential idea, and this is as far as a foundational module needs to go:

> A trust does not grant access. It makes an identity from elsewhere *recognisable* — after which, access still depends entirely on that identity's groups and the resource's ACL.

Properties worth knowing by name:

- **Direction** — a trust can be one-way or two-way. "A trusts B" is not automatically "B trusts A".
- **Transitivity** — some trusts extend along a chain (if A trusts B and B trusts C, A may effectively trust C); some do not.
- **Scope** — trusts exist within a forest (between its domains, automatically) and can be configured between separate forests.

Why they exist: mergers, acquisitions, partner access, and separating environments that must nonetheless interoperate. Why they matter to security: a trust widens the set of identities that can be authenticated in your context, so the security of what you trust becomes part of the security of *you*. Configuring one is an identity-architecture decision, not a networking one.

**This platform simulates a single domain, `YUSHA.LOCAL`.** There is no forest hierarchy, no second domain and no trust to inspect, so nothing in this section is quoted from the console — it is taught conceptually, and the offensive treatment of trusts belongs to the Red Team track, not here.

## 14. Security Principles for Active Directory

Not slogans — each one has a concrete meaning in the environment you have been reading.

**Least privilege.** Every identity gets the minimum access its role requires, and no more. The intern in Domain Admins is the textbook violation; the `Domain Users` ACE on the HR share is the subtler and more common one, because nobody ever decided to grant it to everyone.

**Group-based access.** Grant to groups, put people in groups. Individual ACEs make review impossible and survive role changes silently (Lesson 1, Exercise C).

**Separation of administrative roles.** Administrators should not do daily work — mail, browsing, documents — from an account that holds administrative rights. The usual pattern is separate accounts for separate privilege levels, so that compromising the everyday account does not hand over the domain.

**Strong authentication.** Enforce a real password policy (this domain's 12-character minimum with complexity is a reasonable floor), and add a second factor for privileged access. Note that the policy is only worth what its *enforcement* is — §10 showed the enforcement working.

**Controlled delegation.** OU-scoped delegation is the correct answer to "the help desk needs to reset passwords". Adding the help desk to Domain Admins is the incorrect answer to the same question, and it is depressingly common.

**Auditing.** Decide what security events are recorded, ensure the audit policy is actually applied, and make sure someone reads the result. Straight from the OWASP module's A09: a failure nobody can detect is a failure that lasts.

**Patch management.** Domain Controllers are the highest-value hosts in a Windows estate. Their patch state is not a routine IT metric.

**Secure configuration.** Baseline your GPOs, review them, and treat a weak setting as a domain-wide weakness — because a GPO applies its scope's configuration everywhere in that scope, consistently and repeatedly.

## 15. Common Misconceptions

**WRONG:** "Kerberos sends the user's password to every service."
**CORRECT:** Kerberos uses **tickets**. The password is used once, at logon, to obtain a TGT; each service receives a service ticket it validates without ever seeing the password.

**WRONG:** "The TGT is what gets you into the file server."
**CORRECT:** The TGT gets you *service tickets*. It is presented to the KDC, not to services. The service ticket is what the file server sees.

**WRONG:** "LDAP is the authentication protocol."
**CORRECT:** LDAP is a directory access protocol for querying and modifying directory data. Kerberos is the primary domain authentication protocol.

**WRONG:** "The Domain Controller decides whether I can read the HR share."
**CORRECT:** The DC authenticates you and vouches for your group memberships. The **resource** compares those groups to its own ACL and decides. Two decisions, two places.

**WRONG:** "Being authenticated means you can access the resource."
**CORRECT:** Authentication establishes identity; authorization determines access. This is the same distinction as the OWASP module's A01, expressed in Windows.

**WRONG:** "An OU is a security boundary."
**CORRECT:** OUs organise objects, scope policy and support delegation. The domain — and above it the forest — is where security boundaries live.

**WRONG:** "Group Policy is only cosmetic."
**CORRECT:** GPOs carry password policy, lockout policy, audit policy, firewall configuration, execution control and user rights assignment.

**WRONG:** "NTLM is dead."
**CORRECT:** It is legacy, weaker than Kerberos, and still encountered as a fallback. Reducing its use is a project; assuming its absence is a mistake.

## 16. Knowledge Check

1. What is Kerberos used for in an Active Directory domain?
2. What is a TGT, and what is it *not* used for?
3. What is a service ticket, and what does it carry beyond identity?
4. What is the KDC, and where does it run in an AD domain?
5. Why does a client obtain a service ticket instead of sending the user's password to each service?
6. What is LDAP used for?
7. How is LDAP different from Kerberos?
8. Where does NTLM still fit, and why is that a concern rather than a scandal?
9. What is Group Policy, and what is a GPO?
10. What is the relationship between a GPO and an OU?
11. Explain authentication versus authorization using the DC and a file server.
12. Why does least privilege matter specifically in Active Directory?

<details>
<summary>Answers</summary>

1. It is the primary **authentication** protocol: it proves the identity of users and services to one another, using time-limited tickets issued by a trusted third party, so that credentials do not have to be presented to every service.
2. A **Ticket Granting Ticket** is proof that the KDC authenticated you, obtained once at logon and time-limited. It is **not** presented to services — its only purpose is to let you request service tickets from the KDC without re-authenticating.
3. A ticket for one specific service, proving the KDC vouches for you. Beyond identity it carries your **group memberships**, which is what lets the service make its authorization decision immediately without querying the directory.
4. The **Key Distribution Center** — conceptually the Authentication Service (issues TGTs) plus the Ticket Granting Service (issues service tickets). In an AD domain it runs **on the Domain Controllers**, not on a separate host.
5. Because sending the password would expose it to every service, require every service to be able to verify credentials, and put the secret on the network repeatedly. Tickets mean the service never sees the password, validates using key material shared with the KDC, and the user's secret is used only once at logon.
6. **Reading and modifying directory information** — searching for objects and retrieving or changing their attributes.
7. Different jobs. LDAP is directory *access* ("which users are in Engineering?"); Kerberos is *authentication* ("is this really who they claim to be?"). Both talk to Domain Controllers. LDAP does have its own bind step, which authenticates a client to the LDAP service for querying — that is not the domain's logon mechanism.
8. As a **fallback and compatibility** mechanism, where Kerberos's requirements are not met — connecting by IP address, non-domain-joined machines, applications that never implemented Kerberos. It is a concern because its security properties are weaker than Kerberos's and its material can in some conditions be captured and abused. It is not a scandal because compatibility is a genuine requirement; the correct response is to monitor where it is used and reduce that deliberately.
9. **Group Policy** is the mechanism for delivering configuration to machines and users across a domain, applied at startup/logon and refreshed periodically. A **GPO** is a named collection of those settings, split into Computer Configuration and User Configuration.
10. They are different kinds of thing: an OU is a **container** for objects; a GPO is a **collection of settings**. A GPO is *linked* to a scope — a site, the domain, or an OU. One GPO can be linked to several places, and one OU can have several GPOs linked to it. Where an object sits therefore determines which policy reaches it.
11. The **Domain Controller** authenticates the user (Kerberos, via the KDC) and issues a ticket carrying their identity and groups. The **file server** then compares those groups to its own ACL and decides what, if anything, they may do. Identity is proven in one place; access is decided in another.
12. Because AD centralizes authorization, so an excess grant is rarely local — a group membership or an ACE can hand access to a whole organisation at once (the `Domain Users` entry on the HR share) or hand the entire domain to one account (the intern in Domain Admins). Centralization makes over-privilege cheap to create and expensive to discover.
</details>

## 17. Where This Goes Next

**Hands-on Practice** puts every mechanism in this lesson in front of you in the real simulated **YUSHA.LOCAL** domain: enumerate the directory, derive a user's effective access from their group memberships, read the Group Policy that governs the domain, watch Kerberos succeed and fail, and write findings as evidence — observation, evidence, interpretation, security impact, recommendation, confidence.
