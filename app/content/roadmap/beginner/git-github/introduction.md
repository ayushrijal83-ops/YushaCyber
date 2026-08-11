# Introduction to Git & GitHub

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain the actual problem version control solves, in concrete terms
- explain the precise difference between Git and GitHub — they are not the same thing, and conflating them is one of the most common beginner mistakes
- describe Git's three-area mental model: working directory, staging area, repository
- run `git init`, `git status`, `git add`, and `git commit`, and read their real output correctly
- explain why a security-minded developer treats version-control history as something that never truly disappears

## 2. Why This Matters

Every later module in this platform assumes you can save, track, and share code without losing work or overwriting someone else's. Python Programming already had you writing `.py` script files — Git is how those files (and every other file you'll write from here on) get a permanent, inspectable history instead of a single, fragile copy on disk. It also matters for a reason that isn't obvious yet and will come up repeatedly once you reach the Intermediate and Red Team tracks: **a huge number of real-world security incidents trace back to something committed to a Git repository that should never have been there** — an API key, a password, a private key. Understanding how Git actually stores things is what makes that risk make sense, rather than being a rule you follow without knowing why.

## 3. The Problem: Why Version Control Exists at All

Picture working on a Python script the way Python Programming had you do it, with no tool beyond a text editor. You make a change, it breaks something, and you want yesterday's working version back — but you already overwrote it. You start renaming files `script.py`, `script_v2.py`, `script_v2_final.py`, `script_v2_final_ACTUALLY.py` to cope. Now imagine a second person editing the same file: whoever saves last silently destroys the other person's changes, with no warning and no way to combine both sets of edits.

**Version control** is software that solves both problems at once: it records every change to a set of files over time, lets you go back to any previous point, shows you exactly what changed and when, and — critically — can combine two people's independent changes into one result instead of one overwriting the other. **Git** is, by a wide margin, the version control system the software industry actually uses today.

## 4. Git vs. GitHub — The Distinction That Actually Matters

This is the single most important thing to get exactly right in this lesson, because getting it wrong will confuse almost everything that follows.

**Git is a program.** It's version-control software that runs entirely on your own computer. Every single command in this module — `git init`, `git add`, `git commit`, `git log`, and everything Core Concepts and Hands-on Practice cover — works completely offline, with no network connection and no relationship to any website at all. Git existed, and was fully useful, years before GitHub did.

**GitHub is a website and hosting service.** It stores copies of Git repositories on servers you don't own, adds a web interface for browsing code, and adds collaboration features on top of Git that aren't part of Git itself at all — pull requests, issues, code review, GitHub Actions. GitHub uses Git as its underlying engine, but so do several of its direct competitors (GitLab, Bitbucket) — GitHub is *one company's product built on top of Git*, not Git's official home, and not the same thing as version control itself.

Here's the test that actually proves the distinction, worth remembering: **you can use Git, fully, on a private project, forever, without ever creating a GitHub account or touching the internet.** GitHub only enters the picture the moment you want a remote copy — a backup off your machine, or a way for other people to see or contribute to your work. This lesson covers Git on its own first; Core Concepts and Hands-on Practice bring GitHub in once you have the local vocabulary to understand what it's actually adding.

## 5. Git's Mental Model: Three Areas

Everything Git does moves a file's content through three distinct areas, and almost every point of beginner confusion comes from not tracking which area a change is currently in:

```
Working Directory  →  Staging Area  →  Repository
   (your files,         (changes you've      (permanent history —
    as you edit          marked as ready       every committed
    them normally)       to be recorded)       snapshot, forever)
```

**Working directory** — the actual files on your disk, exactly as you'd see them in a file browser or text editor. Editing a file changes it here first, and only here — Git doesn't know or care about this edit yet.

**Staging area** (also called "the index") — a holding area where you explicitly list which changes you want included in the *next* commit. This is the step beginners most often skip past without understanding: Git does not automatically commit every change in your working directory — you choose what goes in, one `git add` at a time.

**Repository** — the permanent, committed history. Once a change is committed, it's recorded as a snapshot with a timestamp, an author, and a message, and it stays part of the project's history from then on.

The reason this three-area split exists, rather than Git just saving everything automatically, is control: it lets you build one clean, deliberate commit ("fix the login bug") instead of one messy commit that accidentally bundles in an unrelated half-finished edit you happened to have open in another file.

## 6. Your First Repository

**`git init`** — turns the current directory into a Git repository. **What it does:** creates a hidden `.git` folder that holds the entire repository — every commit, every piece of history, all of it lives there, invisible during normal browsing.

```bash
git init
```

**Expected output:**

```
Initialized empty Git repository in /home/student/project/.git/
```

**Common mistake:** running `git init` inside a folder that's already a Git repository (or worse, inside your entire home directory by accident). Check first with `git status` — if it responds normally instead of with "not a git repository," you're already inside one.

**`git status`** — the command you will run more than any other. **What it does:** reports the current state of your working directory and staging area — what's changed, what's staged, what Git isn't tracking yet.

