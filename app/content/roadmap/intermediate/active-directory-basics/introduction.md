# Introduction to Active Directory

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain the problem centralized identity solves, before naming a single Microsoft product
- keep **Active Directory**, **AD DS** and **Domain Controller** as three distinct things
- describe a **domain** as an administrative and security boundary
- say what a Domain Controller actually *does* — six jobs, not one
- describe **users**, **groups**, **computers** and **organizational units** as directory objects with attributes
- explain why access is granted through **groups** rather than to individuals
- state precisely why an **OU is not a security boundary**
- explain why a domain-joined computer has an identity of its own
- describe, conceptually, what happens when a machine joins a domain
- explain why Active Directory depends heavily on **DNS** — and why that does not make AD the same thing as DNS

## 2. Why This Matters

Start with the problem, because the product only makes sense as an answer to it.

A company has 500 Windows computers and 300 employees. Without any central directory, every one of those 500 machines keeps its **own** list of accounts. That means:

- A new hire needs an account created on every machine they might use.
- Someone leaving needs 500 accounts disabled — and the one that gets missed is the one that matters.
- A password change is a password change *per machine*.
- "Who can read the HR folder?" has no single answer; it has 500 partial answers.
- A security setting — password minimum length, say — has to be set 500 times, identically, forever.

Now add a **domain**. One directory holds the identities. One set of servers answers "who is this?" One policy mechanism pushes the same configuration everywhere. A leaver is disabled **once**, and every machine in the organisation stops trusting them.

That is what Active Directory is *for*. Everything technical in these three lessons is machinery in service of that: **centralized identity, centralized authorization, centralized policy.**

