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

We begin with a series of definitions,
applicable to all _unqualified identifiers_
(i.e., not preceded by a dot),
whether used in an expression or as assignment or deletion _target_.
(More about targets below.)

The _syntactic scope_ of an identifier as the nearest enclosing
grammar element that qualifies as a scope
(i.e., toplevel, class, function, lambda, or comprehension).

The _lexical scope_ of an identifier
is the same as its syntactic scope,
with the following exceptions,
which lexically belong to the nearest enclosing non-comprehension scope:

- The class name in a class definition
- The function name in a function definition
- The base classes and keyword arguments in a class definition
  (e.g., `base, flag=1` in `class C(base, flag=1): ...`)
- The default values and annotations in functions and lambdas
- The rightmost iterable in a comprehension
  (e.g., `BAR` in `[x+y for x in FOO for y in BAR if BAZ]`),
  but not the condition following it (here, `BAZ`)
- Walrus targets in comprehensions
  (see [PEP 572](https://www.python.org/dev/peps/pep-0572/#scope-of-the-target);
  this states that for nested comprehensions,
  the target belongs to the scope containing the outermost comprehension)

The _defining scope_ of an identifier is
the nearest enclosing lexical scope where it is has a _target role_.

We need to make a little detour to define target role.
Each non-keyword identifier occurrence has one of the following roles,
based purely on where it occurs syntactically:

- Expression (typical use in an expression)
- Target (typical use as assignment or deletion target)
- Attribute (e.g. `x.FOO`; these have no scope)
- Other (e.g. imported module, or `global` or `nonlocal` statement;
  these have no scope either)

The following are positions where target roles occur
(in these examples, `FOO` is always the target):

- Assignment, e.g. `FOO = ...`
- Augmented assignment, e.g. `FOO += ...`
- Variable declaration, e.g. `FOO: int`
- Walrus, e.g. `(FOO := ...)`
- Deletion, e.g. `del FOO`
- Target of a `for` statement, e.g. `for FOO in ...: ...`
- Target of a comprehension,
  (list/set/dict comprehensions and generator expressions),
  e.g. `[... for FOO in ...]`
- Target of a `with` statement, e.g. `with ... as FOO: ...`
- Target of an `except` clause, e.g. `except ... as FOO: ...`
- Function name, e.g. `def FOO(): ...`
- Class name, e.g. `class FOO: ...`
- Function parameter, e.g. `def f(FOO): ...`
- Lambda parameter, e.g. `lambda FOO: ...`
- Import without `from` or `as`, e.g. `import FOO` or `import FOO.lala`
- `from` `import` without `as`, e.g. `from lala import FOO`
- Import with `as`,
  e.g. `import lala as FOO` or `from la import lala as FOO`

[TODO: Did I forget anything?]

The exact definition of a target role is hard to give
without reference to specific rules in the grammar,
since some syntactic positions allow multiple or complex targets,
e.g. `FOO, (BAR, BAZ) = ...`.
Not all of the above support this.
Also, no identifier has a target role when the target syntactically
is an attribute or subscript, like `obj.attr = 0` or `a[i] = 0`.

Finally, the _binding scope_ of an identifier
is its defining scope unless that defining scope contains a
`global` or `local` statement naming that identifier.
In particular:

- If the defining scope for `x` have `global x`,
  then the binding scope for `x` is the toplevel scope.
- If the defining scope for `x` have `nonlocal x`,
  then the binding scope for `x` is
  the nearest enclosing defining function scope
  that doesn't have `global x` or `nonlocal x`,
  and such a scope must exist.

Note that the definition for `nonlocal` skips class scopes
and scopes that don't define `x`.
For example:

```py
def f(x):
    def g():
        print(x)
        class C:
            x = "nope"
            def h(self):
                nonlocal x
                x += 1
        return C().h
    return g
```

In this example the `x` in `x += 1` in `h`
has `f` as its defining scope, since:

- the containing class scope `C` is skipped
  (even though it defines `x`);
- the containing function scope `g` is skipped
  because it doesn't define `x`.

There is no prohibition on `nonlocal` _occurring_ in a class.

Since lambdas and comprehensions cannot syntactically contain
`global` or `nonlocal` statements,
if an identifier's lexical scope is a lambda or comprehension,
its binding scope is its defining scope.


#### Name binding, unbinding and lookup algorithm

At runtime, operations that bind or unbind (delete) an identifier
always bind or unbind it
in the namespace corresponding to its binding scope.

Operations that look up an identifier can go several ways
depending on the syntactic category of its binding scope.

- If the binding scope is a function, lambda or comprehension,
  the name must exist in the corresponding namespace,
  else the search raises `UnboundLocalError`.
- If the binding scope is a class,
  if the name does not exist in the class namespace,
  the search continues in the global namespace,
  then the built-in namespace.
- If the binding scope is the toplevel scope,
  then the search continues in the built-in namespace.

If the search reaches the built-in scope
and the name is not found there,
it the search raises `NameError`.

Note that augmented assignment (e.g. `x += 1`)
combines a lookup and an assignment.
In rare cases this can produce surprising results.
For example:

```py
x = 0
class C:
    x += 1
print(x, C.x)  # 0 1
```

The binding scope of `x` in `x += 1` is `C`,
but since it is a class scope,
the lookup reads the global `x`,
but the assignment writes the local `x`.

There is one final wrinkle at runtime.
In `exec` and `eval`, the global and local namespaces
corresponding to the toplevel scope may be separate.
In this case, stores and deletions always use the local namespace,
but lookups reaching this scope first try the local namespace,
then the global namespace, and finally the built-in namespace.

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
