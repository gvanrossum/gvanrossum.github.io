# More Precise Definition of Scopes in Python

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

Identifiers can have different roles:

- _Variables_: this is what we are concerned with in this essay
- _Attributes_: these are out of scope for this essay
- _Other_: e.g. import names; also out of scope

Examples:

```py
foo = bar  # Both 'foo' and 'bar' have role Variable
foo.append(1)  # 'foo' has role Variable; 'append' has role Attribute
import foo  # 'foo' has roles Other and Variable
```

Role is determined purely based on the grammar.

## Context

Identifiers can occur in several different contexts:

- _Load context_: uses a variable that must be bound elsewhere
- _Store context_: binds, rebinds or unbinds a variable

Examples:

```py
foo = bar  # 'foo' is in a Store context, bar is in a Load context
foo.append(1)  # 'foo' is in a Load context (!)
import foo  # 'foo' is in a Store context
```

Context is determined purely based on the grammar.

## Scope

_Scope_ is an area of the text of a program where a variable is visible.
(In some languages it is also related to _lifetime_,
but for Python we consider that a separate concept.)

The scope of a Python variable is determined by complex rules
that take into account the syntactic position of the variable,
and the presence of `global` and `nonlocal` statements.