And that centralization is exactly why it matters to security. The same property that makes 500 machines manageable from one place makes them compromisable from one place. An identity system that everything trusts is an identity system worth attacking — which is why the modules after this one (Windows Privilege Escalation, and the Red Team track's Active Directory Attacks) exist, and why they come *after* you understand how the system is supposed to work.

## 3. Authorization and Scope

Everything you run in this module happens inside YushaCyber's simulated **YUSHA.LOCAL** training domain — a fictional company's directory that exists entirely as Python data structures inside this platform. There is no real Windows, no real directory service, and no network connection to anything.

**Nothing in this module may be repeated against a domain you do not own or have written permission to test.** Enterprise directories are production identity infrastructure; querying one you have not been authorized to query is not a neutral act, even when nothing changes.

This module is also deliberately *not* an attack module. It teaches what the system is, how it authenticates, how it authorizes, and what a weak configuration looks like from an administrator's chair. Offensive technique against AD is later, gated content — and it will make far more sense once you can already read a directory.

## 4. Three Words That Are Not Synonyms

People use these three interchangeably and then confuse themselves. Separate them now.

| Term | What it is |
|---|---|
| **Active Directory** | Microsoft's umbrella name for a family of directory and identity services. Several distinct services carry the name |
| **Active Directory Domain Services (AD DS)** | The specific *service* — the one that stores the directory, authenticates domain identities and enforces domain structure. When people say "Active Directory" in an on-premises context, this is almost always what they actually mean |
| **Domain Controller (DC)** | A *server* running AD DS. It is a machine, not a service and not a directory. A domain normally has several |

The relationship, stated as a sentence you can check yourself against:

> **AD DS is the service. A Domain Controller is a server that runs it. Active Directory is the family name.**

Two consequences worth holding on to:

- "We're moving Active Directory to a new server" means moving the *role*, not the *directory* — the directory data is replicated between DCs and does not belong to any one of them.
- Other services also carry the Active Directory name — certificate services, federation services, a lightweight directory service, and Microsoft's cloud identity service. They are related products, not the same product. This module is about **AD DS** specifically.

**A directory service**, generally, is a database optimised for a particular shape of work: many reads, few writes, hierarchical organisation, and objects described by attributes. It is not a general-purpose relational database and it is not, as the common misconception has it, "a list of usernames and passwords."

## 5. The Domain

A **domain** is a group of objects — users, computers, groups — that share a common directory, a common authentication authority, and a common set of policies.

Two ways to read that, both true and both useful:

**As an administrative boundary.** Everything in the domain is administered together. One place to create an account, one place to disable one, one place to define a password policy.

**As a security boundary.** The domain decides who its identities are and what they may do inside it. A machine that is joined to the domain *trusts* the domain's authentication authority — it will accept "the DC says this is Manisha Rai" as proof of identity. A machine that is not joined does not.

Domains are named in DNS style. This module's training domain is:

```
YUSHA.LOCAL
```

with the older, flat **NetBIOS** name `YUSHA` — which is why you will see accounts written both ways: `YUSHA\skhadka` and `skhadka@YUSHA.LOCAL`. Both name the same identity.

Use fictional domain names when you write examples, as this module does throughout. `corp.example`, `contoso.com` and `.local`-style training names are conventional for exactly that reason.

## 6. What a Domain Controller Actually Does

The lazy definition — "the server where the passwords are" — is wrong in a way that will cost you later, because it makes the DC sound passive. It is not passive. It is the thing every other machine in the domain is asking questions of, constantly.

A Domain Controller:

1. **Hosts AD DS** — it holds a replicated copy of the directory database and keeps it in sync with the other DCs.
2. **Authenticates domain identities** — it is the authority that answers "is this really who they claim to be?"
3. **Runs the KDC** — the Key Distribution Center, the Kerberos service that issues the tickets Lesson 2 takes apart. In an AD domain the KDC runs *on the DCs*; it is not a separate box.
4. **Serves directory queries** — applications and administrators ask it for objects and attributes (this is where LDAP comes in, also Lesson 2).
5. **Stores and distributes policy** — Group Policy Objects live in the directory and in a share on the DCs, and clients fetch them from there.
6. **Participates in domain security decisions** — group membership, account state, lockout, password policy: the DC is the authority on all of it.

This platform's simulator names that role explicitly. Inspecting the training domain's controller returns:

```
Computer    : DC-01
OS          : Windows Server 2022
IP address  : 10.20.0.10
OU          : Domain Controllers
Role        : Domain Controller — runs AD DS, DNS and the KDC
Description : Primary domain controller for YUSHA.LOCAL.
```

Note what that `Role` line packs in: directory service, name service, and authentication service, on one machine. That co-location is normal in real deployments and it is a large part of why a Domain Controller is the highest-value host in a Windows network.

> **Domain ≠ Domain Controller.** The domain is the logical grouping and its trust relationships. A Domain Controller is a server that provides services *to* that domain. Losing one DC does not destroy the domain; losing the domain's integrity is a far worse day.

## 7. Directory Objects

Everything in the directory is an **object**: a thing of a defined *class*, carrying *attributes*, sitting in a *container*, with a security identity.

| Object class | Represents | Example attributes |
|---|---|---|
| **User** | A person's (or a service's) identity | account name, display name, title, group memberships, enabled state, last logon |
| **Group** | A named collection of security principals | name, description, members, scope |
| **Computer** | A domain-joined machine's identity | name, operating system, the OU it sits in |
| **Organizational Unit** | A container for organising other objects | name, description, the objects it contains, the policies linked to it |

Two more you will meet in real environments, mentioned so the words are not new later: **contacts** (address-book entries for people with no logon — no credentials, not security principals) and **managed service accounts** (accounts for services whose passwords the directory manages automatically, so nobody has to know them).

The word that matters most here is **attribute**. A user is not a row with a password in it; it is an object with dozens of attributes, most of which have nothing to do with authentication and many of which are readable by ordinary domain users. That is a normal, designed property of a directory — and it is why "what can I learn just by reading the directory?" is a real security question.

## 8. Users

A user object is an **identity**, and it carries at least:

