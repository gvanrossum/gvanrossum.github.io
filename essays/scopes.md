# Everything You Always Wanted to Know About Scopes But Were Afraid to Ask

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
- _Other_: e.g. some import names, keyword parameter names in calls

Note that `nonlocal` and `global` statements imply Variable role.

This essay is concerned only with variables.

Examples:

```py
foo = bar  # Both 'foo' and 'bar' have role Variable
foo.append(1)  # 'foo': Variable; 'append': Attribute
import foo  # 'foo': Variable
import foo.bar  # 'foo': Variable; 'bar': Other
```

Each occurrence of an identifier has exactly one role.
Role is determined purely by the grammar.

## Context

Variables (and attributes) can occur in several different _contexts_:

- _Load context_: uses a variable that must be bound elsewhere
- _Store context_: binds, rebinds or unbinds a variable

Note that `nonlocal` and `global` statements imply Store context.

Examples:

```py
foo = bar  # 'foo': Store; bar: Load
foo.append(1)  # 'foo': Load; 'append': Store
def foo(arg): pass  # 'foo': Store; 'arg': Store
```

Each occurrence of an identifier has exactly one context.
Context is determined purely by the grammar.
Context and role are orthogonal concepts.

## Scope

A _scope_ is the area of the program text where a variable is _visible_.
(In some languages it is also related to _lifetime_,
but for Python we consider that a separate concept.)

Scope is a _compile time_ concept.
The scope of a Python variable is determined by rules
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

- Toplevel (all code not contained in any of the following)
- Class definition
- Function definition
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

### Textual scope

The _textual scope_ of an identifier occurring in the program text is
the nearest enclosing scope-forming syntactic element.

This concept is only used to simplify the next definition.

### Syntactic scope

The _syntactic scope_ of a specific identifier occurrence is
the scope where the compile time lookup process starts.
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
    - the leftmost iterable clause

- In addition, the syntactic scope of
  walrus targets occurring in comprehensions
  is the nearest enclosing non-comprehension scope
  (i.e., skipping enclosing comprehensions)

### Assignment scope

The _assignment scope_ of a given identifier occurrence is
the nearest enclosing scope, starting with its syntactic scope,
where that identifier occurs in a Store context.
(If the given identifier has a Store context,
the assignment scope is the syntactic scope.)

### Binding scope

The _binding scope_ of a given identifier occurrence is
the scope corresponding to the namespace where the identifier
will be searched at runtime
(or where it will be searched first, for chained lookups).

This is equal to the identifier's assignment scope
unless a `global` or `nonlocal` statement mentioning the identifier
is present in the assignment scope:

- If a `global` statement for the identifier is present,
  the binding scope is the global scope.

- If a `nonlocal` statement for the identifier is present,
  the binding scope is the next enclosing function scope
  that does not contain a `nonlocal` statement for that identifier
  where it occurs in a Store context.
  It is a compile time error if no such scope exists.
  It is also a compile time error if the scope thus found
  contains a `global` statement for the identifier,
  or if any scope contains a `nonlocal` statement
  as well as a `global` statement for the same identifier.

### Scope for identifiers in comprehensions

Special rules apply to identifiers (with Variable role)
occurring in comprehensions:

- The syntactic scope for identifiers in the leftmost iterable clause is
  the nearest enclosing scope (this was mentioned above).
- The syntactic, assignment and binding scope
  for name targets in a `for` clause is that comprehension
  (this follows from other rules).
- The assignment scope for walrus targets is
  the nearest enclosing non-comprehension scope;
  it is an error if this is a class scope.
- The syntactic scope for other identifiers is
  the nearest non-class scope enclosing the comprehension
  (this acts as if the comprehension were a lambda).

In addition, the following conditions are errors:

- A walrus target binds a `for` clause target for a comprehension
  containing that walrus (directly or indirectly).
- A walrus occurs in an iterable clause in that comprehension
  (even if as part of a lambda or another comprehension).

(For the walrus-related rules, see
[PEP 572](https://www.python.org/dev/peps/pep-0572/#scope-of-the-target).)

# Compile time and runtime search

## Compile time search

At compile time any occurrence of an identifier with a Variable role
(regardless of Load/Store context) is assigned a binding scope.
The algorithm is specified through the definition of binding scope,
above.

## Runtime search

A Store operation (corresponding to a Store context)
always updates the namespace corresponding to the binding scope.

A Load operation (corresponding to a Load context)
does one of the following,
depending on the nature of the binding scope and the syntactic scope:

- If the binding scope is an open scope,
  the search tries the corresponding binding namespace,
  then the global namespace, and finally the builtin namespace.
  If the search fails, `NameError` is raised.

- If the binding scope and the syntactic scope are both closed scopes,
  the closed namespace corresponding to the binding scope is searched.
  If the search fails, `NameError` is raised.
  (If the binding scope *is* the syntactic scope,
  `UnboundLocalError`, a subclass of `NameError`, is raised.)

- If the binding scope is a closed scope
  and the syntactic scope is an open scope,
  the class namespace is searched before the binding namespace.
  If the search fails, `NameError` is raised.
  (This supports [bpo-17853](https://bugs.python.org/issue17853).)
