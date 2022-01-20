


Scopes are a compile time concept while _namespaces_ are a runtime concept.
Scopes usually have a one-to-many correspondence to namespaces.
At runtime, when execution enters a scope,
a corresponding namespace is created.
This happens for example upon class creation or function call
(but not upon resume of a generator).
Since a function may be called many times, each call creates a new namespace,
but the function has only one scope.
Because a class may be nested inside a function or loop,
a class scope may also map to multiple namespaces.

Both compile time and runtime search for identifiers.
At compile time, scopes are chained in a certain way.
At runtime, namespaces are also chained, but the chaining is not the same.

Function, lambda and comprehension scopes are _closed scopes_,
and the corresponding namespaces are also closed.
Closed namespaces cannot be manipulated behind the compiler's back
(except the CPython implementation allows the debugger to so so).
When an identifier is searched in a closed namespace but not found,
an exception is raised.
(`UnboundLocalError` except when the scope is chained from a class scope,
in which case we raise `NameError`.)

All other types of scopes are _open scopes_,
and can be _chained_ to another scope.
The corresponding namespaces are also open, and can be chained.
Chained namespaces may be manipulated without the compiler's knowledge,
e.g. `locals()['x'] = 1` binds the variable `x` to the value `1`.
(In a close namespace, the same statement has no lasting effect.)
When an identifier is searched in an open namespace but not found,
we continue searching the chained namespace, if any.
When there is no chained namespace,
we raise `NameError` if the search fails.
Most open namespaces are chained to another open namespace,
but there are exceptions:
a class nested inside a function may be chained to a function namespace,
and the builtin namespace isn't chained to anything.

The global and builtin scopes don't correspond to a syntactic construct;
they are defined at runtime.
When the code of a module is executed,
the toplevel and global scopes are the same.
In `exec` and `eval`, the toplevel and global scopes
may be passed in as arguments and may be separate.
The language specification only recognizes a single builtin scope
(but the CPython implementation allows even that to be overridden).