- an account name (the `sAMAccountName`, the short login name)
- a display name and descriptive attributes — title, department, description
- credential material, stored so it can be verified rather than read back
- **group memberships**, which is where its access actually comes from
- **account state** — enabled or disabled, locked out or not, when it last logged on

Here is a real user object from the training domain, as the console renders it:

```
User          : Sujal Khadka
sAMAccountName: skhadka
Title         : IT Manager
OU            : IT
Status        : Enabled
Failed logons : 0
Last logon    : today
Member of     : IT Support, Help Desk, Domain Users
Description   : Leads the IT team.
```

Read the two lines that carry the security meaning. **`Status`** tells you whether this identity can be used at all. **`Member of`** tells you what it can reach — and notice that the object itself lists no permissions whatsoever. Permissions are not stored on the user.

Account state is not a footnote. Compare two other real accounts in the same directory:

```
User          : Manisha Rai
sAMAccountName: mrai
Title         : HR Officer
OU            : HR
Status        : Enabled, LOCKED OUT
Failed logons : 14
Last logon    : 2 day(s) ago
Member of     : HR, Domain Users
Description   : SECURITY NOTE: account locked after repeated failed logins from an unknown workstation.
```

```
User          : Kabita Shrestha
sAMAccountName: kshrestha
Title         : Financial Analyst
OU            : Finance
Status        : Enabled
Failed logons : 0
Last logon    : 210 day(s) ago  ⚠ INACTIVE
Member of     : Finance, Domain Users
Description   : On extended leave since last year.
```

One is **locked out** — a control fired, and 14 failed attempts is a fact worth investigating rather than simply clearing. The other is **enabled and unused for 210 days** — nothing has fired, and that is precisely the problem: an account nobody watches, that still authenticates, is exactly what an attacker would prefer to use. Neither of those is visible from a password. Both are visible from the directory.

**Never put real credentials in a lesson, a ticket, or a report.** Every account name in this module is fictional and belongs to a simulator; no password for any of them exists anywhere.

## 9. Groups — and Why Access Goes Through Them

This is the single most important structural idea in AD authorization.

The naive model:

```
User ──────────────────────────► Permission
```

The model AD actually uses, and the one every competent administrator maintains:

```
User ────► Group ────► Permission
```

Why the extra step is worth it:

| | User → Permission | User → Group → Permission |
|---|---|---|
| New hire | Grant every permission individually, hoping to match a colleague | Add to the right groups; access follows |
| Leaver | Hunt every resource they were granted | Remove from groups; access stops |
| Role change | Find and revoke old, find and grant new | Change group membership |
| "Who can read this?" | Enumerate every user | Read one ACL and its groups |
| Auditing | Effectively impossible at scale | Tractable |

Groups are also *named*, and a good name is documentation: `Finance` says why the access exists. A pile of individual grants says nothing about intent, which means nobody can later tell whether a particular grant is still justified.

Two group properties worth knowing now:

**Built-in vs. custom.** Some groups ship with the domain and carry meaning the operating system itself understands — **Domain Users** (every account) and **Domain Admins** (full administrative control) are the two you must recognise. Others are created by the organisation to model its own roles: `HR`, `Finance`, `Help Desk`, `IT Support` in this training domain.

**Groups nest.** A group can contain another group, so effective membership is not always what one screen shows. Real environments accumulate surprising chains this way, and "why does this person have access?" often has a two-hop answer.

The training domain's group list, from the real console:

```
GROUP                    KIND      MEMBERS
──────────────────────────────────────────────
Domain Admins            built-in  2  ⚠
Domain Users             built-in  10
Finance                  custom    2
Help Desk                custom    2
HR                       custom    2
IT Support               custom    2

Use `get-group <name>` or `members <name>` for membership.
```

Ten users, and two of them are in **Domain Admins**. That ratio is the kind of thing you notice on a first pass and confirm on a second — Lesson 3 confirms it.

## 10. Organizational Units

An **Organizational Unit** is a container. It exists to organise objects inside the domain, and it does three jobs:

