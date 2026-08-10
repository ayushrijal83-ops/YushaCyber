# Introduction to Linux

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain the difference between a **terminal**, a **shell**, a **command**, and a **program**
- run `pwd` and explain exactly what its output means
- run `ls` (and `ls -la`) and read the result
- explain why hidden files exist and how to see them
- recognize the four most important top-level directories on a Linux system

## 2. Why This Matters

Most servers on the internet run Linux. Most security tools — `nmap`, `Wireshark`, Metasploit, Burp Suite — either run on Linux or were built assuming a Linux-style terminal. Every lab, mission, and CTF challenge later in this platform drops you into a Linux shell and expects you to already be comfortable there. This lesson is that starting point: not trivia about Linux, but the handful of commands and mental models you will use in literally every session from here on.

## 3. Terminal, Shell, Command, Program — Four Different Things

These four words get used interchangeably by beginners, but they mean different things, and the distinction matters once you start troubleshooting:

| Term | What it actually is |
|---|---|
| **Terminal** | The window/program that displays text and lets you type. It's just a text window — it doesn't interpret anything itself. |
| **Shell** | The program that *reads* what you type and runs it. Bash is the most common Linux shell. The terminal shows you the shell's output. |
| **Command** | A specific instruction you type, like `pwd` or `ls`. |
| **Program** | The actual executable file the shell runs when you type a command. `ls` is a command *and* the name of the program it invokes. |

Think of it this way: the **terminal** is the room, the **shell** is the person listening to you in that room, a **command** is a sentence you say, and a **program** is the thing that actually goes and does the work once the shell understands your sentence. When something goes wrong later — "command not found," a script that "works in one terminal but not another" — this distinction is usually the reason why, so it's worth having it straight now, even though it will feel abstract until you've typed a few commands.

## 4. Your First Command: `pwd`

**What it does:** `pwd` stands for **p**rint **w**orking **d**irectory. Every terminal session has a *current working directory* — the folder you're "standing in" right now, even though there's no visual folder icon to look at. `pwd` tells you where that is.

**Why it matters:** Unlike a graphical file browser, the terminal gives you no visual cues about your location in the filesystem. If you don't know your current directory, a command like `ls` or `cat somefile.txt` might succeed or fail depending on where you are, with no obvious reason why. Checking your location with `pwd` is the single most useful habit for staying oriented.

**Basic syntax:**

```bash
pwd
```

`pwd` takes no arguments in normal use — you just run it by itself.

**Example:**

```bash
pwd
```

**Expected output:**

```
/home/student
```

**What the output means:** You are currently in `/home/student` — the home directory belonging to the user `student`. The leading `/` means this is an **absolute path**: a full address starting from the very top of the filesystem, not a location relative to anywhere else. You'll build on absolute vs. relative paths in the next lesson.

**Common mistake:** Typing `PWD` (capital letters) or `Pwd`. Linux commands are case-sensitive — `PWD` is a different, nonexistent command as far as the shell is concerned, and you'll get a "command not found" error.

**Safe exercise:** In the YushaCyber terminal, run `pwd` right now and confirm you see a path starting with `/home/`.

## 5. Who Am I? `whoami`

**What it does:** `whoami` prints the username of the account you're currently operating as.

**Why it matters:** On a shared system, or after using `sudo` to switch privileges, it's easy to lose track of which user you actually are. Security work in particular cares a lot about *which account* is running a command — a command run as `root` behaves very differently from the same command run as an ordinary user.

**Example and output:**

```bash
whoami
```
```
student
```

That's it — one line, no options, no arguments. Small commands like this are common in Linux; not everything needs a flag or a manual page.

## 6. Listing Files: `ls`

**What it does:** `ls` lists the contents of a directory — by default, your current one.

**Basic syntax:**

```bash
ls [options] [path]
```

Both `[options]` and `[path]` are optional. Running plain `ls` lists the current directory.

**Important options:**

| Option | Effect |
|---|---|
| `-l` | "Long" format — one entry per line, with permissions, owner, size, and modification date |
| `-a` | "All" — also show **hidden files** (see below) |
| `-la` | Both combined — the long format, including hidden files |

