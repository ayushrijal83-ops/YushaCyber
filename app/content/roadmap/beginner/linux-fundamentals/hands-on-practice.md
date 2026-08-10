# Hands-on Practice: Files, Permissions, and Your First Mission

## 1. What You Will Learn

By the end of this lesson you should be able to:

- create files and directories with `touch` and `mkdir`
- copy and move files with `cp` and `mv`
- delete files and directories with `rm` — and explain why it's more dangerous than a graphical recycle bin
- read a permission string like `rwxr-xr-x` and explain what each character means
- change permissions with `chmod`, using both symbolic and numeric notation
- complete the platform's Linux Basics terminal mission using exactly what you've learned in this module

This is the longest lesson in the module for a reason: Introduction gave you your bearings, Core Concepts taught you to move around and read files — this lesson is where you start *changing* the filesystem, which is both more useful and more capable of causing real damage if done carelessly.

## 2. Why This Matters

Every script, every lab, and every real Linux system you'll ever touch requires creating, moving, and cleaning up files, and controlling exactly who can read, write, or run them. Permissions in particular are a security topic disguised as a filesystem topic: a huge number of real-world breaches trace back to a file or service that was more permissive than it should have been. Understanding `rwx` here is the foundation for two much bigger topics later in this platform — least privilege, and privilege escalation.

## 3. Creating Files and Directories