```bash
git status
```

**Expected output**, right after `git init` with nothing added yet:

```
On branch main

No commits yet

nothing to commit, working tree clean
```

Create a file and run it again:

```bash
touch notes.py
git status
```

```
On branch main

No commits yet

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	notes.py

nothing added to commit but untracked files present (use "git add" to track)
```

**What the output means:** "Untracked" is Git's precise term for a file it has noticed exists but has never been told to track — it's sitting in the working directory (Section 5) and nothing more. Git is explicitly telling you the next step in its own suggested command, right there in the output — reading `git status` output line by line, instead of skimming past it, is a habit worth building immediately.

## 7. Staging and Committing

**`git add`** — moves a change from the working directory into the staging area. **What it does:** tells Git "include this file's current state in my next commit."

```bash
git add notes.py
git status
```

```
On branch main

No commits yet

Changes to be committed:
  (use "git rm --cached <file>..." to unstage)
	new file:   notes.py
```

Notice exactly what changed in the output: `notes.py` moved from "Untracked files" to "Changes to be committed" — same file, different area (Section 5's staging area), and `git status` names the area explicitly every time.

**`git commit`** — takes everything currently staged and permanently records it as a snapshot in the repository.

```bash
git commit -m "Add notes.py"
```

```
[main (root-commit) 8f3a1c2] Add notes.py
 1 file changed, 0 insertions(+), 0 deletions(-)
 create mode 100644 notes.py
```

**What the output means:** `8f3a1c2` is the first characters of this commit's unique ID (a full commit hash is 40 characters — Git shortens it for display). `(root-commit)` marks this as the very first commit in the repository's history. Everything after that is a summary of what changed.

**The `-m` flag matters specifically:** it lets you supply the commit message directly on the command line. Without it, `git commit` opens a text editor and *requires* you to type a message before it will let the commit proceed — Git will not accept an empty commit message. This is deliberate, not an inconvenience: a commit with no message is a snapshot with no explanation of *why* it exists, which defeats a large part of the point of keeping history at all.

Run `git status` one more time:

```
On branch main
nothing to commit, working tree clean
```

"Clean" is Git's word for "the working directory and staging area currently match the last commit exactly" — nothing edited, nothing staged, nothing to lose.

## 8. Common Mistakes

**Assuming `git add` sends anything anywhere.** It doesn't touch the network, another computer, or GitHub — it only moves a change from the working directory to the staging area, entirely on your own machine. Section 4's Git/GitHub distinction is exactly why this confusion happens: people expect "adding" a file to mean uploading it somewhere, because that's what "add" means on many websites.

**Committing without ever running `git status` first.** Skipping it means committing blind — you don't actually know what's staged until you check, and "I thought I only changed one file" is one of the most common real mistakes in version control.

**Treating an empty commit message as acceptable.** `git commit -m ""` will be rejected — and even where a tool lets a vague message like `-m "fix"` through, it defeats the purpose covered in Section 7: a future reader (often you, months later) needs to know *why* a change happened, not just that something changed.

## 9. Practice

In any terminal with Git installed (this lesson's commands run identically on your own machine — Section 4 established that Git needs no network and no GitHub account at all):

1. Create a new empty folder and run `git init` inside it. Confirm the exact wording Git uses to tell you it worked.
2. Create one file, then run `git status` before staging anything. Identify which of the three areas from Section 5 that file is currently in.
3. Stage the file, run `git status` again, and note precisely how the wording changed.
4. Commit it with a real, descriptive message, then run `git status` one final time and explain, in your own words, what "clean" means.

## 10. Knowledge Check

1. What specific problem does version control solve that a folder full of manually renamed file copies doesn't?
2. In one sentence each: what is Git, and what is GitHub — and why are they not interchangeable words?
3. Name Git's three areas in order, and say which command moves a change from the first to the second.
4. Why does `git commit` refuse an empty message, and why does that matter beyond this one command?
5. A file shows up under "Untracked files" in `git status`. What does that specifically tell you, and not tell you, about that file?

## 11. Key Takeaways

- Version control tracks every change over time and can combine two people's edits — solving both "I lost my working version" and "we overwrote each other's work" at once.
- Git is standalone software that runs entirely on your machine, with no network or account required; GitHub is a separate hosting website built on top of Git, one of several such services.
- Every changed file moves through three areas in order: working directory (your edits) → staging area (`git add`, what you've chosen for the next commit) → repository (`git commit`, permanent history).
- `git status` is the single most useful command in this lesson — it names, explicitly, which area every change is currently in, and even suggests the next command.
- A commit without a real message throws away the one thing that makes history actually useful later: knowing *why* a change was made.

## 12. What's Next

**Core Concepts** goes further into the repository itself: reading history with `git log`, seeing exactly what changed with `git diff`, branching to work on something without disturbing the main line of work, and — for the first time in this module — what a **remote** actually is, which is where GitHub finally enters the picture.
