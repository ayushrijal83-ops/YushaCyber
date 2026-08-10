# Introduction to Python

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what Python is and why it's an interpreted language
- run Python two different ways: the REPL and a script file
- write a script that uses `print()`, comments, and basic expressions
- explain why indentation is not optional in Python
- read a simple Python error message and identify what went wrong

## 2. Why This Matters

Every tool you'll use later in this roadmap — network scanners you script yourself, log parsers, automation for repetitive security checks — is either written in Python or scriptable through it. Before any of that is useful, you need to be able to reliably do one thing: write a few lines of Python, run them, and understand what happened. This lesson is entirely about that one skill.

## 3. Core Concept: What Python Actually Is

Python is an **interpreted** language. That word matters, so here's the mental model:

A language like C gets **compiled**: a separate program (a compiler) translates your entire source file into machine code *before* it runs. You get an executable, and that's what actually runs.

Python skips that step. The **Python interpreter** reads your code and executes it directly, line by line, translating each piece into instructions as it goes. There's no separate "build" step — you write code, you run it, it executes immediately.

This has a practical consequence you'll feel right away: Python won't discover an error in line 40 until it actually reaches line 40. If lines 1–39 ran fine, they already had their effects (printed output, changed files, sent something over the network) before the program crashes. A compiled language would have refused to produce an executable at all if line 40 had a syntax error. Python doesn't get that chance to warn you up front — that's part of what makes testing your code as you go a real habit worth building, not a suggestion.

## 4. Running Python

There are two ways you'll run Python in this course, and they serve different purposes.

**The REPL** (Read-Eval-Print Loop) is an interactive session. You type one line, press Enter, and Python evaluates it immediately and shows you the result. It's for quick experiments — checking how something behaves, not for anything you want to save or run again. You'd start it from a terminal with the `python` command and get a prompt like this:

```
>>> 2 + 2
4
>>> print("hello")
hello
```

**A script file** is a plain text file (conventionally ending in `.py`) containing a sequence of statements. You run the whole file at once, and it executes top to bottom. This is what you'll actually build things with — the lessons after this one, and every lab that uses Python, work this way.

### Statements vs. expressions

An **expression** is anything that produces a value: `2 + 2`, `"hello"`, `len("cat")`. On its own, in the REPL, Python shows you that value. In a script, an expression that isn't used for anything (not printed, not assigned) just evaluates and its result is silently discarded.

A **statement** is a full instruction — it does something, but doesn't necessarily produce a value you can use. `print("hello")` is a statement that happens to contain an expression (`"hello"`) as its argument. Assigning a variable (`x = 5`) is a statement, not an expression — in Python, you can't do something like `print(x = 5)` and expect it to print `5`, because `x = 5` doesn't evaluate to a value the way `2 + 2` does.

### Indentation is syntax, not style

In most languages, whitespace at the start of a line is a formatting choice. In Python, it's part of the grammar. Python uses indentation to know which lines belong to which block — there are no `{ }` braces marking the start and end of a block of code. You'll feel the real weight of this in the next lessons, once you're writing `if` statements and loops that have a body. For now, the rule to internalize is simple: **lines that are meant to run together must be indented by the same amount**, and Python (via `IndentationError`) will refuse to run code where that's ambiguous or inconsistent.

### Comments

Anything after a `#` on a line is a comment — the interpreter ignores it entirely. Comments exist for the next human who reads the code, which is very often you, three weeks from now, having forgotten why you wrote something a particular way.

```python
# This is a comment. Python skips this whole line.
print("This line actually runs.")  # so does this line, up to the #
```

## 5. Examples

Start with the smallest possible program:

```python
print("Hello, world!")
```

`print` is a **function** — a named, reusable piece of behavior. You *call* it by writing its name followed by parentheses containing whatever you want to give it. Here, you're giving it one piece of data: the text `"Hello, world!"`. The function's job is to display whatever you pass it.

Now something with an expression:

```python
print(2 + 2)
```

Python evaluates `2 + 2` first (getting `4`), then passes that result to `print`, which displays `4`. The addition happens *before* the printing — Python always finishes evaluating an expression down to its final value before doing anything with that value.

Now put a few lines together, the way a real (tiny) script looks:

```python
# A short script that introduces itself
print("Starting up...")
print("2 + 2 is:")
print(2 + 2)
print("Done.")
```

Run this as a file and you'd see:

```
Starting up...
2 + 2 is:
4
Done.
```

Each `print()` call runs in order, top to bottom — this is the "line by line" execution from Section 3, made visible.

## 6. Common Mistakes

**Forgetting the parentheses.** `print "hello"` (no parentheses) is not valid Python 3 — it's a leftover habit from Python 2. `print` is a function; calling it always requires `()`.

**Mismatched quotes.** `print("hello')` — starting with a double quote and ending with a single quote — produces a `SyntaxError`. Python needs the opening and closing quote characters to match.

**Inconsistent indentation.** Mixing tabs and spaces, or indenting a line by a different amount than its neighbors when they're meant to be in the same block, raises an `IndentationError`. Pick spaces (4 is the near-universal convention) and stay consistent — most editors can be configured to insert spaces automatically when you press Tab.

**Misreading the error location.** When Python reports an error, it tells you *where it noticed the problem*, which is sometimes one line after where you actually made the mistake — a missing closing parenthesis is a classic example, since Python doesn't know it's missing until it hits something that doesn't fit. If a line looks completely correct, check the line above it too.

## 7. Practical Relevance

You won't write anything security-specific yet — that comes once you have real building blocks (the next two lessons). But every log parser, every "check these 200 hosts and tell me which ones are misconfigured" script, every proof-of-concept you'll eventually write starts exactly like this: as a plain script file, run top to bottom, built out of `print()` statements while you're figuring out whether your logic actually works. That habit — write a little, run it, look at the output — doesn't go away as the code gets more advanced. It's the whole workflow.

## 8. Practice

Open a new file named `intro.py` and write a script that:

1. Prints a line introducing what the script does (e.g. `"Temperature converter (demo)"`)
2. Prints the result of converting 100°C to Fahrenheit, using the formula `F = C * 9/5 + 32`, computed directly as an expression inside `print()` (don't worry about variables yet — that's next lesson)
3. Prints a closing line

Run it and confirm the printed Fahrenheit value is `212.0`.

## 9. Knowledge Check

1. What's the difference between the REPL and running a script file?
2. Why does Python only discover an error in line 40 after running lines 1–39?
3. What character starts a comment in Python?
4. What kind of error do you get from inconsistent indentation?
5. Is `2 + 2` a statement or an expression? What about `print(2 + 2)`?

## 10. Key Takeaways

- Python is interpreted: code executes line by line, with no separate compile step.
- The REPL is for quick, throwaway checks; script files are for anything you want to keep and rerun.
- Indentation is part of Python's grammar, not a style preference.
- `print()` is how you make a value visible; without it (or an assignment), a computed value is discarded.
- Errors are reported where Python *notices* the problem, which is sometimes after where the mistake actually is.

## 11. What's Next

**Core Concepts** builds directly on this: you'll start storing values instead of just printing them once, using variables, and you'll meet Python's basic data types (numbers, text, booleans) and the operators that work on them.
