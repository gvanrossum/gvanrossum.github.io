# Towards Semi-formal Semantics For Pythoṇ

Guido van Rossum, 2022

[For the previous set of ramblings, [look here](informal.md).]

## Introduction

It would be nice to have a more formal specification of Python.
A few things are getting in the way:

- The language is rather big and has grown organically.
- Much of the semantics depend on data types (list, dict, str etc.).
- Practical backwards compatibility is determined by details of CPython.

My approach here is to first identify the many layers,
and then focus on the layers that are the most in need of specification
(IMO that's the execution model).

In first approximation we can identify the following layers,
which roughly parallel the stages of a typical compiler and runtime:

- Lexical analysis (tokenizing)
- Syntactic analysis (parsing)
- Semantic analysis (symbol table, identifier scope analysis)
- Code generation
- Code execution
- Built-in data types
- Importing modules
- Standard library

I'll briefly go over each of these.

### Lexical analysis

This is specified well in [Lexical analysis
](https://docs.python.org/3/reference/lexical_analysis.html)
in the language reference.

### Syntactic analysis

See [Full Grammar specification
](https://docs.python.org/3/reference/grammar.html)
in the language reference.

Here we're also in a fairly good spot.
There is a formal grammar
(albeit using PEG, which is more complicated than context-free grammars)
and a formal definition of AST nodes.
All further processing of code uses AST nodes as input.

Some constraints that are considered syntactic constraints
are not expressed in the grammar,
e.g. the placement of `return` and `yield` inside functions,
the placement of `await`, `async for` and `async with` inside `async def`,
and the placement of `break` and `continue` inside loops.
These are checked ad-hoc in a separate next stage of compilation
(perhaps as part of semantic analysis).

Other examples include the requirement that parameter names are unique
(rejecting function definitionas like `def f(x, x):`)
and that keyword arguments are unique
(rejecting calls like `f(x=1, x=1)`).

### Semantic analysis

See [Naming and binding
](https://docs.python.org/3/reference/executionmodel.html#naming-and-binding)
in the language reference.

The task of this stage is to assign each identifier a scope.

A _scope_ is either a comprehension, a lambda, a function,
a class, or a _toplevel scope_.

Toplevel scopes are for modules and for `exec` and `eval`.
For each invocation of the compiler there is a single toplevel scope.

Scopes are closely related to _namespaces_,
but while namespaces are a run-time concept,
scopes are a compile-time concept.
For example, a function may be called (or defined!) multiple times,
and for each call a new namespace is created for the local variables.
But a function has a single scope, in which all its locals are defined.

Scopes may be lexically nested in each other,
except for the toplevel scope,
which is never nested in another scope
(but may contain other scopes nested inside it).
Note that the grammar restricts some nesting
(e.g. a class definition cannot occur inside a lambda).

#### Scope assignment

Each occurrence of an identifier is assigned to a scope
by analyzing all code that potentially _defines_ identifiers
(e.g., assignments, class/function definitions, and more),
plus syntax that _modifies_ identifier scope
(i.e., `global` and `nonlocal`).
Scope analysis must ignore dead-code analysis (if any),
so that e.g. `if False: x = 1` still counts as defining `x`.

The _syntactic scope_ of an identifier as the nearest enclosing
grammar element that qualifies as a scope
(i.e., toplevel, class, function, lambda, or comprehension).

The _lexical scope_ of an identifier
is usually the same as its syntactic scope, with the following
exceptions, which belong to the next outer scope:

- The class name in a class definition
- The function name in a function definition
- The base classes and keyword parameters in a class definition
  (e.g., `base, flag=1` in `class C(base, flag=1): ...`)
- Default values and annotations in functions and lambdas
- The rightmost iterable in a comprehension
  (e.g., `BAR` in `[x+y for x in FOO for y in BAR]`)
  and a condition following it, if any
- Walrus targets in comprehensions

[TODO, HIRO]

#### Name lookup algorithm

[TODO]

### Code generation

[TODO]

### Code execution

[TODO]

### Built-in data types

[TODO]

### Importing modules

[TODO]

### Standard library

[TODO]

## Deep dive on code generation and execution

[TODO]
