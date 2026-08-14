# Hands-on Practice: An Active Directory Investigation

## 1. Authorization Comes First

Everything below runs against **YUSHA.LOCAL**, a fictional company's directory that exists entirely as Python data structures inside YushaCyber. There is no real Windows, no real directory service, and no network connection to anything. You are explicitly authorized to investigate it.

**Nothing in this lesson may be repeated against a domain you do not own or have written permission to test.** An enterprise directory is production identity infrastructure. Enumerating one you have not been authorized to enumerate is not a neutral act just because nothing changes — reading who works where, who is privileged, and which accounts are dormant *is* the reconnaissance phase of an attack, and it is treated that way.

**What this lesson does not teach**, deliberately: credential attacks, ticket abuse, privilege escalation, or any technique for compromising a domain. This is an administrator's and an assessor's view — read the directory, work out what it actually permits, and write down what should change. The offensive material has its own modules later, and it will be far more useful to you after this one.

Every exercise below is **read-only investigation**. Nothing you are asked to run changes the directory.

## 2. The Environment

The console connects you to the training domain as a simulated administrator. This is the real welcome screen:

```
╔══════════════════════════════════════════════════╗
║   ACTIVE DIRECTORY ADMINISTRATION — SIMULATED     ║
╚══════════════════════════════════════════════════╝

Connected to domain: YUSHA.LOCAL  (functional level 2016)
Primary training domain of Yusha Corp — a small company with IT, HR and Finance departments.

  10 users · 6 groups · 9 OUs · 5 computers · 3 shares

Click objects in the explorer, or type `help` for commands.
```

Ten users, six groups, nine OUs, five computers, three shares. Small enough to hold in your head — which is the point, because the reasoning has to be learned somewhere it can be checked, and it does not change at ten thousand users.

The commands available, real output from `help`:

```
AD ADMINISTRATION CONSOLE — available commands

 DIRECTORY
  get-users                     list every user account
  get-user <sam>                one user's full properties
  get-groups                    list security groups
  get-group <name>              one group + its members
  members <group>               shorthand for get-group
  get-ous                       organizational units
  get-computers                 domain-joined computers
  get-computer <name>           one computer's properties
  get-shares                    shared folders
  get-share <name>              one share + its permissions

 ACCOUNT MANAGEMENT
  reset-password <sam> <new>    reset a password (policy enforced)
  unlock <sam>                  clear an account lockout
  enable <sam> / disable <sam>  activate / deactivate an account
  move <sam> <ou>               move a user to another OU

 GROUP MANAGEMENT
  add-member <group> <sam>      add a user to a group
  remove-member <group> <sam>   remove a user from a group

 SECURITY
  access <sam> <share>          test a user's access to a share
  grant-access <share> <group> <right>    right: read|write|full
  revoke-access <share> <group>
  kerberos <sam> [service]      visualize the Kerberos ticket flow
  policy                        password + lockout policy
  gpos                          list Group Policy Objects

 OTHER
  whoami · hostname · clear · exit · help

Names with spaces need quotes: members "Domain Admins".
```

**The exercises below use only the DIRECTORY and SECURITY commands.** The account- and group-management verbs exist and the later labs in this track use them; this lesson does not, because the skill being built here is *reading* a directory correctly before changing anything in it.

## 3. The Investigation Workflow

```
AUTHORIZED ENVIRONMENT
        ↓
OBSERVATION      what did the environment actually show?
        ↓
EVIDENCE         which exact output supports that?
        ↓
INTERPRETATION   what does that evidence mean, stated as a reading
                 rather than a verdict?
        ↓
SECURITY IMPACT  why does it matter — what does it let someone do?
        ↓
RECOMMENDATION   what control would change it?
        ↓
CONFIDENCE       how sure are you, and what would raise it?
```

The same discipline the Wireshark, Burp Suite and OWASP modules installed, applied to directory objects instead of packets and requests. The step people skip is the one between EVIDENCE and INTERPRETATION — deciding what the output *means* before deciding whether it is a *problem*.

## 4. Exercise 1 — The Domain and Its Controller