**`touch` — create an empty file (or update an existing one's timestamp).**

```bash
touch notes.txt
```

There's no output on success — in Linux, "silence is success" is a common pattern; a command that completes without printing anything usually means it worked. Run `ls` afterward to confirm `notes.txt` now exists, with 0 bytes of content.

**`mkdir` — make a directory.**

```bash
mkdir practice
```

Same idea: silent success. `ls` afterward shows `practice` as a new directory (and `ls -l` would show a `d` as the first character of its permissions, as covered in the Introduction lesson).

**Common mistake:** Trying to `touch` a file inside a directory that doesn't exist yet (e.g. `touch newfolder/file.txt` before `newfolder` exists) fails with "No such file or directory" — `touch` creates files, not the directories that would contain them.

## 4. Copying and Moving

**`cp` — copy a file.**

```bash
cp notes.txt notes-backup.txt
```

This creates `notes-backup.txt` as an independent copy — editing one afterward does not affect the other. To copy an entire directory (not just a single file), add `-r` (recursive), since `cp` alone refuses to copy a directory:

```bash
cp -r practice practice-backup
```

**`mv` — move (or rename) a file.**

```bash
mv notes-backup.txt archive.txt
```

`mv` is also how you rename something — Linux doesn't have a separate "rename" command, because moving a file to a new name in the same directory *is* a rename. Unlike `cp`, `mv` doesn't leave the original behind.

**Common mistake:** Both `cp` and `mv` overwrite an existing destination file **without asking for confirmation** by default. If `archive.txt` already existed before that `mv` command ran, it would be silently replaced — this is a common way people lose work, and it's exactly why the next section matters.

## 5. Deleting: `rm`

**What it does:** `rm` removes a file. With `-r`, it removes a directory and everything inside it, recursively.

```bash
rm notes.txt
rm -r practice-backup
```

**Why this is different from a graphical trash bin — and why that matters.** On a desktop, deleting a file usually moves it to a Recycle Bin or Trash folder, recoverable with a couple of clicks. `rm` does not do this. By default, there is no undo, no trash folder, and no confirmation prompt. Once `rm` completes, the data is gone as far as the shell is concerned. This is the single most consequential difference between a terminal and a graphical file manager for a beginner to internalize.

The danger compounds with `-r`: `rm -r somedirectory` deletes that directory and every file and subdirectory inside it, permanently, in one command, with no per-file confirmation. A mistyped path with `rm -r` is one of the most common real-world "I just deleted the wrong thing" stories in all of computing.

**How to stay safe while you're still learning:**
- Always double-check the exact path with `pwd` and `ls` *before* running `rm`, especially with `-r`.
- Never practice destructive commands like `rm -r` against anything except this training environment.
- If you're ever unsure exactly what a command will delete, stop and re-read it before pressing enter — `rm` does not pause to ask if you're sure.

**Common mistake:** Confusing `rm file.txt` (deletes one file) with `rm -r folder` (deletes a whole directory tree) and using the wrong one — either deleting far more than intended, or getting an "Is a directory" error when trying to `rm` a directory without `-r`.

## 6. Reading Permissions

Recall from the Introduction lesson that `ls -l` shows a permission string like `rwxr-xr-x` at the start of each line. Now let's actually read it.

The string breaks into four parts:

```
d rwx r-x r-x
│  │   │   │
│  │   │   └── other (everyone else)
│  │   └────── group (users in the file's group)
│  └────────── owner (the user who owns the file)
└───────────── entry type (d = directory, - = regular file)
```

Each three-character group represents the same three permissions, in the same order, for a different category of user:

| Letter | Meaning for a file | Meaning for a directory |
|---|---|---|
| `r` | read the file's contents | list the directory's contents |
| `w` | modify the file's contents | create/delete entries inside it |
| `x` | execute the file as a program/script | enter the directory with `cd` |

A `-` in any position means that permission is **not** granted. So `rwxr-xr-x` reads as: the owner can read, write, and execute; the group can read and execute but not write; everyone else can also read and execute but not write.

**Why the `x` bit on a directory is confusing at first:** a directory's `x` doesn't mean "run it" (directories aren't programs) — it means "you're allowed to `cd` into it or access files inside it by name." A directory with `r` but not `x` lets you list what's inside, but not actually enter or open any of it. This distinction trips up almost everyone the first time they see it.

## 7. Changing Permissions: `chmod`

**What it does:** `chmod` (**ch**ange **mod**e) sets a file or directory's permissions. There are two ways to specify what you want.

**Symbolic notation** — add or remove a specific permission for a specific category:

```bash
chmod u+x script.sh
```

This reads as "for the **u**ser (owner), **add** the e**x**ecute permission." Other combinations follow the same pattern: `g-w` (remove write from group), `o+r` (add read for others), `a+x` (add execute for everyone — **a**ll).

**Numeric notation** — set all three categories at once using one number per category, where each permission has a fixed value: `r = 4`, `w = 2`, `x = 1`. You add the values you want for each category:

```bash
chmod 755 script.sh
```

Breaking `755` down digit by digit:

| Digit | Category | Sum | Meaning |
|---|---|---|---|
| `7` | owner | 4+2+1 | read + write + execute |
| `5` | group | 4+0+1 | read + execute (no write) |
| `5` | other | 4+0+1 | read + execute (no write) |

This is exactly the `rwxr-xr-x` string from Section 6 — `755` and `rwxr-xr-x` describe the identical permission set, just in two different notations. A few numeric permission sets you'll see constantly:

| Numeric | Symbolic | Typical use |
|---|---|---|
| `644` | `rw-r--r--` | An ordinary file: owner can edit, everyone else can only read |
| `755` | `rwxr-xr-x` | A script or program: owner can edit and run it, everyone else can run but not edit it |
| `600` | `rw-------` | A private file (like an SSH key): only the owner can read or write it at all |

**Common mistake:** Setting a permission far broader than needed — for example, `chmod 777` (read, write, *and* execute for absolutely everyone) "to make an error go away." This is almost never the correct fix, and it's a textbook example of a real misconfiguration: a world-writable file or script means literally any user or process on the system can modify it, which is exactly the kind of gap that turns a minor bug into a serious security incident.

## 8. Why This Matters for Security

Permissions are how Linux enforces the principle of **least privilege** — giving each user and process only the access it actually needs, nothing more. A web server process that only needs to *read* its own files but is accidentally given write access to system directories is a real, common source of vulnerabilities: if that process is ever compromised, an attacker inherits whatever access it had. Later in this platform (Linux Privilege Escalation, in the Intermediate track) you'll learn how attackers specifically hunt for permission mistakes like an overly-permissive file or a misconfigured `sudo` rule — but that's an *exploitation* topic for later. Today's goal is simpler and comes first: understand what permissions mean and set them correctly, so you can recognize when something looks wrong.

## 9. Common Mistakes (Recap)

- **Assuming `rm` has an undo.** It doesn't — verify the path before running it, every time.
- **Forgetting `-r` for directories** with `cp` or `rm`, resulting in an unexpected error instead of the intended action.
- **Misreading the `x` bit on directories** as "executable" instead of "enterable."
- **Over-granting permissions** (`chmod 777`) as a shortcut past a permission error, instead of granting exactly what's needed.
- **Confusing owner, group, and other** — remember the string always reads owner, then group, then other, left to right.

## 10. Practice

**Exercise 1 — Guided.** Create a file called `draft.txt` with `touch`, then use `ls -l` to confirm it exists and note its default permissions.

**Exercise 2 — Independent.** Make a copy of `draft.txt` called `draft-backup.txt`, then delete the original `draft.txt` with `rm`. Confirm with `ls` that only the backup remains.

**Exercise 3 — Reasoning.** A file shows permissions `rw-r--r--`. Without running anything, answer: can the file's owner execute it? Can anyone in the file's group modify it?

**Challenge.** Create a directory called `scripts`, create an empty file inside it called `run.sh`, then use `chmod` to give the owner execute permission on `run.sh` without changing anything else about its permissions (hint: Section 7's symbolic notation is built for exactly this).

## 11. Capstone: The Linux Basics Mission

Everything in this module — navigation, reading files, creating and managing files, and the beginning of permissions — comes together in the platform's **Linux Basics** terminal mission. It's a structured, scored version of exactly what you've been practicing, on a simulated filesystem with its own `student` home directory:

1. Find your current directory (`pwd`)
2. List the files there (`ls`)
3. List *all* files, including hidden ones (`ls -la`)
4. Navigate into `Documents` (`cd Documents`)
5. Read `welcome.txt` (`cat welcome.txt`)
6. Create `notes.txt`
7. Create a `practice` directory
8. Review your command history (`history` — prints the list of commands you've run this session, in order)

Open the mission from the link below and work through it using the commands from this module. You'll earn XP for each objective, and it directly reinforces every command covered so far — this is the "practice" half of the lesson → practice → mission loop this whole roadmap is built around.

## 12. Knowledge Check

1. Why is `rm` more dangerous than deleting a file in a graphical file manager?
2. What does `-r` do when added to `cp` or `rm`?
3. In the permission string `rwxr-xr-x`, which characters apply to the file's group?
4. What do the numbers in `chmod 644` correspond to, and what do the individual digits 6 and 4 mean?
5. Why is `chmod 777` usually the wrong fix for a permission error?

## 13. Key Takeaways

- `touch` and `mkdir` create files and directories; `cp` and `mv` copy and move them; `rm` deletes them — permanently, with no built-in undo.
- Always confirm your path with `pwd`/`ls` before a destructive command, especially `rm -r`.
- A permission string has four parts: entry type, then owner/group/other, each as an `rwx` triplet.
- `chmod` sets permissions either symbolically (`u+x`) or numerically (`755`), and the two notations describe the exact same thing.
- Least privilege — granting only the access actually needed — is a security principle you now understand at the filesystem level, and you'll see it again in Linux Privilege Escalation.

## 14. What's Next

This is the last lesson in Linux Fundamentals — you now have real terminal fluency: navigation, file management, and the basics of permissions. The roadmap's next module, **Computer Networking**, shifts focus to how machines talk to each other — you'll keep using the Linux terminal skills from this module constantly as you go, since every networking tool you're about to learn is run from exactly this same shell.
