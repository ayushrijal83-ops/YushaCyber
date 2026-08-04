"""Lab engine models — built-in sample lab definitions."""

from __future__ import annotations

from app.lab_engine.objectives import LabDefinition, Objective

SAMPLE_LABS: dict[str, LabDefinition] = {
    "linux-basics": LabDefinition(
        slug="linux-basics",
        title="Linux Command Line Basics",
        description="Learn essential Linux commands.",
        mode="linux", difficulty="Easy", category="linux",
        xp_total=200,
        intro_text="Welcome to the Linux terminal! Complete each objective.",
        objectives=[
            Objective(id="lb-1", title="Find your location",
                      description="Use the command that shows your current directory.",
                      hint="Try 'pwd'.",
                      validation_type="command", expected="pwd",
                      xp=25, order=1),
            Objective(id="lb-2", title="List files",
                      description="List the contents of the current directory.",
                      hint="Use 'ls'.",
                      validation_type="command", expected="ls",
                      xp=25, order=2),
            Objective(id="lb-3", title="Read a file",
                      description="Read the contents of notes.txt.",
                      hint="Use 'cat notes.txt'.",
                      validation_type="command", expected="cat notes.txt",
                      xp=25, order=3),
            Objective(id="lb-4", title="Create a directory",
                      description="Create a directory called 'evidence'.",
                      hint="Use 'mkdir evidence'.",
                      validation_type="command", expected="mkdir evidence",
                      xp=25, order=4),
        ],
    ),
    "log-analysis": LabDefinition(
        slug="log-analysis",
        title="Log Analysis Fundamentals",
        description="Analyze system logs to find suspicious activity.",
        mode="linux", difficulty="Medium", category="soc",
        xp_total=300,
        intro_text="Examine the logs in /var/log/ for suspicious entries.",
        objectives=[
            Objective(id="la-1", title="View the syslog",
                      description="Read the system log file.",
                      hint="Try 'cat /var/log/syslog'.",
                      validation_type="command",
                      expected="cat /var/log/syslog",
                      xp=50, order=1),
            Objective(id="la-2", title="Search for SSH activity",
                      description="Find SSH-related entries in the log.",
                      hint="Use grep with 'sshd'.",
                      validation_type="command",
                      expected="grep sshd /var/log/syslog",
                      xp=75, order=2),
        ],
    ),
    "windows-basics": LabDefinition(
        slug="windows-basics",
        title="Windows Command Prompt Basics",
        description="Learn essential Windows commands.",
        mode="windows", difficulty="Easy", category="windows",
        xp_total=150,
        intro_text="Welcome to the Windows command prompt.",
        objectives=[
            Objective(id="wb-1", title="List directory",
                      description="List files in the current directory.",
                      hint="Use 'dir'.",
                      validation_type="command", expected="dir",
                      xp=25, order=1),
            Objective(id="wb-2", title="Who are you?",
                      description="Find out your username.",
                      hint="Use 'whoami'.",
                      validation_type="command", expected="whoami",
                      xp=25, order=2),
        ],
    ),
}


def get_lab(slug: str) -> LabDefinition | None:
    return SAMPLE_LABS.get(slug)


def list_labs() -> list[dict]:
    return [lab.to_dict() for lab in SAMPLE_LABS.values()]