**Objective:** establish what this domain is and which machine holds its authority.

**Why start here:** every later finding is relative to this. "An intern is in Domain Admins" only means something once you know what this domain contains.

```
PS YUSHA\admin> whoami
yusha\admin (simulated administrator session)
```

```
PS YUSHA\admin> hostname
DC-01
```

```
PS YUSHA\admin> get-computers
NAME     OS                    IP           ROLE
────────────────────────────────────────────────────
DC-01    Windows Server 2022   10.20.0.10   DOMAIN CONTROLLER
FS-01    Windows Server 2022   10.20.0.20   member
WS-101   Windows 11            10.20.1.101  member
WS-102   Windows 11            10.20.1.102  member
WS-103   Windows 10            10.20.1.103  member
```

```
PS YUSHA\admin> get-computer DC-01
Computer    : DC-01
OS          : Windows Server 2022
IP address  : 10.20.0.10
OU          : Domain Controllers
Role        : Domain Controller — runs AD DS, DNS and the KDC
Description : Primary domain controller for YUSHA.LOCAL.
```

### Required reasoning

**OBSERVATION:** the domain is `YUSHA.LOCAL` at functional level 2016, with five domain-joined computers. Exactly one, `DC-01`, is marked `DOMAIN CONTROLLER`; it sits in the `Domain Controllers` OU and is described as running AD DS, DNS and the KDC.

**EVIDENCE:** the `get-computers` role column and the `get-computer DC-01` Role line.

**INTERPRETATION:** `DC-01` is the domain's authentication authority, its directory service and its name service simultaneously. `FS-01` is a member server hosting the shares. The three workstations are ordinary members. Three of the five machines are servers, which is a high ratio and consistent with a small company.

**SECURITY IMPACT:** compromise of `DC-01` is compromise of the domain — the identity of every user, the tickets that authenticate them, and the policy that configures every machine. Its patch state and administrative access are not routine IT concerns.

**RECOMMENDATION:** treat `DC-01` as a tier-0 asset — restricted administrative access, restricted logon rights, prioritised patching, and monitored. Note also that `WS-103` runs Windows 10 while the others run Windows 11; that is a lifecycle question worth an owner, not a finding on its own.

**CONFIDENCE:** high for the facts; the tiering recommendation is standard practice rather than something this output proves.

### What you cannot conclude

- That there is only one Domain Controller **in reality**. This is a training domain with one; production domains normally have several for redundancy, and a single-DC production domain would itself be a finding.
- Anything about patch level from the OS name alone. `Windows Server 2022` is a product, not a build.

## 5. Exercise 2 — The User Population

**Objective:** find the accounts whose *state* is worth a second look.

```
PS YUSHA\admin> get-users
SAM             DISPLAY NAME             OU            STATUS      LAST LOGON
──────────────────────────────────────────────────────────────────────────────
administrator   Administrator            IT            ok          today
dtamang         Dipesh Tamang            Finance       ok          3d ago
intern01        Bikash Magar (Intern)    Interns       ok          today
kshrestha       Kabita Shrestha          Finance       ok          210d ago ⚠
lbasnet         Laxmi Basnet             HR            ok          1d ago
mrai            Manisha Rai              HR            LOCKED      2d ago
pgurung         Prakash Gurung           IT            ok          today
rthapa          Rojina Thapa             IT            ok          1d ago
skhadka         Sujal Khadka             IT            ok          today
svc-backup      Backup Service           Service Accounts ok          today

10 user(s). Use `get-user <sam>` for details.
```

Two rows stand out on the STATUS and LAST LOGON columns. Inspect both.

```
PS YUSHA\admin> get-user kshrestha
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

```
PS YUSHA\admin> get-user mrai
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

And the non-human account, because service accounts deserve their own look:

```
PS YUSHA\admin> get-user svc-backup
User          : Backup Service
sAMAccountName: svc-backup
Title         : Service Account
OU            : Service Accounts
Status        : Enabled, service account
Failed logons : 0
Last logon    : today
Member of     : Domain Users
Description   : Runs the nightly backup job on FS-01.
```

