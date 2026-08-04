# Interactive Cyber Labs — Browser Lab Engine

## Architecture

```
app/lab_engine/
├── filesystem.py  ← VirtualFS — in-memory file tree (no real OS access)
├── terminal.py    ← Terminal — command parser for Linux + Windows
├── objectives.py  ← LabDefinition + Objective dataclasses
├── validator.py   ← Validates commands/answers/files against objectives
├── progress.py    ← LabProgress — completion tracking
├── simulator.py   ← LabSimulator — orchestrates session
├── state.py       ← Save/load/reset session state
├── models.py      ← Built-in sample labs (linux-basics, log-analysis, windows-basics)
├── services.py    ← Public API: start_lab, execute_command, submit_answer, reset_lab
└── routes.py      ← REST API under /api/lab-engine/
```

## Simulation Design

Everything runs in-memory. The VirtualFS holds a dict tree, the Terminal
parses commands against it. No real shell, no OS access, no subprocess calls.

### Linux commands (15)
ls, pwd, cd, cat, grep, find, chmod, mkdir, rm, cp, mv, echo, history, clear, whoami

### Windows commands (11)
dir, cd, type, copy, move, tree, findstr, ipconfig, whoami, cls, mkdir, echo

## Validation

3 types: `command` (exact/partial match), `answer` (text comparison),
`file` (existence check). Auto-validates after every command.

## Lab Lifecycle

1. `start_lab(user_id, slug)` → creates LabSimulator
2. `execute_command(user_id, slug, "pwd")` → runs command, auto-validates
3. Auto-saved after every command
4. `reset_lab(user_id, slug)` → fresh start

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/lab-engine/labs` | GET | List available labs |
| `/api/lab-engine/start` | POST | Start/resume lab |
| `/api/lab-engine/execute` | POST | Run terminal command |
| `/api/lab-engine/answer` | POST | Submit text answer |
| `/api/lab-engine/reset` | POST | Reset lab |
| `/api/lab-engine/session/<slug>` | GET | Current session state |

## Security

- No real shell access — commands parsed by Terminal class
- No subprocess, no os.system, no eval
- VirtualFS never touches real filesystem
- Command length limited to 500 chars
- CSRF exempt (JSON API)

## Extension

Add new labs in `models.py`: create a `LabDefinition` with objectives,
an optional custom filesystem tree, and add it to `SAMPLE_LABS`.
