# Core Concepts: History, Branches, and Remotes

## 1. What You Will Learn

By the end of this lesson you should be able to:

- read `git log` and `git diff` output and explain exactly what each is showing you
- explain why `git diff` alone and `git diff --staged` show two different things, and when to use each
- create and switch branches, and explain what a branch actually is under the hood
- explain what a merge conflict is and why it happens, in terms of the three-area model from Introduction
- write a `.gitignore` file and explain what problem it solves
- explain what a **remote** is, and connect it to how GitHub actually fits into the picture

## 2. Why This Matters

Introduction gave you a single, linear history: one file, staged, committed, done. Real work is never that linear — you'll want to try something risky without breaking what already works, look back at what changed and why, and eventually share your work with someone else (or with your future self, on a different machine). Every concept in this lesson exists to make one of those three things possible.

## 3. Reading History: `git log`

**What it does:** `git log` lists every commit in the current branch's history, most recent first.

```bash
git log
```

**Expected output** (continuing Introduction's repository, after a second commit):

```
commit 4b7e9a1c2d5f8e3a6b9c1d4e7f0a3b6c9d2e5f8a
Author: student <student@example.local>
Date:   Mon Aug 10 14:22:03 2026 +0000

    Add a second script

commit 8f3a1c2b5d8e1a4b7c0d3e6f9a2b5c8d1e4f7a0b
Author: student <student@example.local>
Date:   Mon Aug 10 14:10:47 2026 +0000

    Add notes.py
```

**What the output means:** each block is one commit, newest at the top — the full 40-character hash (Introduction only showed you the shortened version), who made it, when, and the message you wrote. This is the entire point of committing with real messages, made concrete: six months from now, `git log` is how you (or anyone else) reconstructs *why* the project looks the way it does.

**A shorter, everyday version:**

```bash
git log --oneline
```

```
4b7e9a1 Add a second script
8f3a1c2 Add notes.py
```

Same history, compressed to one line per commit — this is the version you'll actually reach for most often once a project has more than a handful of commits.

## 4. Seeing What Changed: `git diff`

**What it does:** shows the exact line-by-line difference between two states of your files. Which two states depends on which form you use — and this is the detail that trips up almost every beginner.

**`git diff`** (no arguments) — compares your **working directory** against the **staging area**. It shows changes you've made but haven't staged yet.

**`git diff --staged`** — compares the **staging area** against the **last commit**. It shows exactly what would go into your next commit if you ran `git commit` right now.

Edit an already-committed file and run both, side by side, to see the distinction:

```bash
git diff
```

```
diff --git a/notes.py b/notes.py
index e69de29..8a3f21b 100644
--- a/notes.py
+++ b/notes.py
@@ -0,0 +1 @@
+print("hello from git")
```

```bash
git add notes.py
git diff
```

```

```

**Notice the second `git diff` produced no output at all** — not an error, an empty result. That's the correct, meaningful answer: once you `git add` the change, it's no longer a difference between working directory and staging area (they now match); it becomes visible under `git diff --staged` instead, because *that's* now the actual pending change:

```bash
git diff --staged
```

```
diff --git a/notes.py b/notes.py
index e69de29..8a3f21b 100644
--- a/notes.py
+++ b/notes.py
@@ -0,0 +1 @@
+print("hello from git")
```

**How to read the `+`/`-` lines specifically:** a line starting with `+` was added; a line starting with `-` was removed; a line with neither was unchanged context, shown so you can see where the change sits. `e69de29..8a3f21b` are shortened content hashes — Git identifies file content by hash, not by name, which is exactly why renaming a file's contents unchanged shows up differently from editing its contents.

## 5. Branches: Working Without Disturbing the Main Line

A **branch** is a movable pointer to a specific commit — nothing more exotic than that under the hood. When you commit, the branch you're currently "on" moves forward to point at the new commit. Every repository starts with one branch, `main`, by default (you saw `On branch main` in every `git status` output in Introduction, without it being explained yet).

**Why branches matter:** they let you start work on something — a new feature, a risky experiment, a fix — from the current state of `main`, without touching `main` itself until you're ready. If the experiment fails, you simply stop using that branch; `main` was never affected.

```bash
git branch feature-login
git switch feature-login
```

```
Switched to branch 'feature-login'
```

**What actually happened:** `git branch feature-login` created a new pointer, `feature-login`, at the exact commit `main` currently points to — no new commit, no files changed, just a new named pointer sitting right next to `main`. `git switch feature-login` changed which pointer you're currently working from. Commits you make now move `feature-login` forward; `main` stays exactly where it was.

**A shortcut worth knowing:** `git switch -c feature-login` does both steps — create and switch — in one command (`-c` for "create").

**Merging** brings a branch's work back into another branch:

```bash
git switch main
git merge feature-login
```

```
Updating 8f3a1c2..4b7e9a1
Fast-forward
 notes.py | 1 +
 1 file changed, 1 insertion(+)
```

**"Fast-forward"** is the simple case: `main` hadn't moved at all since `feature-login` branched off, so Git just moves `main`'s pointer forward to match — no real merging of conflicting content required.

## 6. Merge Conflicts

A **merge conflict** happens when Git tries to combine two branches that both changed the *same lines* of the *same file* in different ways, and Git genuinely cannot decide which version you want. This is not a bug or a sign you did something wrong — it's the expected result of two people (or two branches) editing the same spot independently, and Git correctly refusing to silently pick a winner.

When it happens, Git marks the conflicting section directly inside the file itself:

```
<<<<<<< HEAD
print("hello from main")
=======
print("hello from feature-login")
>>>>>>> feature-login
```

**How to read this:** everything between `<<<<<<< HEAD` and `=======` is what's currently on your branch (`HEAD` means "the commit you're currently on"); everything between `=======` and `>>>>>>> feature-login` is what's coming in from the branch you're merging. Resolving a conflict means editing the file to what it *should* actually say, deleting the `<<<<<<<`/`=======`/`>>>>>>>` marker lines entirely, then staging and committing the result — Git treats a resolved conflict as a normal commit from that point on.

## 7. Ignoring Files: `.gitignore`

Not everything in a project folder belongs in version control. Python Programming's virtual environments, compiled `__pycache__` files, editor configuration, and (Hands-on Practice covers this specifically) anything containing a real secret should never be committed at all — some because they're regenerable clutter, some because committing them is a genuine security mistake.

A `.gitignore` file, placed in your repository's root, lists patterns Git should never track, even if `git add .` (adding everything at once) is used:

```
__pycache__/
*.pyc
.env
venv/
```

**What each line does:** `__pycache__/` ignores that entire directory anywhere in the project; `*.pyc` ignores any file ending in `.pyc`, wherever it appears; `.env` and `venv/` ignore a specific file and directory by exact name. Once listed, `git status` stops showing these as untracked — they simply disappear from Git's view entirely, which is the intended behavior, not a bug to work around.

**The one case `.gitignore` does not cover:** a file that's already been committed. Adding a pattern to `.gitignore` only prevents *future* tracking — Hands-on Practice covers exactly why this distinction becomes a real security problem.

## 8. Remotes: Where GitHub Actually Enters the Picture

Everything so far in this module has been entirely local — one machine, no network. A **remote** is a stored reference to a copy of your repository that lives somewhere else — most commonly, on GitHub.

```bash
git remote add origin https://github.com/example-user/example-repo.git
git remote -v
```

```
origin  https://github.com/example-user/example-repo.git (fetch)
origin  https://github.com/example-user/example-repo.git (push)
```

**What this actually did:** it taught your local repository one fact — "there's another copy of this project at this URL, and I'll call it `origin`" — and nothing more. No files moved. `origin` is simply the conventional name for "the main remote copy," not a Git keyword; you could name it anything.

This is the precise mechanism behind Introduction's Git/GitHub distinction: **GitHub is just a server holding a Git repository that your local Git already knows how to talk to, using the exact same commit/branch/history model from this entire lesson.** `git push` (send your local commits to a remote) and `git pull` (bring a remote's new commits into your local repository) are the two commands that actually move data across that connection — Hands-on Practice walks through using them for real, against a real GitHub repository.

