# Hands-on Practice: Conditions, Loops, and Functions

## 1. What You Will Learn

By the end of this lesson you should be able to:

- branch program behavior with `if` / `elif` / `else`
- combine conditions with `and`, `or`, and `not`
- repeat work with `for` and `while` loops, and control iteration with `break` and `continue`
- write your own function with parameters and a `return` value
- combine all three into one working script that takes input, makes decisions, and reports a result

This is the longest lesson in the module for a reason: variables and types (the previous lesson) are the *nouns* of Python; conditions, loops, and functions are the *verbs*. Once you have both, you can write programs that actually do something, not just calculate a single value once.

## 2. Why This Matters

Every script you'll write from here on needs at least one of these three tools, usually all of them: decide something based on a value (`if`), repeat something until you're done (`for`/`while`), and package a piece of logic so you can reuse it without retyping it (`def`). A port scanner loops over ports and decides which are open. A log parser loops over lines and decides which match a pattern. This lesson is where Python stops being a calculator and starts being a programming language.

## 3. Conditions: Making Decisions

An `if` statement runs a block of code only when a condition is `True`:

```python
age = 20

if age >= 18:
    print("Adult")
```

The mental model: Python evaluates the expression after `if` down to a `bool`. If it's `True`, the indented block underneath runs. If it's `False`, Python skips straight past the block entirely — the code inside never executes, and no error occurs. This is where indentation (from the Introduction lesson) stops being abstract: the indented lines *are* the block that belongs to this `if`.

Add alternatives with `elif` (checked only if everything above it was `False`) and `else` (runs only if nothing above matched):

```python
score = 72

if score >= 90:
    print("Grade: A")
elif score >= 80:
    print("Grade: B")
elif score >= 70:
    print("Grade: C")
else:
    print("Grade: F")
```

Python checks these top to bottom and stops at the **first** one that's `True` — even if a later condition would also technically be true. With `score = 72`, the first two conditions (`>= 90`, `>= 80`) are `False`, the third (`>= 70`) is `True`, so `"Grade: C"` prints, and Python never even evaluates the `else`. Order matters: if you'd written `score >= 70` before `score >= 90`, a score of 95 would incorrectly print `"Grade: C"`, since that condition is also true for 95 and gets checked first.

### Combining conditions

`and`, `or`, and `not` combine `bool` values:

```python
age = 25
has_id = True

if age >= 18 and has_id:
    print("Entry allowed")

if age < 13 or age > 65:
    print("Discount applies")

if not has_id:
    print("ID required")
```

`and` requires both sides to be `True`. `or` requires at least one side to be `True`. `not` flips a `bool`. These read almost like English, which is exactly the point — but be precise about which one you mean. `age >= 18 or has_id` would let someone in with *just* an ID, regardless of age, which is a different (and probably wrong) rule than the `and` version above. This is a real category of bug: syntactically valid code that expresses the wrong logic.

### Nested conditions

An `if` can contain another `if`:

```python
logged_in = True
role = "admin"

if logged_in:
    if role == "admin":
        print("Full access")
    else:
        print("Limited access")
else:
    print("Access denied")
```