### Required reasoning

**OBSERVATION:** `kshrestha` is enabled, has zero failed logons, and has not logged on for 210 days. `mrai` is enabled but **locked out** after 14 failed logons, with a description attributing them to an unknown workstation. `svc-backup` is a service account, active, and a member only of `Domain Users`.

**INTERPRETATION:**
- `kshrestha` is a **dormant but usable credential**. Nothing is broken; that is exactly the concern — an identity nobody uses is an identity nobody would notice being used.
- `mrai` is a control **firing correctly**. Fourteen failures against the domain's threshold of five (Exercise 6) locked the account. This is the lockout policy working, not a malfunction.
- `svc-backup` is *well configured* on the evidence available: it holds no group beyond `Domain Users`, which is least privilege for a backup job that only needs to read the Public share. Service accounts are frequently over-privileged; this one is not.

**SECURITY IMPACT:** the dormant account carries the `Finance` group's access with no oversight. The lockout is potentially the visible edge of a password-guessing attempt against a real user — the *account* is protected, but the *event* is unexplained.

**RECOMMENDATION:** for `kshrestha`, confirm the leave status with her manager, then disable (not delete — deletion loses the object's SID and history) and move to the `Disabled Accounts` OU. For `mrai`, investigate the source of the 14 attempts **before** unlocking; unlocking without investigating clears the symptom and leaves the cause.

**CONFIDENCE:** high on the account states — they are directly observed. Low on the *cause* of the failed logons; the description is a note left by someone else, not evidence this console produced.

### Common mistake

Unlocking `mrai` immediately because "the user can't work". Unlock is a two-minute fix that also destroys the reason to look. The order is: establish where the attempts came from, confirm the owner is in control of the credential, *then* unlock.

## 6. Exercise 3 — Groups and Where Privilege Actually Lives

**Objective:** find the privileged group and audit its membership.

```
PS YUSHA\admin> get-groups
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

```
PS YUSHA\admin> get-group "Domain Admins"
Group       : Domain Admins  (Built-in)
Description : Full administrative control of the domain. Membership must be minimal.
Members     : 2
⚠ PRIVILEGED GROUP — members have administrative control. Keep membership minimal.
  · administrator  Administrator
  · intern01       Bikash Magar (Intern)   ⚠ review — least privilege?
```

Confirm what that second member actually is, rather than trusting the display name:

```
PS YUSHA\admin> get-user intern01
User          : Bikash Magar (Intern)
sAMAccountName: intern01
Title         : IT Intern
OU            : Interns
Status        : Enabled
Failed logons : 0
Last logon    : today
Member of     : Domain Users, Domain Admins
  ⚠ MEMBER OF DOMAIN ADMINS
Description   : Summer intern assisting the IT team.
```

For contrast, the group that exists for the work an intern would plausibly be doing:

```
PS YUSHA\admin> members help-desk
Group       : Help Desk  (Custom)
Description : First-line support: password resets and unlocks.
Members     : 2
  · pgurung        Prakash Gurung
  · skhadka        Sujal Khadka
```

### Required reasoning

**OBSERVATION:** `Domain Admins` has two members: the built-in `administrator` account, and `intern01`, whose title is *IT Intern* and whose description is *Summer intern assisting the IT team*. A `Help Desk` group exists, scoped to password resets and unlocks, and the intern is not in it.

**EVIDENCE:** the `get-group "Domain Admins"` membership list, corroborated by the `Member of` line on the user object itself.

**INTERPRETATION:** a temporary, junior account holds full administrative control of the domain. The environment already contains a correctly-scoped group for the work this person is likely doing, which suggests the Domain Admins membership was a shortcut rather than a considered decision.

**SECURITY IMPACT:** this is the most serious finding in the domain. `intern01` can read, change or delete any object; reset any password including other administrators'; alter Group Policy that configures every machine; and — as Exercise 5 shows — reach every share at FULL control. A temporary account is also more likely to have a weak or shared credential and less likely to be monitored, so it is both the most powerful and the least watched identity here.

**RECOMMENDATION:** remove `intern01` from `Domain Admins`. If the intern genuinely needs to perform support tasks, add them to `Help Desk`, which is scoped to exactly that. More broadly: Domain Admins membership should be a short, reviewed list, and day-to-day work should never run under it.

**CONFIDENCE:** high. Membership is directly observed from two independent views, and the impact follows from what the group is defined to grant.

### What you cannot conclude

- That anything bad has happened. Over-privilege is a **risk**, not an incident. There is no evidence here that the account was misused.
- That removing the membership is safe to do *right now* without checking what would break. The correct sequence is: identify what the account is actually used for, provision the right group, then remove.

## 7. Exercise 4 — Structure: OUs and Computers

**Objective:** read the organisation's structure and understand what it does and does not control.

```
PS YUSHA\admin> get-ous
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

```
PS YUSHA\admin> get-ou IT
OU          : IT
Description : IT department staff.
Users       :
  · administrator (Administrator)
  · pgurung (Prakash Gurung)
  · rthapa (Rojina Thapa)
  · skhadka (Sujal Khadka)
Computers   :
  (none)
```

```
PS YUSHA\admin> get-ou Interns
OU          : Interns
Description : Temporary intern accounts — least privilege applies.
Users       :
  · intern01 (Bikash Magar (Intern))
Computers   :
  (none)
```

### Required reasoning

**OBSERVATION:** users are filed by department, computers by role, with a `Disabled Accounts` quarantine OU (currently empty) and a dedicated `Service Accounts` OU. The `Interns` OU is described as *least privilege applies*, and contains `intern01`.

**INTERPRETATION:** the structure is deliberate and reasonably designed. Crucially, it also shows the limit of what an OU does: `intern01` sits in an OU explicitly labelled *least privilege applies* **and holds Domain Admins anyway**. Container placement did not constrain the account's access in the slightest.

**SECURITY IMPACT:** this is Lesson 1's correction, demonstrated rather than asserted — an OU is not a security boundary. Anyone auditing by structure alone, reading "the intern is in the Interns OU", would miss the actual problem entirely. Effective access has to be computed from **group membership and ACLs**, never inferred from location.

**RECOMMENDATION:** keep the OU structure (it is good for delegation and policy scope — Exercise 6 uses it), and audit privilege by group membership independently of it. The empty `Disabled Accounts` OU is where `kshrestha` should end up after Exercise 2's recommendation.

**CONFIDENCE:** high.

## 8. Exercise 5 — Shares, ACLs and Effective Access

**Objective:** derive real users' effective access from group membership, and find where an ACL grants more than anyone intended.

```
PS YUSHA\admin> get-shares
SHARE                PATH                          ACL ENTRIES
──────────────────────────────────────────────────────────────
Finance-Reports      \\FS-01\Finance-Reports       3
HR-Confidential      \\FS-01\HR-Confidential       3
Public               \\FS-01\Public                2

Use `get-share <name>` for the full permission list, and `access <user> <share>` to test access.
```

```
PS YUSHA\admin> get-share HR-Confidential
Share       : HR-Confidential
Path        : \\FS-01\HR-Confidential
Server      : FS-01
Description : Salary reviews, disciplinary records, contracts.
Permissions :
  · HR               WRITE
  · Domain Users     READ   ⚠ everyone in the domain
  · Domain Admins    FULL
```

Now test it against real users, one at a time. Start with someone who *should* have access:

```
PS YUSHA\admin> access lbasnet HR-Confidential
ACCESS GRANTED — 'lbasnet' has WRITE on 'HR-Confidential' (\\FS-01\HR-Confidential).
  · via group 'HR' → WRITE
  · via group 'Domain Users' → READ
⚠ AUDIT FINDING: this access comes from 'Domain Users' — EVERY account in the domain can read this confidential share. That violates least privilege.
```

Then someone who has no HR role at all:

```
PS YUSHA\admin> access dtamang HR-Confidential
ACCESS GRANTED — 'dtamang' has READ on 'HR-Confidential' (\\FS-01\HR-Confidential).
  · via group 'Domain Users' → READ
⚠ AUDIT FINDING: this access comes from 'Domain Users' — EVERY account in the domain can read this confidential share. That violates least privilege.
```

Then the intern from Exercise 3:

```
PS YUSHA\admin> access intern01 HR-Confidential
ACCESS GRANTED — 'intern01' has FULL on 'HR-Confidential' (\\FS-01\HR-Confidential).
  · via group 'Domain Users' → READ
  · via group 'Domain Admins' → FULL
⚠ AUDIT FINDING: this access comes from 'Domain Users' — EVERY account in the domain can read this confidential share. That violates least privilege.
```

And a control case — a properly scoped share, to prove the pattern is not universal:

```
PS YUSHA\admin> access dtamang Finance-Reports
ACCESS GRANTED — 'dtamang' has WRITE on 'Finance-Reports' (\\FS-01\Finance-Reports).
  · via group 'Finance' → WRITE
```

```
PS YUSHA\admin> access skhadka Finance-Reports
ACCESS GRANTED — 'skhadka' has READ on 'Finance-Reports' (\\FS-01\Finance-Reports).
  · via group 'IT Support' → READ
```

### Required reasoning

**OBSERVATION:** `HR-Confidential`, described as holding salary reviews, disciplinary records and contracts, grants **READ to `Domain Users`** — a group containing all ten accounts in the domain. Dipesh Tamang, an accountant with no HR role, is granted READ purely through that entry. Laxmi Basnet gets WRITE via `HR` *and* READ via `Domain Users`, and her effective access is the more permissive of the two. `intern01` reaches FULL via `Domain Admins`. `Finance-Reports`, by contrast, grants only to `Finance`, `IT Support` and `Domain Admins` — no domain-wide entry.

**EVIDENCE:** the `get-share HR-Confidential` ACL, plus four `access` results each naming the group the right came from.

**INTERPRETATION:** the confidential share's ACL contains a domain-wide grant that its own description contradicts. Because `Finance-Reports` has no equivalent entry, this looks like a one-off — an entry added at some point to make something work, whose scope nobody re-examined. Note also the general rule visible in Laxmi's result: **allow rights from multiple groups accumulate, and the most permissive wins.**

**SECURITY IMPACT:** every account in the organisation — including the dormant `kshrestha` from Exercise 2 and the service account — can read salary and disciplinary records. That is a confidentiality failure affecting the most sensitive data in the environment, and it requires no attack at all: it is what the system is configured to do.

**RECOMMENDATION:** remove the `Domain Users` ACE from `HR-Confidential`, leaving `HR` (WRITE) and `Domain Admins` (FULL). Before removing it, identify what currently depends on it — if some legitimate process needs read access, grant that to a purpose-named group instead of to everyone. Then review every other share for domain-wide ACEs as a class of problem, not a one-off.

**CONFIDENCE:** high. The ACL is directly observed and the effective access was verified against four separate users, including a control case that behaves correctly.

### Common mistake

Reading the ACL and stopping. The ACL says `Domain Users READ`; it takes the second step — checking who is actually in `Domain Users`, and running `access` against a real user — to turn that line into the sentence that makes a manager act: *"our accountant can read the salary reviews."*

## 9. Exercise 6 — Group Policy

**Objective:** read the domain's policy, work out who it applies to, and judge whether it is adequate.

```
PS YUSHA\admin> gpos
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

```
PS YUSHA\admin> policy
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

**The four questions to ask of any policy:**

| Question | `Default Domain Policy` | `Desktop Restrictions` |
|---|---|---|
| What does it control? | Password strength/age/history; lockout behaviour | Control Panel, command prompt, USB storage, wallpaper |
| Who does it apply to? | Linked to **domain** — everything in it | Linked to **interns** and **workstations** OUs only |
| Why is it security-relevant? | Sets the credential floor for every identity; bounds online guessing | Restricts local reconfiguration and blocks removable-storage data movement |
| What if it were too permissive? | A 6-character minimum, or no lockout, would make guessing cheap domain-wide | Interns could reconfigure their machine or copy data to USB |

### Required reasoning

**OBSERVATION:** the domain-linked security GPO requires 12-character complex passwords with a 90-day maximum age and 5 remembered, and locks accounts after 5 failed attempts in a 15-minute window for 30 minutes. A second GPO applies desktop restrictions to the `interns` and `workstations` OUs. A third maps drives domain-wide.

**INTERPRETATION:** the password and lockout baseline is **reasonable** — 12 characters with complexity is a defensible floor, and the lockout thresholds directly explain Manisha Rai's locked account from Exercise 2 (14 attempts against a threshold of 5). The scoping of `Desktop Restrictions` also demonstrates the GPO/OU relationship concretely: it reaches objects in two OUs and nothing else, which is why *where an object sits* determines what policy it gets.

**SECURITY IMPACT:** this is the control that fired in Exercise 2. It is also the reason a weak GPO would be so serious — a bad setting linked at the domain is a bad setting applied to everything, consistently.

**RECOMMENDATION:** the baseline is sound; the questions worth raising are ones this output does not answer — is multi-factor authentication required for privileged accounts, and what does the **audit policy** record? Neither appears in these three GPOs, and an environment that logs nothing cannot investigate the Exercise 2 lockout properly.

**CONFIDENCE:** high on what the policies contain; the audit-policy gap is an *absence* in this simulated environment's data, not proof that a real organisation lacks one.

### The connection worth making

`Desktop Restrictions` is linked to the `interns` OU and denies the command prompt and USB storage to `intern01`. That same account is in **Domain Admins**. The policy restricts the desktop; the group membership grants the domain. Policy scope and privilege are entirely separate mechanisms, and constraining one says nothing about the other.

## 10. Exercise 7 — Watching Kerberos

**Objective:** observe authentication succeed and fail, and locate the exact point where authorization is decided.

```
PS YUSHA\admin> kerberos skhadka
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

Now the same command against the locked account:

```
PS YUSHA\admin> kerberos mrai
KERBEROS AUTHENTICATION — Manisha Rai (YUSHA.LOCAL)
────────────────────────────────────────────────────────
[1] AS-REQ   mrai → DC-01 (KDC): "I am mrai, here is proof (encrypted timestamp)"
[2] AS-REP   DC-01 → KDC_ERR_CLIENT_REVOKED

✗ REFUSED — the account is LOCKED OUT (14 failed attempts). The lockout policy is doing its job; unlock only after confirming the owner is in control of the credentials.
```

And the consequence at the resource:

```
PS YUSHA\admin> access mrai HR-Confidential
ACCESS DENIED — 'mrai' cannot authenticate: the account is locked out.
(No Kerberos ticket → no access, whatever the ACL says.)
```

**Answer these before reading on:**

1. Which steps involve the KDC, and which involve the file server?
2. Why does the client obtain a service ticket rather than sending the password to `FS-01`?
3. At which numbered step is *authorization* decided — and on which machine?
4. `mrai` is a member of the `HR` group, which has WRITE on `HR-Confidential`. Why is she denied?

<details>
<summary>Discussion</summary>

**1.** Steps 1–4 involve the KDC on `DC-01`: the AS exchange issues the TGT, the TGS exchange issues the service ticket. Steps 5–6 involve `FS-01` only. Note that the file server never contacts the DC in this flow — it validates the ticket itself.

**2.** Because sending the password would expose it to `FS-01` (and to every other service, on every access), would require `FS-01` to be able to verify credentials, and would put the secret on the network repeatedly. The ticket lets `FS-01` verify the KDC's assertion without ever seeing the password, and the user's secret is used once, at logon.

**3.** Step **[6]**, on **`FS-01`** — the resource, not the Domain Controller. The ticket carries the user's group memberships; the server compares those against its own ACL. The KDC has no opinion about which shares exist.

**4.** Because the flow never reaches step 6. Authentication fails at step 2 with `KDC_ERR_CLIENT_REVOKED`, so no TGT is issued, so no service ticket exists, so there is nothing to present to `FS-01`. Her `HR` membership is irrelevant — the ACL is never consulted. That is the ordering the `access mrai` output states outright: *no Kerberos ticket → no access, whatever the ACL says.*
</details>

## 11. Exercise 8 — The Investigation Report

An observation is not a finding. A finding is a claim someone else can verify, whose impact someone can weigh, with a control someone can implement.

### The template

```
OBSERVATION:
    What the environment showed. Fact only, no judgement.

EVIDENCE:
    The exact command and the exact output that supports it.

AD COMPONENT:
    Which part of Active Directory this concerns — group membership,
    share ACL, GPO, account state, directory object.

SECURITY RELEVANCE:
    Why this matters as a security question rather than a tidiness one.

POTENTIAL IMPACT:
    What it lets someone do, concretely, in this environment.

RECOMMENDED CONTROL:
    The specific change, and what to check before making it.

CONFIDENCE:
    High / Medium / Low, and what would raise it.
```

### Worked example — the finding from Exercise 3

```
OBSERVATION:
    The account intern01 ("Bikash Magar (Intern)", title: IT Intern) is
    a member of the Domain Admins group.

EVIDENCE:
    get-group "Domain Admins" lists two members: administrator and
    intern01, with the console's own marker "⚠ review — least
    privilege?". Confirmed independently on the user object:
    get-user intern01 shows "Member of : Domain Users, Domain Admins"
    and "⚠ MEMBER OF DOMAIN ADMINS".

AD COMPONENT:
    Group membership — a built-in privileged security group.

SECURITY RELEVANCE:
    Domain Admins grants full administrative control of the domain.
    A temporary, junior account holding it breaks least privilege and
    separation of administrative roles. A correctly scoped group for
    this person's actual work already exists: Help Desk, described as
    "First-line support: password resets and unlocks".

POTENTIAL IMPACT:
    The account can read, modify or delete any directory object; reset
    any password including other administrators'; alter Group Policy
    affecting every machine in the domain; and reach every share at
    FULL control — verified: access intern01 HR-Confidential returns
    FULL via Domain Admins. A temporary account is also less likely to
    be monitored and more likely to have a shared credential, so this
    is simultaneously the most powerful and least supervised identity
    in the domain.

RECOMMENDED CONTROL:
    Remove intern01 from Domain Admins. If support duties are genuinely
    required, add to Help Desk instead. Before removing, confirm what
    the account is currently used for so nothing breaks silently. More
    broadly, review Domain Admins membership on a schedule and keep
    day-to-day work off privileged accounts.

CONFIDENCE:
    High. Membership is directly observed from two independent views,
    and the impact follows from the group's defined rights, confirmed
    against a real resource.
```

### Worked example — the finding from Exercise 5

```
OBSERVATION:
    The HR-Confidential share grants READ to the Domain Users group.

EVIDENCE:
    get-share HR-Confidential lists three ACEs — HR WRITE, Domain Users
    READ (flagged "⚠ everyone in the domain"), Domain Admins FULL. The
    share is described as holding "Salary reviews, disciplinary records,
    contracts". get-group "Domain Users" lists all 10 domain accounts.
    Verified against a user with no HR role: access dtamang
    HR-Confidential returns READ "via group 'Domain Users'".

AD COMPONENT:
    Share ACL — an access control entry naming a domain-wide group.

SECURITY RELEVANCE:
    The ACL contradicts the share's own stated purpose. Access is granted
    to a group that contains every account in the organisation, so the
    control that is supposed to restrict this data does not restrict it
    at all.

POTENTIAL IMPACT:
    Every account in the domain can read salary and disciplinary records
    — including the dormant kshrestha account (210 days unused) and the
    svc-backup service account. No attack is required; this is the
    configured behaviour. By contrast Finance-Reports grants only to
    Finance, IT Support and Domain Admins, so this is not the
    organisation's normal pattern.

RECOMMENDED CONTROL:
    Remove the Domain Users ACE from HR-Confidential, leaving HR (WRITE)
    and Domain Admins (FULL). First identify what currently relies on
    that entry; if some legitimate need exists, grant it to a
    purpose-named group rather than to everyone. Then review all shares
    for domain-wide ACEs as a class.

CONFIDENCE:
    High. The ACL is directly observed and effective access was verified
    against four users, including a correctly-scoped control case.
```

### Your turn

Write the same report for **`kshrestha`** (Exercise 2). It is deliberately the hardest of the three, because nothing about the account is flagged as broken — it is enabled, unlocked, with zero failed logons. Your SECURITY RELEVANCE section has to explain why an account that looks healthy belongs in a report at all, and your CONFIDENCE section has to be honest that 210 days of inactivity is evidence of an unmonitored credential and **not** evidence of compromise.

## 12. Common Mistakes

1. **Auditing by structure.** `intern01` sits in an OU labelled *least privilege applies* and holds Domain Admins. Container placement is not access.
2. **Reading an ACL without resolving the groups.** `Domain Users READ` is a line of configuration; "our accountant can read salary reviews" is a finding.
3. **Fixing before investigating.** Unlocking `mrai` clears the symptom and destroys the reason to look for the cause.
4. **Confusing a control firing with a control failing.** The lockout worked. The unexplained 14 attempts are the open question.
5. **Treating over-privilege as an incident.** It is a risk. Nothing observed here shows the intern's account was misused, and saying otherwise in a report is a claim you cannot support.
6. **Stopping at the first finding.** Three separate issues exist in a ten-user domain. The `Finance-Reports` control case is what proves the HR share is an anomaly rather than the house style.
7. **Deleting instead of disabling.** Deleting an account destroys its SID and its history; recreating it does not restore its access. Disable and quarantine.
8. **Assuming one Domain Controller is normal.** It is normal *here*, in a training domain. In production it would be its own finding.

## 13. Practising on This Platform

The real **active-directory** lab category contains five labs, all running the same simulated `YUSHA.LOCAL` domain and the same console you used above:

| Lab | What it adds |
|---|---|
| **AD Basics: Explore YUSHA.LOCAL** | The orientation this lesson is built on — users, groups, OUs, the Domain Controller, shares, and a Kerberos authentication, as six scored objectives |
| **Find the Inactive Account** | Exercise 2's dormant-account reasoning, taken through to disabling and quarantining |
| **The Compromised Password** | Exercise 2's lockout, taken through investigation to a policy-compliant reset |
| **The Over-Privileged Intern** | Exercise 3's finding, taken through to remediation |
| **Least Privilege Audit** | Exercise 5's share ACL, taken through to a full audit |

They unlock **in that order**, each requiring the previous one — so start at the first, which is linked directly from this lesson and needs no prerequisite. Note the shape of that progression: this lesson teaches you to *find* these four issues; the labs then have you *fix* them, using the account- and group-management commands §2 deliberately left alone.

**There is no Active Directory terminal mission on this platform.** The mission engine's sixteen missions cover Linux, networking, Nmap, Wireshark and web security; none involves a domain. That is a real gap, stated rather than papered over — the AD labs above are the practice environment for this module, and no mission link is offered because there is nothing to link to.

## 14. Where This Goes Next

Six modules now stack on each other, and the last three are one continuous idea:

- **Computer Networking** — DNS, which AD needs before it can do anything
- **Linux Fundamentals** — identity and permissions, the same questions in a different operating system
- **Web Fundamentals** and the **OWASP Top 10** — authentication versus authorization, and broken access control as the most common failure of all
- **Burp Suite** — evidence-driven investigation: change one thing, compare, conclude carefully
- **Active Directory Basics** — the same two questions (*who are you?*, *what may you do?*) answered by enterprise identity infrastructure

The transferable habit is the one you just practised: read what the system actually says, work out what it *means* before deciding whether it is a *problem*, name the impact concretely, and state your confidence.

**Metasploit**, **Windows Privilege Escalation** and **Linux Privilege Escalation** come next in this track, and the Red Team track's **Active Directory Attacks** takes the three findings you just wrote up and shows what an attacker does with exactly that kind of configuration. All of them assume what this module built: that you can read a directory, derive effective access from group membership, and explain what you are looking at.

And the professional habit that outlasts the technology: **an observation is a fact, a finding is a fact plus its impact, and a recommendation is what makes anyone act on either.**