1. **Organisation** — grouping objects so a human can navigate them (`IT`, `HR`, `Finance`, `Workstations`, `Service Accounts`).
2. **Policy scope** — a Group Policy Object can be linked to an OU, so the settings apply to the objects in it. Lesson 2 takes this apart properly.
3. **Delegation** — administrative rights over the objects in an OU can be handed to someone without making them an administrator of the whole domain. This is genuinely important and genuinely easy to get wrong.

The training domain's OUs, real output:

```
ORGANIZATIONAL UNIT        USERS  COMPUTERS
─────────────────────────────────────────────
Disabled Accounts              0          0
Domain Controllers             0          1
Finance                        2          0
HR                             2          0
Interns                        1          0
IT                             4          0
Servers                        0          1
Service Accounts               1          0
Workstations                   0          3
Use `move <sam> <ou>` to move a user between OUs.
```

You can read the organisation's intent straight off that: people are filed by department, machines by role, and there is a `Disabled Accounts` quarantine OU for leavers. `Domain Controllers` is its own OU because DCs get policy that nothing else should.

Now the correction this section exists for.

> **WRONG:** "An OU is a security boundary."
> **CORRECT:** An OU organises objects, scopes policy and supports delegation. It is **not** an inherent security boundary.

Being in a different OU does not, by itself, stop a user reaching a resource. Authorization is decided by **security principals and permissions** — who you are, which groups you are in, and what the resource's ACL says — not by which container your object happens to sit in. Two users in two different OUs with identical group memberships have identical access.

The domain (and above it the forest) is where the real security boundaries live. An OU is an organisational convenience with policy and delegation attached.

## 11. Computer Accounts

A domain-joined computer has its **own** object in the directory, with its own name, its own credential material, and its own identity in the domain.

This surprises people, so it is worth stating plainly: **a computer account is not "another user account."** It represents a *machine*, and the machine uses it to prove to the domain that it is the machine it claims to be — a mutual relationship, established when the machine joins and maintained automatically afterwards (the machine changes its own password on a schedule; no human ever types it).

Why it matters:

- It is what lets a machine be trusted by the domain at all, before any human logs in.
- It is what lets **computer-scoped policy** apply to the machine itself rather than to whoever is sitting at it.
- It means machines are objects you can inventory, organise into OUs, and reason about — and that a stale computer account is as much a loose end as a stale user account.

Real output for the training domain's machines:

```
NAME     OS                    IP           ROLE
────────────────────────────────────────────────────
DC-01    Windows Server 2022   10.20.0.10   DOMAIN CONTROLLER
FS-01    Windows Server 2022   10.20.0.20   member
WS-101   Windows 11            10.20.1.101  member
WS-102   Windows 11            10.20.1.102  member
WS-103   Windows 10            10.20.1.103  member
```

