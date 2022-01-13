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

See [Lexical analysis in the language
reference](https://docs.python.org/3/reference/lexical_analysis.html).

The tokenizer is written in C, and hence most likely has bugs.
There's an alternative tokenizer written in Python,
and we know there are occasional differences between the two.
The bugs tend to be about obscure edge cases of whitespace handling.
I'd rather not spend time on this right now.

One thing to note is that there is another layer in front of this:
Unicode decoding.
Most source code is stored in UTF-8,
but Python is defined in terms of Unicode code points.
In addition, for identifiers we apply some Unicode normalization (which?).
AFAIK we don't normalize string literals.
There are probably many weirdnesses due to Unicode.
(For example, there are alternative digits that may or may not work.)

There are no practical size limits on the input due to the lexer:
files, lines, identifiers and strings may be as long as we have space for.

### Syntactic analysis

See [Full Grammar specification in the language
reference](https://docs.python.org/3/reference/grammar.html).

Here we're in a fairly good spot.
There is a formal grammar
(albeit using PEG, which is more complicated than context-free grammars)
and a formal definition of AST nodes.
All further processing of code uses AST nodes as input.

Some constraints that are considered syntactic constraints
are not expressed in the grammar,
e.g. the placement of `return` and `yield` inside functions,
the placement of `await`, `async for` and `async with` inside `async def`,
and the placement of `break` and `continue` inside loops.
These are checked ad-hoc in the next stage of compilation
(perhaps as part of semantic analysis).

### Semantic analysis

See [Naming and binding in the language
reference](https://docs.python.org/3/reference/executionmodel.html#naming-and-binding).

A few things close to syntax are done here
(and often raise `SyntaxError`),
like the placement of certain statements (see above).

Other examples include the requirement that parameter names are unique
(rejecting function definitionas like `def f(x, x):`)
and that keyword arguments are unique
(rejecting calls like `f(x=1, x=1)`).

The main task of this stage however is to assign each identifier a scope.

A _scope_ is either a comprehension, a function (which could be a lambda),
a class, or a "toplevel" scope (module or `exec` or `eval`).

Each occurrence of an identifier is assigned a scope
by analyzing all code that _defines_ identifiers
(e.g. arguments, assignments, imports, class/function definitions,
for-loops, and more),
plus syntax that _modifies_ identifier scope (i.e., `global` and `nonlocal`).
It disregards dead-code analysis,
so that e.g. `if False: x = 1` still counts as defining `x`.

Scopes can be either dynamic or static.
For example, functions scopes are static,
but class and global scopes are dynamic.
The key difference between dynamic and static scopes is
that if an identifier searched for in a static scope is not found,
it is considered "unset" (which is a failure),
while if an identifier is searched for in a dynamic scope,
if it is not found the search continues in the next linked scope.

Scopes are linked by the semantic analysis.
This linkage is always static (it happens during AST analysis),
and the linked scopes form a DAG.
The linkage is a bit complicated because when functions nest,
identifiers defined in outer functions are visible in inner functions
(unless overridden), while identifiers defined in classes are only
visible in that class scope.
(Scopes are unrelated to attribute namespaces.)

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
