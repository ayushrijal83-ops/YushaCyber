# Hands-on Practice: Working With GitHub, and Committing Safely

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what `git clone` actually does, in terms of Introduction's three-area model
- explain what a GitHub repository adds on top of a plain Git repository: forks, pull requests, issues, and a README
- describe the standard feature-branch collaboration workflow, start to finish
- explain, precisely, why committing a secret is a serious security mistake — and why deleting it afterward doesn't fix it
- write a `.gitignore` for a real Python project, and know what to do if a secret is committed anyway
- walk a small, realistic collaboration scenario end to end

## 2. Why This Matters

Core Concepts ended at the exact point GitHub becomes relevant: a remote, referenced but not yet used. This lesson is where that reference becomes real work — getting a copy of an existing project, contributing to it the way real open-source and team projects expect, and the one mistake in this entire module with real, immediate security consequences if you get it wrong. This last part connects directly back to Cybersecurity Fundamentals: a leaked credential is exactly the kind of **asset** that module taught you to identify and protect — this lesson is where you learn one of the most common real ways that asset actually gets exposed.

## 3. Cloning: Getting a Local Copy of a Remote Repository

**`git clone`** — creates a full local copy of a remote repository, including its **entire commit history**, not just its current files.

```bash
git clone https://github.com/example-org/example-project.git
```

**Expected output:**

```
Cloning into 'example-project'...
remote: Enumerating objects: 142, done.
remote: Counting objects: 100% (142/142), done.
remote: Compressing objects: 100% (98/98), done.
Receiving objects: 100% (142/142), 38.21 KiB | 2.12 MiB/s, done.
Resolving deltas: 100% (61/61), done.
```

**What actually happened:** Git created a new folder (`example-project`), copied every object in the remote's history into it, checked out the default branch's latest commit into your working directory, and automatically set up a remote named `origin` pointing back at the URL you cloned — the exact `git remote add` step from Core Concepts, done for you. Run `git log --oneline` immediately after cloning and you'll see the project's *entire* real history, not just its latest state — this is the concrete proof that `git clone` copies history, not a snapshot.

**Why this matters beyond convenience:** it's also why Section 6's warning about committed secrets is as serious as it is. Anyone who clones a repository gets every commit that was ever pushed to it, not just the current files — including anything sensitive that was committed and later "removed" in a newer commit. The old commit, and whatever it contained, is still sitting in history, and `git clone` hands it over along with everything else.

## 4. What GitHub Adds on Top of Git

Introduction drew a hard line between Git (the tool) and GitHub (a hosting service built on it). Here's exactly what's on GitHub's side of that line — none of it is a Git feature; all of it is GitHub's own product built around a Git repository:

- **A repository page** — a web UI for browsing a project's files, history, and branches without needing Git installed at all.
- **README.md** — an ordinary file (rendered as page content), by convention the first thing GitHub displays for a repository — a project's self-description, not a Git mechanism.
- **Issues** — GitHub's tracker for bugs, questions, and planned work, tied to a repository but stored on GitHub's servers, not in your `.git` history.
- **Forks** — your own personal, full copy of someone else's repository, hosted under your own GitHub account. A fork is how you get write access to try changes on a project you don't have direct permission to push to — you can commit freely to your fork without touching the original at all.
- **Pull requests (PRs)** — a request, opened on GitHub, asking a repository's maintainers to merge a specific branch (often from your fork) into their project. A pull request is a *conversation about a merge* — comments, review, requested changes — layered on top of Git's plain `merge` command from Core Concepts, not a replacement for it.

## 5. The Feature-Branch Workflow, End to End

This is the standard shape of contributing to a real project, combining Core Concepts' branching with this lesson's GitHub concepts:

```
Fork the repository (your own copy, on GitHub)
    ↓
Clone your fork locally (git clone)
    ↓
Create a branch for your change (git switch -c fix-typo)
    ↓
Make the change, commit it (git add, git commit)
    ↓
Push the branch to your fork (git push origin fix-typo)
    ↓
Open a pull request on GitHub, from your branch to the original project
    ↓
Maintainers review, request changes or approve
    ↓
Pull request is merged into the original project
```

Notice how little of this is actually new: everything up through "commit it" is exactly Introduction and Core Concepts. `git push` is the one genuinely new command:

```bash
git push origin fix-typo
```

```
Enumerating objects: 5, done.
Counting objects: 100% (5/5), done.
Writing objects: 100% (3/3), 312 bytes | 312.00 KiB/s, done.
To https://github.com/your-username/example-project.git
 * [new branch]      fix-typo -> fix-typo
```

**What it does:** sends your local commits on `fix-typo` to the `origin` remote, creating a matching branch there if one doesn't already exist. Nothing about this is different from any other network upload conceptually — it's the same client/server relationship Web Fundamentals already taught you, applied to Git's commit history instead of HTTP requests.

**Why the *branch* specifically, not `main` directly:** almost every real project either restricts who can push directly to `main`, or simply expects contributions through pull requests as a review step — pushing a feature branch and opening a PR is the normal, expected way to propose a change you don't have (or shouldn't use) direct write access for.

## 6. Never Commit a Secret

Here's the security lesson this whole module has been building toward, and it deserves to be stated as plainly as possible: **a password, API key, private key, or any other credential that gets committed to a Git repository should be treated as permanently compromised the moment it's pushed — even if you delete it in the very next commit.**

Walk through exactly why, using what you already know from this lesson:

1. You accidentally commit a file containing a real API key.
2. You notice, and immediately commit a fix that removes it.
3. You push both commits to GitHub.