One controller, one file server, three workstations — and the operating system version is right there, which (as the OWASP module's A06 material would have you note) is a starting question about patch level, not an answer.

## 12. Joining a Domain

What follows is the **conceptual** sequence. It is deliberately not presented as protocol-level exactness — the real join involves more steps, more protocols and more failure modes than a foundational lesson needs. Treat it as the shape of the thing.

```
A Windows machine is told: "join the domain corp.example"
        ↓
DISCOVERY — it uses DNS to find out which servers offer domain
            services for that domain name
        ↓
CONTACT — it reaches a Domain Controller
        ↓
AUTHORIZATION — an account with permission to join machines must
                authorize the operation; not just anyone may add a
                computer to a domain
        ↓
COMPUTER ACCOUNT — an object for this machine is created in (or
                   matched to) the directory
        ↓
TRUST ESTABLISHED — machine and domain now share credential material;
                    the machine can authenticate as itself
        ↓
POLICY — at startup and periodically thereafter, the machine fetches
         and applies the policy that targets it
        ↓
USERS — a domain user can now log on at this machine, and the machine
        will ask the domain to authenticate them
```

Two things to take from that sequence rather than memorise:

**Joining is a privileged operation.** If anyone could add a machine to your domain, anyone could introduce a machine your domain trusts.

**Discovery comes first.** Before any of the rest can happen, the machine has to *find* the domain — which is the subject of the next section, and the single most common cause of "Active Directory is broken" turning out to be something else entirely.

## 13. DNS and Active Directory

This section matters more than its length suggests. In practice, a very large share of AD problems are DNS problems wearing a costume.

**Computer Networking** taught you what DNS is: the system that resolves names to addresses, and more generally answers questions about a name by returning records. You met `A` records (name → address), `NS`, `MX`, and the query/response flow through a resolver.

AD uses DNS for something slightly different from "look up an address". It uses it for **service location**. When a machine needs a Domain Controller for `corp.example`, it does not have one configured by hand; it *asks DNS which servers offer that service for that domain*, using a record type designed for the purpose (an `SRV` record, which names a service, a protocol, a host and a port rather than just an address).

The consequence is the important part:

```
A machine needs to authenticate a user
        ↓
It must first FIND a Domain Controller
        ↓
It asks DNS
        ↓
If DNS answers correctly → it contacts a DC → authentication proceeds
If DNS answers wrongly, or not at all → nothing else can happen
```

That is why:

- Domain Controllers very commonly run DNS themselves (this training domain's `DC-01` does — see §6's `Role` line).
- Domain members are normally configured to use the domain's DNS servers, not a public resolver. A workstation pointed at a public DNS server can browse the internet perfectly and still fail to log in, because the public resolver knows nothing about `corp.example`'s internal service records.
- "I can ping the DC by IP but the domain won't work" is a DNS story almost every time.

Now the correction, because the dependency invites the wrong conclusion:

> **WRONG:** "Active Directory is DNS."
> **CORRECT:** Active Directory *depends* on DNS to locate its services. They are two different systems with two different jobs. DNS answers "where is the service?"; AD DS answers "who is this identity, and what may it do?"

You can have DNS with no Active Directory anywhere — the public internet is exactly that. You cannot usefully have AD without DNS, which is a dependency, not an identity.

**Illustrative example — not captured output.** This platform's terminal has a real DNS simulator (Computer Networking's `nslookup`), but it does not model AD service records, so there is nothing real to quote here. Conceptually, the question a joining machine asks looks like *"which hosts provide the Kerberos service for `corp.example`, over TCP?"*, and the answer names one or more Domain Controllers and the port to reach them on. The shape — *a query about a service, answered with hosts* — is the part to remember.

## 14. The Whole Chain

Everything above, in one sequence:

```
Windows devices
      ↓  joined to, and trusting
Domain                       (administrative + security boundary)
      ↓  whose directory is provided by
Active Directory Domain Services
      ↓  running on
Domain Controllers           (found via DNS; also run the KDC)
      ↓  which hold
Users / Groups / Computers / OUs      (objects with attributes)
      ↓  used for
Authentication               ("who is this?" — Kerberos, Lesson 2)
      ↓  which feeds
Authorization                ("what may they do?" — groups + ACLs)
      ↓  alongside
Group Policy                 (configuration pushed to objects)
      ↓  governing access to
Resources                    (shares, servers, applications)
      ↓  bounded by
Security boundaries          (domain, forest, trust — not OU)
```

Read it downward and it is how the system works. Read it upward and it is how you investigate one: a resource is reached by an identity, whose access came from a group, held in a directory, served by a controller, inside a domain the machine trusts.

## 15. Common Misconceptions

**WRONG:** "Active Directory is just a database of usernames and passwords."
**CORRECT:** AD DS is a directory service holding objects of many classes, each with many attributes, plus the relationships (group membership, containment, policy links) and security information that connect them. Credentials are a small part of it.

**WRONG:** "Domain Controller = Active Directory."
**CORRECT:** A Domain Controller is a *server running AD DS* and providing domain services. The directory is replicated across DCs and belongs to none of them individually.