**Example:**

```bash
ls -la /home
```

**Expected output (shape, not exact bytes):**

```
drwxr-xr-x  3 root    root    4096 Jan 10 09:00 .
drwxr-xr-x 18 root    root    4096 Jan 10 08:55 ..
drwxr-x---  4 student student 4096 Jan 10 09:12 student
```

**What the output means:** Each line is one entry in `/home`. The first character (`d`) tells you it's a directory, not a plain file. The next nine characters (`rwxr-xr-x`) are its **permissions** — you'll learn to read these fully in the Hands-on Practice lesson. The two names, owner and group (`root`, `root`), tell you who owns the entry. The size and date come next, and the name is last. Notice the first two lines: `.` and `..` — these are always present and are explained next.

**Hidden files.** Any file or directory whose name starts with a dot (`.`) is "hidden" — plain `ls` skips it, but it is not secret, encrypted, or inaccessible. It's a simple display convention, mostly used for configuration files that clutter a directory listing if always shown (like `.bashrc`, a shell configuration file). `ls -a` reveals them. A common beginner misconception is that a dot-prefixed file is somehow protected — it isn't. Anyone with normal read access can view it exactly like any other file.

**Common mistake:** Running `ls -la` and being confused by the `.` and `..` entries appearing as if they were real files you created. They aren't new files — `.` always refers to "this directory" and `..` always refers to "the parent directory." Every directory on the system has both.

**Safe exercise:** Run `ls` in your home directory, then run `ls -la`. Compare the two outputs and identify at least one hidden file that only appeared the second time.

## 7. Common Top-Level Directories

Linux organizes the entire filesystem as one tree starting at `/` (the root directory — unrelated to the `root` user, though the naming overlap trips people up). A few directories you'll see constantly:

| Path | Purpose |
|---|---|
| `/` | The root of the entire filesystem — everything else lives under it |
| `/home` | Contains each regular user's personal directory (e.g. `/home/student`) |
| `/etc` | System-wide configuration files |
| `/var` | Variable data that changes over time — most importantly, logs (`/var/log`) |

You don't need to memorize the whole filesystem layout today — you'll get hands-on with navigating it in the next lesson. For now, just recognize these four when you see them.

## 8. Common Mistakes

**Confusing the shell with the terminal.** If someone says "open a new shell," they usually mean "open a new terminal window" — in casual use the two get blended, but remember the terminal is the window and the shell is the interpreter running inside it.

**Assuming hidden files are secure.** As covered above, a leading dot only hides a file from a plain `ls` — it provides no actual protection.

**Typing commands with the wrong case.** `PWD`, `Ls`, and `WHOAMI` are not the same as `pwd`, `ls`, and `whoami` to the shell.

**Expecting output when there's an error.** If you mistype a command entirely (e.g. `pwdd`), the shell won't guess what you meant — it reports `command not found` and does nothing further. That's expected behavior, not a bug.

## 9. Practice

In the YushaCyber terminal:

1. Run `pwd` and note your current directory.
2. Run `whoami` and note your username.
3. Run `ls`, then run `ls -la`, and compare what each shows you.
4. Find at least one hidden file in the output of `ls -la` and name it.

## 10. Knowledge Check

1. What is the difference between a terminal and a shell?
2. What does `pwd` actually tell you?
3. What does a leading dot (`.`) in a filename mean, and what does it *not* mean?
4. What is the difference between what `ls` and `ls -la` show you?
5. What does `/etc` typically contain?

## 11. Key Takeaways

- The terminal displays text; the shell interprets your commands; a command names what to run; a program is what actually runs.
- `pwd` prints your current working directory — your one reliable way to know where you are in a terminal.
- `ls` lists a directory's contents; `-a` reveals hidden (dot-prefixed) files, and `-l` shows permissions, ownership, size, and date.
- Hidden files are a display convention, not a security feature.
- `/`, `/home`, `/etc`, and `/var` are directories you'll see constantly — you don't need the whole map yet.

## 12. What's Next

**Core Concepts** builds directly on this: you'll learn how to actually move around the filesystem (`cd`), the difference between absolute and relative paths, and how to read a file's contents from the terminal.