**The key is still exposed**, for a very specific reason: Section 3 established that `git clone` (and every `git pull`) transfers a repository's *entire history*, not just its latest state. Your "fix" commit only changes what the *current* files look like — the earlier commit, containing the real key, is still sitting in history, permanently reachable by anyone who clones the repository or simply browses its commit history on GitHub. If the repository is public, this includes automated bots that actively scan public GitHub commits for exactly this pattern, continuously, within minutes of a push — this is not a hypothetical risk, it's routine, automated, and fast.

**The only real fix, once a secret has been pushed, is to treat the credential itself as burned: rotate it.** Generate a new API key or password and revoke the old one at the source (the service that issued it), exactly as if it had been stolen — because, for practical purposes, it has been. Rewriting Git history to strip the secret out (a real, more advanced technique) does not undo the exposure by itself, because the key may have already been cloned, cached, or scraped before the rewrite ever happened; it only prevents *new* clones from getting it. Rotating the credential is the step that actually closes the risk.

**Prevention is far cheaper than remediation** — this is Core Concepts' `.gitignore` doing real security work, not just tidiness:

```
.env
*.pem
*.key
secrets.json
config/credentials.yml
```

Combine this with the practice, standard across real projects, of never hardcoding a real secret directly in a source file at all — reading it from an environment variable or an untracked config file instead, so there's nothing sensitive in the code Git tracks in the first place. A `.gitignore` only protects a secret that's never been staged; Section 3 and this section together are why "just remove it later" isn't a real safety net.

## 7. Common Mistakes

**Believing `.gitignore` retroactively protects an already-committed secret.** Core Concepts already established this technically; this lesson is why it's not just a technicality — it's the exact gap that turns a mistake into a real incident.

**Treating "I deleted it in a later commit" as resolved.** History (Section 3) means the earlier commit, and whatever it contained, doesn't go away just because a newer commit looks clean.

**Pushing directly to `main` on a project you don't maintain.** The feature-branch-then-pull-request workflow (Section 5) exists specifically so changes get reviewed before landing — skipping it isn't a shortcut, it's usually just rejected or reverted.

**Assuming a private repository makes committed secrets safe.** Private repositories limit *who* can see the history — they don't change anything about Sections 3 and 6's underlying mechanism. Anyone with legitimate access still has the entire history, and access lists change over time (a collaborator leaves, a repository is later made public by mistake) — rotating a leaked credential is still the only real fix.

## 8. A Note on Practicing These Commands

Every command in this module — `git init` through `git push` — is standard Git, and runs identically on your own machine once Git is installed; none of it depends on anything specific to this platform. **This platform's terminal does not currently include a Git simulation**, unlike the filesystem and networking commands from earlier modules — there's no `git` command available in the free-practice terminal or any terminal mission yet. The most useful way to practice this module is on your own machine: install Git, create a scratch folder, and work through Introduction's and Core Concepts' examples directly, for real. A dedicated Git lab or mission is a real, documented gap for a future pass — not something this lesson works around with an unrelated substitute.

## 9. Capstone Scenario: A Small Team Project

Two students, Aisha and Marcus, are collaborating on a small Python script that's hosted in a GitHub repository Aisha owns.

1. Marcus wants to fix a bug. He doesn't have push access to Aisha's repository directly. What are his first two steps, in order, before he writes a single line of code? *(Section 5)*
2. Marcus finishes the fix on a branch called `fix-divide-by-zero` and wants Aisha to review it before it becomes part of the project. What does he open, and what is it, precisely, layered on top of? *(Section 4)*
3. While testing, Marcus's script briefly printed a real database password to the console, and he accidentally committed a log file containing it before catching the mistake in his next commit. What should Marcus actually do now, and what should he *not* assume is already handled? *(Section 6)*
4. Aisha reviews the pull request and approves it. What real Git command, running on GitHub's own servers, does "merging" the pull request ultimately perform? *(Section 5, Core Concepts Section 5)*

Work through your own answers before continuing — this scenario deliberately combines every major idea from this module into one situation, the same way it would come up in real, everyday work.

## 10. Knowledge Check

1. What does `git clone` actually copy — just the current files, or something more? Why does that answer matter for Section 6?
2. Name two things GitHub adds on top of plain Git, and explain why neither one is a Git feature itself.
3. In the feature-branch workflow, why do most real projects expect a pull request rather than a direct push to `main`?
4. A teammate committed an API key and then deleted it in the very next commit. Is the key still exposed? Explain exactly why, using what `git clone`/`git pull` actually transfer.
5. What is the one real fix for an already-pushed secret, and why doesn't simply removing it from the latest commit count?
6. Does making a repository private change anything about Section 6's core risk? Why or why not?

## 11. Key Takeaways

- `git clone` copies a repository's entire history, not just its current state — this is *why* an old, committed secret stays exposed even after being removed from later commits.
- GitHub's README, Issues, forks, and pull requests are all built on top of Git, not part of Git itself — Introduction's Git/GitHub distinction holds all the way through this lesson's most advanced concepts.
- The standard collaboration workflow is fork → clone → branch → commit → push → pull request → review → merge — almost entirely built from commands you already know from Introduction and Core Concepts.
- A committed secret should be treated as compromised the instant it's pushed; the only real fix is rotating the credential at its source, not editing history after the fact.
- This platform has no Git terminal simulation yet — practicing these commands for real happens on your own machine, and a dedicated Git lab/mission is a documented gap, not something worked around here.

## 12. What's Next

This is the last lesson in Git & GitHub — every module ahead of you that involves writing your own code or scripts (and several Intermediate and Red Team labs that provide starter code from a repository) now assumes you can track, branch, and share that work without losing it or leaking something that shouldn't be public. The roadmap's next module, **Operating Systems**, shifts back to systems fundamentals — but the habit this module was really teaching, treating your own change history as something deliberate and inspectable rather than accidental, is one you'll keep using for the rest of this platform and well beyond it.