**WRONG:** "An OU is a security boundary."
**CORRECT:** OUs organise objects, scope Group Policy and enable delegation. Authorization is decided by security principals and permissions, not by container membership.

**WRONG:** "A computer account is just another user."
**CORRECT:** It represents a machine identity, maintained automatically by the machine, and it is what allows computer-scoped policy and machine authentication independent of any logged-on user.

**WRONG:** "Active Directory is DNS."
**CORRECT:** AD depends on DNS for service location. Two systems, two jobs; the dependency is real and one-directional.

**WRONG:** "Groups are just a convenience."
**CORRECT:** Groups are the mechanism authorization actually runs on. In a well-run domain, essentially all access is granted to groups, which is what makes joining, leaving and role changes tractable — and what makes auditing possible at all.

## 16. Exercises

Reasoning questions. Everything you need is above; the console work starts in Lesson 3.

**Exercise A — The 500 machines.**
A company with 500 standalone Windows machines wants to fire an employee today and be confident that by tomorrow that person cannot log on anywhere. Describe what has to happen without a domain, and what happens with one. Then name the *security* difference, not just the effort difference.

<details>
<summary>Discussion</summary>

Without a domain: every machine that holds a local account for that person needs that account disabled, individually. The effort is 500 units of work; the *security* problem is that you cannot verify you finished. There is no authoritative list of where accounts exist, so "did we get them all?" is unanswerable — and one missed machine is a working credential.

With a domain: the account is disabled once, in the directory. Every machine that authenticates that identity asks a Domain Controller, and the DC now refuses. The security difference is **verifiability**: there is one authoritative answer to "can this person log on?", and you can check it.

Worth noting the flip side, which the module returns to: the same centralization means compromise of the directory is compromise of everything that trusts it.
</details>

**Exercise B — Reading a user object.**
Look again at the `kshrestha` object in §8. Nothing about it is flagged as broken — the account is enabled, unlocked, with zero failed logons. Why might a security-minded administrator still put it at the top of a review list?

<details>
<summary>Discussion</summary>

Because `Last logon : 210 day(s) ago` describes an identity that still works and that **nobody is watching**. The account authenticates, carries the `Finance` group's access, and its owner is not using it — so if it were used, no legitimate user would notice the anomaly, and no control has fired to draw attention to it.