## 9. Common Mistakes

**Confusing `git diff` and `git diff --staged`.** Section 4's exact distinction — working-directory-vs-staged, or staged-vs-last-commit — is the single most common source of "wait, why isn't this change showing up" confusion in this lesson.

**Panicking at a merge conflict.** It's normal, expected behavior for two independent changes to the same line — not a sign that something broke. Section 6's marker syntax is the same in every conflict you'll ever see.

**Assuming `.gitignore` retroactively removes an already-tracked file.** It only stops *future* tracking. A file committed before being added to `.gitignore` stays in history regardless — Hands-on Practice explains exactly why that matters.

**Believing `git remote add` sends anything.** Like `git branch`, it only records information locally — no data moves until you explicitly `push` or `pull`.

## 10. Practice

**Exercise 1 — Guided.** Using Introduction's repository, edit `notes.py`, run `git diff`, then stage it and run `git diff` again. Explain in one sentence why the second `git diff` showed nothing.

**Exercise 2 — Independent.** Create a new branch, make a commit on it, switch back to `main`, and confirm (with `git log --oneline`) that `main`'s history doesn't include that commit.

**Exercise 3 — Reasoning.** Two branches both edited line 12 of the same file, differently. You run `git merge` and Git stops with a conflict. Without looking anything up, describe what you'd expect to see inside the affected file, using Section 6's marker syntax.

**Challenge.** Write a `.gitignore` that would correctly ignore a Python virtual environment folder named `.venv`, all `.pyc` files, and a local secrets file named `secrets.json`.

## 11. Knowledge Check

1. What's the exact difference between what `git diff` and `git diff --staged` each compare?
2. What is a branch, mechanically — what is Git actually creating when you run `git branch`?
3. Why is a merge conflict not a sign that something went wrong?
4. What does adding a file to `.gitignore` do, and what does it explicitly *not* do?
5. What is a remote, and what two commands actually move data across it?

## 12. Key Takeaways

- `git log` (and `git log --oneline`) reads committed history; `git diff` reads *uncommitted* changes — and which two states it compares depends on whether you add `--staged`.
- A branch is a lightweight, movable pointer to a commit — creating one is instant and doesn't duplicate any files.
- A merge conflict happens when two branches change the same lines differently; Git marks the conflict directly in the file with `<<<<<<<`/`=======`/`>>>>>>>` and expects you to resolve it manually.
- `.gitignore` prevents future tracking of matching files — it has no effect on anything already committed.
- A remote is just a recorded reference to another copy of the repository (commonly on GitHub); `git remote add` records the reference, `push`/`pull` are what actually move commits.

## 13. What's Next

**Hands-on Practice** puts a remote to real use: cloning an existing repository, understanding what GitHub adds on top of Git specifically (repositories, forks, pull requests, issues), and — critically for everything ahead of you on this platform — why committing a secret to a repository is a real, common, and serious security mistake, and what to actually do about it.
