# Core Concepts: Variables, Types, and Operators

## 1. What You Will Learn

By the end of this lesson you should be able to:

- explain what a Python variable actually is (a name, not a box)
- assign, reassign, and inspect variables
- name variables correctly and avoid the mistakes that trip up beginners
- identify Python's core built-in types: `int`, `float`, `str`, `bool`, and `None`
- use `type()` to check what you're working with, and convert between types deliberately
- use arithmetic, comparison, and string-formatting operators correctly

## 2. Why This Matters

The Introduction lesson had you print fixed, literal values. That's fine for a one-off calculation, but it falls apart the moment you need to reuse a value, change it, or build something out of user input — which is nearly everything you'll ever write. Variables and types are the vocabulary every later lesson assumes you already have: conditions branch on typed values, loops iterate over typed collections, functions accept and return typed data. Get this lesson solid and everything after it gets easier; skip it and you'll be debugging type errors instead of learning new concepts.

## 3. Core Concept: What a Variable Actually Is

Don't think of a variable as a labeled box that holds a value. In Python, that mental model breaks down later (especially once you meet mutable objects like lists), so it's worth building the correct one now.

Think of it this way instead: **values live independently in memory, and a variable is just a name that points at one.** Assignment (`=`) doesn't put a value "into" a name — it makes the name refer to a value that already exists.

```python
name = "Ayush"
age = 19
```

Read the first line as *"the name `name` now refers to the string `"Ayush"`"*, not *"put `"Ayush"` into a box called `name"`*. This distinction matters immediately when you reassign:

```python
age = 19
age = 20
```

The second line doesn't modify the number `19` — numbers can't be modified. It makes `age` refer to a *different* value, `20`, entirely. The `19` is simply no longer referred to by anything and is discarded. This is why the phrase "reassigning a variable" is more accurate than "changing a variable's value."

## 4. Assignment and Naming

The general form is `name = value`. Python evaluates the right-hand side completely first, then binds the name on the left to the result:

```python
total = 10 + 5   # right side evaluates to 15 first, then total refers to 15
```

**Naming rules** (enforced by Python — breaking these is a `SyntaxError`):
- Must start with a letter or underscore, not a digit (`score1` is fine, `1score` is not)
- Can contain letters, digits, and underscores only — no spaces, no hyphens
- Case-sensitive: `score` and `Score` are two different names

**Naming conventions** (not enforced, but expected — code that ignores them is harder for anyone, including you later, to read):
- `snake_case` for variables and functions: `user_name`, `max_retries`
- Names should describe what the value *is*, not its type: `age`, not `age_int`

You can assign several names at once:

```python
x, y, z = 1, 2, 3
```

Python matches each name on the left to the value in the same position on the right. This is genuinely useful, not just shorthand — it's how you'll later unpack function results that return more than one value.

## 5. Dynamic Typing

Python variables have no fixed type — the *value* has a type, the name doesn't:

```python
value = 5          # value refers to an int
value = "five"     # now value refers to a str — this is legal
```

This is called **dynamic typing**. It's convenient, but it's also exactly the kind of thing that causes real bugs: reusing a variable name for two conceptually different things (a number, then a string) is a common source of confusing errors several lines later, when older code assumes the earlier type. Prefer a fresh, well-named variable over recycling one for a different purpose.

## 6. The Core Built-In Types

Every value has a type, and you check it with the built-in `type()` function.

| Type | Example | Represents |
|---|---|---|
| `int` | `42` | A whole number, positive or negative |
| `float` | `3.14` | A number with a decimal point |
| `str` | `"hello"` | Text — always in quotes, single or double |
| `bool` | `True` / `False` | A truth value — exactly two possible values |
| `NoneType` | `None` | The deliberate absence of a value |

```python
>>> type(42)
<class 'int'>
>>> type(3.14)
<class 'float'>
>>> type("hello")
<class 'str'>
>>> type(True)
<class 'bool'>
>>> type(None)
<class 'NoneType'>
```

A few things worth understanding properly, not just memorizing:

**Strings are always quoted**, either `'single'` or `"double"` — Python treats them identically, so pick one convention and stick with it (this course uses double quotes). Without quotes, `hello` isn't a string at all — Python would try to treat it as a variable name and fail with a `NameError` if nothing by that name exists.

**`bool` is a specialized `int`.** This sounds like trivia, but it explains real behavior: `True` behaves as `1` and `False` behaves as `0` in arithmetic (`True + True` really does evaluate to `2`). You won't rely on this often, but it explains behavior you'll eventually run into.

**`None` is not the same as `0`, `False`, or `""`.** It specifically means "no value was ever assigned here" — a function that doesn't explicitly `return` anything returns `None`. Confusing `None` with "empty" or "zero" is a common source of bugs once you start writing your own functions.

### Converting between types

Values don't convert themselves — you do it explicitly, using `int()`, `float()`, or `str()`:

```python
>>> int("42")      # str -> int
42
>>> str(42)         # int -> str
'42'
>>> float("3.14")   # str -> float
3.14
>>> int("abc")      # this fails — "abc" isn't a valid number
ValueError: invalid literal for int() with base 10: 'abc'
```

That last line matters: conversion isn't guaranteed to succeed. `int("abc")` can't produce a number, so Python raises a `ValueError` instead of silently returning something wrong. Later, when you read input from a user or a file, this is exactly the kind of failure you'll need to anticipate.

## 7. Operators

**Arithmetic** works as you'd expect, with two behaviors worth calling out:

```python
>>> 7 / 2
3.5      # / always produces a float
>>> 7 // 2
3        # // is floor (integer) division — discards the remainder
>>> 7 % 2
1        # % is the remainder ("modulo")
>>> 2 ** 3
8        # ** is exponentiation
```

`//` and `%` come up constantly once you start writing loops and conditions — `%` in particular is the standard way to check "is this number even?" (`n % 2 == 0`) or "has every 10th item been processed?" (`count % 10 == 0`).