The general principle: an enabled account that is not in use is access with no oversight attached. The usual handling is to disable rather than delete (deletion loses the object's history and its security identifier), move it to a quarantine OU, and confirm with the owner's manager before doing anything irreversible.

Note also what you *cannot* conclude: 210 days of inactivity is not evidence of compromise or of wrongdoing. It is evidence of an unmonitored credential, which is a risk, not an incident.
</details>

**Exercise C — Groups versus grants.**
An administrator, in a hurry, grants Dipesh Tamang read access to the Finance share directly, rather than adding him to the `Finance` group. Everything works. Name three things that are now worse, and say when each one bites.

<details>
<summary>Discussion</summary>

1. **Auditing.** "Who can read Finance-Reports?" no longer has a group-shaped answer; the ACL now has an individual on it, which means every future review has to reason about that one entry separately. Bites at the next access review.
2. **Leaving and role changes.** Removing Dipesh from the `Finance` group would no longer remove this access, because it was never granted through the group. Bites on the day he changes role — silently, which is the dangerous part.
3. **Intent.** The grant records *that* he has access, not *why*. `Finance` says "because he works in Finance". A direct ACE says nothing, so nobody can later judge whether it is still justified. Bites at every review, forever.

The general rule: grant to groups, put people in groups. Individual ACEs are how ACLs rot.
</details>

**Exercise D — Where does it break first?**
A newly-built workstation is joined to `corp.example` successfully. The next morning nobody can log on to it, though it has network connectivity and can reach the internet. Using §13, name the first thing you would check and why.

<details>
<summary>Discussion</summary>

Its DNS configuration. Internet connectivity proves the machine has a working network path and *some* working resolver — it does not prove it is using the **domain's** resolver. A machine pointed at a public DNS server can browse fine and still be unable to locate a Domain Controller, because a public resolver has no records for the internal domain's services.

The reasoning chain: logon requires authentication → authentication requires reaching a DC → reaching a DC requires *finding* one → finding one requires DNS answering questions about `corp.example`. The first link that can fail while everything else looks healthy is the DNS one.

What you should *not* conclude first: "Active Directory is down." One machine failing while others work is evidence about that machine, not about the directory.
</details>

## 17. Knowledge Check

1. What is Active Directory, and what does AD DS specifically provide?
2. What is a Domain Controller, and how is it different from the domain?
3. What is a domain, read as a boundary?
4. Name four things a Domain Controller does beyond storing credentials.
5. What is a user object, and where does its *access* actually come from?
6. Why are groups important? Give the reason that survives at 300 users.
7. What is an Organizational Unit, and what three jobs does it do?
8. Why is an OU not a security boundary?
9. Why does Active Directory depend heavily on DNS — and why is AD not DNS?

<details>
<summary>Answers</summary>

1. **Active Directory** is Microsoft's family name for several directory and identity services. **AD DS** is the specific service that stores the directory, authenticates domain identities, and enforces domain structure and policy — it is what people almost always mean by "Active Directory" on-premises.
2. A **Domain Controller** is a *server running AD DS*. The **domain** is the logical grouping of objects that share a directory, an authentication authority and a policy set. The DC provides services to the domain; it is not the domain, and the directory is replicated across DCs rather than owned by one.
3. Both an **administrative boundary** (everything in it is managed together — one place to create, disable, and set policy) and a **security boundary** (it decides who its identities are and what they may do; joined machines trust its authentication authority).
4. Any four of: runs the KDC and issues Kerberos tickets; serves directory queries; stores and distributes Group Policy; holds and replicates the directory database; decides group membership, account state and lockout; commonly also provides DNS.
5. A user object is an **identity** made of attributes — account name, descriptive fields, credential material, account state, and group memberships. Its access comes from its **group memberships** combined with resources' ACLs. The user object itself stores no permissions.
6. Because they make authorization manageable and auditable: joining, leaving and role changes become membership changes rather than resource-by-resource hunts, and "who can read this?" has an answer you can actually compute. At 300 users, individual grants are not merely tedious — they are unverifiable.
7. A container for objects. It provides **organisation**, **policy scope** (a GPO can be linked to it), and **delegation** (administrative rights over its contents can be granted without domain-wide admin rights).
8. Because authorization is decided by **security principals and permissions** — identity, group membership, and the resource's ACL — not by which container an object sits in. Two users in different OUs with the same group memberships have the same access. OUs scope *policy and delegation*; the domain and forest are where the security boundaries are.
9. AD uses DNS for **service location** — a machine must find a Domain Controller before it can authenticate anything, and it does that by querying DNS for the domain's service records. AD is not DNS because they answer different questions: DNS answers "where is this service?", AD DS answers "who is this identity and what may it do?". DNS exists happily without AD; AD cannot function without working DNS.
</details>

## 18. Where This Goes Next

**Core Concepts** takes apart the mechanisms: authentication versus authorization in a domain, **Kerberos** and its ticket model (with the real ticket flow from this platform's simulator), the **KDC**, where **NTLM** still fits and why, what **LDAP** is actually for and how it differs from Kerberos, **Group Policy** and GPOs, **ACLs** and effective access, and the forest/domain/OU hierarchy with its real security boundaries.

**Hands-on Practice** puts you in front of the real simulated **YUSHA.LOCAL** domain to investigate it: enumerate the directory, trace how a user's access is actually derived, read a Group Policy, watch a Kerberos authentication succeed and fail, and write up findings as evidence rather than as opinions.

Beyond this module, **Windows Privilege Escalation** and the Red Team track's **Active Directory Attacks** are where the offensive side lives — and both assume exactly what these three lessons build: that you can read a directory and explain what you are looking at.
