# Welcome to Linux Fundamentals

Linux powers most of the servers, containers, and security tools you'll ever touch. This lesson gets you comfortable at the **terminal**.

## Why Linux?

- It's *everywhere* — servers, embedded devices, phones
- It's transparent: you can inspect almost everything
- Security work assumes terminal fluency

> The command line rewards curiosity. Break things in a VM, not in production.

## Your first commands

Here's an inline snippet: type `whoami` to see your current user.

A fenced block:

```bash
# List files, including hidden ones
ls -la /home

# Who am I, and where?
whoami
pwd
```

## Common directories

| Path    | Purpose                      |
|---------|------------------------------|
| `/etc`  | System configuration         |
| `/home` | User home directories        |
| `/var`  | Logs and variable data       |

That's it for the intro — head to **Core Concepts** next.