**Comparison** operators produce a `bool`:

```python
>>> 5 == 5
True
>>> 5 == "5"
False    # different types are never equal, even if they "look" the same
>>> 5 != 3
True
>>> 5 > 3
True
```

`==` checks equality; `=` assigns. Writing `if x = 5:` instead of `if x == 5:` is a mistake so common in other languages that Python simply refuses to compile it — using `=` where an expression is expected is a `SyntaxError`, not a silent bug. That's one of the rare cases where Python's strictness saves you from yourself.

**String concatenation and formatting.** You can join strings with `+`, but it only works between strings — `"age: " + 25` fails, because `+` doesn't know whether you mean arithmetic or text-joining across types. The practical, readable way to build a string containing values is an **f-string**:

```python
name = "Ayush"
age = 19
print(f"{name} is {age} years old.")
```

The `f` before the opening quote turns `{...}` inside the string into "evaluate this expression and insert the result here." This is the standard modern way to build strings with embedded values — prefer it over manual `+` concatenation, which gets unreadable fast and forces you to convert every non-string value yourself.

## 8. Reading Input

`input()` pauses execution, displays an optional prompt, and returns whatever the user typed — **always as a `str`**, even if they typed a number:

```python
name = input("What's your name? ")
age_text = input("What's your age? ")
age = int(age_text)   # convert explicitly — age_text is a string, not a number
print(f"In 5 years, {name} will be {age + 5}.")
```

Forgetting that `input()` always returns a string is one of the single most common beginner mistakes — `age_text + 5` would fail, because you can't add an `int` to a `str`, even if the string looks like a number.

## 9. Common Mistakes

**Using `=` when you mean `==`.** Covered above — Python catches this one for you with a `SyntaxError` in a boolean context, but it's worth knowing why.

**Forgetting `input()` returns a string.** `age = input("Age: ")` followed by `age + 1` raises a `TypeError: can only concatenate str (not "int") to str`. Convert first: `age = int(input("Age: "))`.

**Reassigning a variable to an unrelated type partway through a script.** Legal, but a real source of bugs — a variable named `total` that starts as an `int` and later gets reassigned to a `str` "just for a moment" will break the first piece of code downstream that still expects a number.

**Comparing values of different types with `==` and expecting `True`.** `5 == "5"` is `False`. If you're comparing user input (always a string) against a number, convert one side deliberately rather than hoping Python will do it for you — it won't.

## 10. Practice

Write a script `bmi.py` that:

1. Uses `input()` to ask for a weight in kilograms and a height in meters
2. Converts both inputs to `float`
3. Computes BMI using `weight / (height ** 2)`
4. Prints the result using an f-string, formatted to one decimal place: `f"{bmi:.1f}"`

Run it with a weight of `70` and height of `1.75` — you should get a BMI of `22.9`.

## 11. Knowledge Check

1. When you write `x = 5` and then `x = 6`, does Python modify the value `5`, or does something else happen?
2. What type does `input()` always return, regardless of what the user types?
3. What's the difference between `/` and `//`?
4. Why does `5 == "5"` evaluate to `False`?
5. What does `None` represent, and how is it different from `0` or `""`?

## 12. Key Takeaways

- A variable is a name pointing to a value, not a container holding one.
- Python is dynamically typed: the value has a type, not the variable name.
- The core types are `int`, `float`, `str`, `bool`, and `None` — check any of them with `type()`.
- `input()` always returns a `str`; convert deliberately with `int()` or `float()` when you need a number.
- Use f-strings (`f"{value}"`) to build strings containing other values — not manual `+` concatenation.

## 13. What's Next

**Hands-on Practice** puts all of this to work: you'll use `if`/`elif`/`else` to make decisions based on these values, `for`/`while` loops to repeat work, and write your own first function — then combine all three into one working script.
