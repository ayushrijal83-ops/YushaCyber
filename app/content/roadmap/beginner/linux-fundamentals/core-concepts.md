# Core Concepts: The Filesystem and Navigation

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what the filesystem hierarchy is and how it's organized
- tell the difference between an **absolute path** and a **relative path**, and know when to use each
- navigate between directories with `cd`, including into subdirectories, up to a parent, and home
- read a file's contents from the terminal with `cat`
- diagnose why a path-related command failed

## 2. Why This Matters

The previous lesson taught you to check *where* you are (`pwd`) and *what's there* (`ls`). This lesson teaches you to actually *move* and *look inside things* — the two abilities that turn a terminal from a curiosity into a tool. Every later mission on this platform — reading a log file, finding a config, dropping into a target's home directory during a lab — assumes you can navigate confidently and know exactly what a path like `../logs/auth.log` means without having to guess.

## 3. The Filesystem Hierarchy

Linux organizes every file and directory into a single tree, starting at one root, written `/`. Unlike Windows, there is no `C:\` or separate drive letters — external drives, USB sticks, and network shares all get attached ("mounted") somewhere *inside* this same tree, not as a new tree of their own.

Picture it as an upside-down tree: `/` is the root, and everything else — `/home`, `/etc`, `/var`, and every file you'll ever touch — is a branch or leaf hanging off it, directly or through several levels of subdirectories.

Your own files live under your **home directory**, at `/home/<username>` — for the `student` account used in this platform's labs, that's `/home/student`. This is the directory you land in when a new terminal session starts, and it's yours to read, write, and organize freely.

## 4. Absolute vs. Relative Paths

A path is just an address for a file or directory. There are two ways to write one:

**Absolute path** — starts with `/`, and describes the full location from the root of the filesystem, regardless of where you currently are:

```
/home/student/Documents/welcome.txt
```

This always points to the same file, no matter your current directory when you use it.

**Relative path** — does *not* start with `/`, and describes a location relative to your current directory:

```
Documents/welcome.txt
```

This only resolves correctly if you're currently standing in `/home/student`. Run the exact same relative path from `/home/student/Downloads` instead, and it points somewhere that doesn't exist (`/home/student/Downloads/Documents/welcome.txt`), because relative paths are always interpreted starting from wherever `pwd` currently says you are.

Two special symbols make relative paths more useful:

| Symbol | Meaning |
|---|---|
| `.` | The current directory |
| `..` | The parent directory (one level up) |
| `~` | Shorthand for your home directory (e.g. `~` = `/home/student`) |

So `../Downloads` means "go up one level from here, then into `Downloads`," and `~/Documents` means "my home directory, then into `Documents`" — usable from anywhere, since `~` always expands to your absolute home path.

**The rule of thumb:** if a path starts with `/` or `~`, it works from anywhere. If it doesn't, it only works from the right starting directory — and "the right starting directory" is exactly what `pwd` (previous lesson) tells you.

## 5. Navigating: `cd`

**What it does:** `cd` (**c**hange **d**irectory) moves your current working directory to a new one.

**Basic syntax:**

```bash
cd <path>
```

The path can be absolute or relative — `cd` accepts either.

**Example:**

```bash
pwd
```
```
/home/student
```
```bash
cd Documents
pwd
```
```
/home/student/Documents
```

**What happened:** `cd Documents` was a **relative** move — it worked because we were already in `/home/student`, so `Documents` correctly resolved to `/home/student/Documents`. Running `pwd` afterward confirms the move.

**Going back up:**

```bash
cd ..
pwd
```
```
/home/student
```

`cd ..` moved us up one level, back to the parent directory.

**Going home from anywhere:**

```bash
cd ~
```

or, with no argument at all:

```bash
cd
```

Both return you straight to your home directory, regardless of how deep you'd wandered.

**Common mistake:** Running `cd` with a relative path from the wrong location. If you're in `/home/student/Downloads` and run `cd Documents`, the shell looks for `/home/student/Downloads/Documents` — which doesn't exist — and reports an error, even though `/home/student/Documents` is real. This is the single most common navigation mistake, and the fix is always the same: run `pwd` first to confirm where you actually are before using a relative path.

**Debugging exercise.** Suppose you run:

```bash
cd /home/student/Documnts
```

and get:

```
bash: cd: /home/student/Documnts: No such file or directory
```

**Why did this fail?** Look closely at the spelling — `Documnts` is missing the second `e` (it should be `Documents`). The shell does not correct typos or guess your intent; it looks for an exact, case-sensitive match and reports failure if nothing exists at that exact path. Reading error messages carefully, character by character, is a real skill — most "broken" commands on this platform (and in real Linux use) turn out to be exactly this.

**Safe exercise:** From your home directory, use `cd` to enter `Documents`, confirm your location with `pwd`, then use `cd ..` to return home.

## 6. Reading a File: `cat`

**What it does:** `cat` ("con**cat**enate") prints a file's entire contents straight to the terminal. For a single small file, that's effectively "show me what's inside."

**Basic syntax:**

```bash
cat <path>
```

**Example:**

```bash
cd ~/Documents
cat welcome.txt
```

**Expected output:**

```
Welcome to YushaCyber!
You're learning Linux. Keep going!
```

**What the output means:** Everything printed is the literal content of `welcome.txt` — nothing is summarized or truncated. `cat` doesn't care about file type; it just dumps bytes to your screen and lets your terminal render them as text.

**Common mistake:** Running `cat` on a very large file (megabytes of text, or worse, a binary file like an image) floods your terminal with output, some of which may render as garbled characters or even affect your terminal's display. `cat` is for looking at *small* text files. Later in this platform you'll meet tools built for larger files, but for now, stick to short files you already expect to be readable text.

**Another common mistake:** Forgetting you moved directories. If `cat welcome.txt` reports "No such file or directory," the file most likely isn't missing — you're probably not in `/home/student/Documents` anymore. `pwd` first, always.

## 7. Practice

Work through these in the YushaCyber terminal, in order:

**Exercise 1 — Guided.** Run `pwd` to confirm you're in `/home/student`. Then `cd Documents`, then `pwd` again to confirm the move.

**Exercise 2 — Independent.** From inside `Documents`, use a *relative* path to move back up to your home directory, without typing `cd ~` or `cd` alone. (Hint: Section 4's special symbols.)

**Exercise 3 — Reasoning.** You're currently in `/home/student`. Without running anything, predict what `cat Documents/welcome.txt` would print, and why it works as a relative path from exactly this location.

**Challenge.** From your home directory, in a single line using `&&` is not required — just get there in as few commands as you can: navigate into `Documents`, read `welcome.txt`, then return home and confirm your location.

## 8. Practical Relevance

Reading files from a specific, correct path is not a toy skill — it's what you'll do to read a web server's access log at `/var/log`, a target's SSH keys during a lab, or a configuration file while investigating a misconfiguration. The path discipline built here (know where you are, know whether your path is absolute or relative) is the same discipline that keeps you oriented six months from now in a much more complex environment.

## 9. Knowledge Check

1. What is the difference between an absolute path and a relative path?
2. What does `cd ..` do, and how is it different from `cd ~`?
3. If you're in `/home/student/Downloads` and run `cd Documents`, why might this fail?
4. What does `cat` do, and what kind of file is it well-suited for?
5. What does the shell do when a path you gave it doesn't exist — does it guess, or report an error?

## 10. Key Takeaways

- The filesystem is one tree rooted at `/`; your home directory (`/home/student`) is where your own files live.
- Absolute paths (starting with `/` or `~`) work from anywhere; relative paths depend entirely on your current directory.
- `cd` changes your current directory; `cd ..` goes up one level, `cd ~` (or plain `cd`) goes home.
- `cat` prints a file's full contents — useful for small text files, not for large or binary ones.
- Most "broken" path commands are really typos or a wrong assumption about your current directory — `pwd` is always the first debugging step.

## 11. What's Next

**Hands-on Practice** puts navigation to work: you'll create, copy, move, and delete files and directories, learn to read and change file permissions, and finish with a guided run through the platform's Linux Basics terminal mission.