Nesting is sometimes the clearest way to express "this decision only makes sense once that other condition is already true" — but nest sparingly. Three or four levels deep, code like this becomes hard to follow; often an early `if not logged_in: return` (once you're inside a function) reads more clearly than deep nesting. You'll develop a feel for this with practice.

## 4. Loops: Repeating Work

### `for` — iterate over a known sequence

A `for` loop runs its body once for each item in something iterable:

```python
for i in range(5):
    print(i)
```

`range(5)` produces the sequence `0, 1, 2, 3, 4` — five numbers, **starting at 0**, stopping *before* 5. This trips up almost every beginner at least once: `range(5)` does not include `5`. The loop variable `i` takes each value in turn, and the indented block runs once per value — so this prints five lines, `0` through `4`.

You can also loop directly over the characters of a string, or the items of a list:

```python
for letter in "cat":
    print(letter)
# prints: c, a, t — one per line
```

Each pass through the loop is called an **iteration**. Picture it as Python pausing at the top of the loop, pulling the next value out of the sequence, running the body with that value, and then going back to the top to check if there's another value left — until the sequence is exhausted.

### `while` — repeat until a condition becomes false

Use `while` when you don't know in advance how many times you need to repeat — you're repeating *until something changes*, not for a fixed count:

```python
count = 0
while count < 3:
    print(f"Attempt {count + 1}")
    count += 1
```

`count += 1` is shorthand for `count = count + 1` — this line is what eventually makes the condition `False` and ends the loop. **This step is not automatic.** If you forget it, `count` never changes, `count < 3` stays `True` forever, and you have what's called an **infinite loop** — the single most common mistake with `while`. Every `while` loop needs something inside its body that moves it toward the condition becoming `False`.

### `break` and `continue`

`break` exits a loop immediately, skipping any remaining iterations:

```python
for number in range(10):
    if number == 5:
        break
    print(number)
# prints 0, 1, 2, 3, 4 — then stops
```

`continue` skips the rest of the *current* iteration only, and moves on to the next one — the loop keeps going:

```python
for number in range(5):
    if number == 2:
        continue
    print(number)
# prints 0, 1, 3, 4 — 2 is skipped, but the loop doesn't stop
```

The distinction matters: `break` says "I'm done with this loop entirely." `continue` says "skip this one item, but keep going."

## 5. Functions: Packaging Reusable Logic

A function is a named, reusable block of code. Define one with `def`, give it a name and (optionally) parameters, and call it later by name:

```python
def greet(name):
    print(f"Hello, {name}!")

greet("Ayush")
greet("Priya")
```

`name` here is a **parameter** — a placeholder the function's body refers to. `"Ayush"` and `"Priya"` are **arguments** — the actual values supplied at each call. This distinction (parameter = the placeholder in the definition, argument = the real value at the call site) is standard terminology worth using correctly.

Functions can send a result back with `return`:

```python
def add(a, b):
    return a + b

result = add(3, 4)
print(result)   # 7
```

`return` immediately ends the function and hands the value back to whoever called it — unlike `print`, which just displays something and doesn't give the *rest of your program* anything to work with. A function with no `return` statement implicitly returns `None` (from the previous lesson) — this is a real source of confusion when a beginner expects a function to "give back" a value but forgot to `return` it.

### Why functions matter beyond "less typing"

The obvious benefit is not repeating yourself. The less obvious, more important one: a well-named function is a unit of *meaning*. `is_strong_password(pw)` tells the reader what the code is checking without them having to read the implementation. As your scripts grow — and the ones you write for security work will — breaking logic into small, named functions is what keeps a 200-line script readable instead of becoming one long unreadable block.

### Local scope, briefly

A variable created inside a function only exists inside that function:

```python
def compute():
    x = 10
    return x

compute()
print(x)   # NameError: x is not defined
```

`x` is **local** to `compute` — it's created fresh each call and disappears when the function returns. This is deliberate, not a limitation: it means you can reuse a name like `x` or `count` inside as many different functions as you like without them interfering with each other.

## 6. Common Mistakes

**Off-by-one errors with `range()`.** `range(5)` gives `0` through `4`, not `1` through `5`. If you need `1` through `5`, write `range(1, 6)`.

**Infinite `while` loops.** Forgetting to update the variable the condition depends on. If your program hangs and never finishes, this is the first thing to check.

**Confusing `break` and `continue`.** Reread Section 4 if a loop is stopping too early (should be `continue`) or not skipping the way you expected (should be `break`).

**Forgetting `return`.** A function that computes something but never returns it silently gives back `None` to the caller — no error, just a value that's quietly wrong.

**Trying to use a function's local variable outside it.** Covered above — this raises a `NameError`, and the fix is almost always to `return` the value you need instead of trying to reach into the function from outside.

## 7. Practical Relevance

This is the first lesson where the security connection is concrete rather than a promise for later. A password-strength check, a loop that scans a list of ports and reports which respond, a function that classifies a log line as suspicious or not — all three are exactly "a condition, inside a loop, wrapped in a function," which is what you're about to build below.

## 8. Practice

Before the capstone exercise, do these two short drills:

**Drill 1 — FizzBuzz.** Write a loop over `range(1, 21)` (1 through 20). For each number: if it's divisible by both 3 and 5, print `"FizzBuzz"`; if divisible by 3 only, print `"Fizz"`; if divisible by 5 only, print `"Buzz"`; otherwise print the number itself. (Hint: check "divisible by both" *before* checking either one alone — otherwise the first matching `elif` wins and you'll never reach the "both" case.)

**Drill 2 — Count vowels.** Write a function `count_vowels(text)` that loops over each character in `text` and counts how many are in `"aeiou"` (lowercase only is fine). Return the count. Test it on `"hello world"` — you should get `3`.

## 9. Knowledge Check

1. Why does `range(5)` produce five numbers, but not include `5` itself?
2. What's the difference between what `break` does and what `continue` does?
3. What causes an infinite `while` loop, and how do you prevent one?
4. What's the difference between a parameter and an argument?
5. What does a function return if it has no `return` statement at all?

## 10. Capstone Exercise: Password Strength Checker

Write a script `password_check.py` that combines everything from this lesson:

```python
def is_strong(password):
    has_upper = False
    has_digit = False

    for character in password:
        if character.isupper():
            has_upper = True
        if character.isdigit():
            has_digit = True

    long_enough = len(password) >= 8
    return long_enough and has_upper and has_digit


password = input("Enter a password to check: ")

if is_strong(password):
    print("Strong password.")
else:
    print("Weak password — needs 8+ characters, an uppercase letter, and a digit.")
```

Trace through it before you run it: `is_strong` loops over every character once (`for character in password`), using two `bool` flags to remember whether it has seen an uppercase letter or a digit anywhere so far — this is a common pattern, sometimes called an "accumulator" or "flag" variable, worth recognizing when you see it again. `len(password) >= 8` is a condition on its own, combined with the two flags using `and`. The function returns one final `bool`, which the `if` at the bottom branches on.

Run it against `"abc"` (weak: too short, no uppercase, no digit), then `"Password1"` (strong), and confirm the output matches what you'd expect by hand.

**Extend it, on your own:** add a third check — at least one character from `"!@#$%^&*"` — using the same flag pattern as `has_upper` and `has_digit`.

## 11. Key Takeaways

- `if`/`elif`/`else` branch on a condition; Python runs the first block whose condition is `True` and skips the rest.
- `and`/`or`/`not` combine `bool` values — be precise about which logic you actually mean.
- `for` iterates over a known sequence; `while` repeats until a condition becomes `False` — and needs something in its body that eventually makes that happen.
- `break` exits a loop entirely; `continue` skips just the current iteration.
- A function packages reusable logic: parameters are placeholders, arguments are the real values, `return` sends a result back, and variables created inside are local to that function.

## 12. What's Next

This is the last lesson in Python Programming — you now have the four building blocks (variables/types, conditions, loops, functions) that every later script in this course assumes you're comfortable with. The roadmap's next module, **Web Fundamentals**, shifts focus to how the web itself works (HTTP, requests, responses) — you'll come back to Python skills like these the moment you start automating anything against it.
