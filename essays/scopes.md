# Everything You Always Wanted To Know About Scopes

## (But were afraid to ask)

Guido van Rossum, 2022

# Introduction

I've been trying to pin down the definition of scopes.
Here's my latest attempt.
IMO the official
[Naming and binding
](https://docs.python.org/3/reference/executionmodel.html#naming-and-binding)
section in the Language Reference does not do a good job specifying this.

# Definitions

## Role

Identifiers can have different _roles_:

- _Variables_
- _Attributes_
- _Other_: e.g. import names, keyword parameter names in calls

This essay is concerned only with variables.

Examples:

```py
foo = bar  # Both 'foo' and 'bar' have role Variable
foo.append(1)  # 'foo' has role Variable; 'append' has role Attribute
import foo  # 'foo' has roles Other and Variable
import foo.bar  # 'foo' has role Variable; 'foo' and 'bar' have role Other
```

Each occurrence of an identifier has exactly one role.
Role is determined purely by the grammar.

## Context

Identifiers can occur in several different _contexts_:

- _Load context_: uses a variable that must be bound elsewhere
- _Store context_: binds, rebinds or unbinds a variable

Examples:

```py
foo = bar  # 'foo' is in a Store context, bar is in a Load context
foo.append(1)  # 'foo' is in a Load context (!)
import foo  # 'foo' is in a Store context
```

Each occurrence of an identifier has exactly one context.
Context is determined purely by the grammar.
Context and role are orthogonal concepts.

## Scope

A _scope_ is the area of the program text where a variable is _visible_.
(In some languages it is also related to _lifetime_,
but for Python we consider that a separate concept.)

Scope is a _compile-time_ concept.
The scope of a Python variable is determined by rules (specified later)
that take into account the syntactic position of the variable
and the presence of `global` and `nonlocal` statements.

A scope always corresponds to one of the following:

- Builtin
- Global
- Toplevel
- Class
- Function
- Lambda
- Comprehension (list, set or dict comprehension, or generator expression)

The difference between global and toplevel scope is subtle:

- In a module, they are the same.
- In `exec` and `eval`, they *may* be different.

## Namespace

A _namespace_ is a mapping from variable identifiers to values.
Namespaces are a _runtime_ concept.

A namespace always corresponds to a scope.
Many namespaces may correspond to the same scope.
For example, a new namespace is created for each function call,
but a given function only has one scope.
The global and toplevel scopes may share a single namespace.

## Scope-forming syntactic element

A _scope-forming syntactic element_ is a syntactic element
that corresponds to a scope.

The following syntactic elements are scope-forming:

- Toplevel
- Class
- Function
- Lambda
- Comprehension

## Scope and namespace categories

We define a variety of categories of scopes and namespaces:

### Closed scopes and namespaces

Function, lambda and comprehension scopes are _closed scopes_,
and correspond to _closed namespaces_.
A closed namespace cannot be extended dynamically
(e.g. by monkey-patching).

### Open scopes and namespaces

All other scopes are _open scopes_, and correspond to _open namespaces_.

### Chained namespace

A _chained namespace_ is one that delegates search to another namespace
if the search key is not found.
Chained namespaces are always open
(but the chained-to namespace may be closed).

### Terminal namespace

A _terminal namespace_ is the opposite of a chained namespace.
Closed namespaces are always terminal
(but they may be chained to from open namespaces).

### Textual scope

The _textual scope_ of an identifier occurring in the program text is
the nearest enclosing scope-forming syntactic element.

This concept is only used to simplify the next definition.

### Syntactic scope

The _syntactic scope_ of a specific identifier occurrence is
the scope where the compile-time lookup process starts.
This is usually the identifier's textual scope,
with the following exceptions:

- In the following cases the syntactic scope is
  the next outer enclosing scope
  (if the syntactic scope is the toplevel scope,
  this is the global scope):

  - In a class definition:
    - the class argument list (base classes and keyword arguments)
  - In a function definition:
    - the decorators
    - the function name
    - type annotations
    - default expressions
  - In a lambda definition:
    - default expressions
  - In a comprehension:
    - the leftmost iterable

- In addition, the syntactic scope of
  walrus targets occurring in comprehensions
  is the next outer enclosing non-comprehension scope
  (i.e., skipping enclosing comprehensions)

### Assignment scope

The _assignment scope_ of a given identifier occurrence is
the nearest enclosing scope, starting with its syntactic scope,
where that identifier occurs in a store context.

### Definition scope

The _definition scope_ of a given identifier occurrence is
the scope corresponding to the namespace where the identifier
will be looked up at runtime (or the start of the chain,
if it's a chained namespace).
