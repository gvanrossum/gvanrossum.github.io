# Towards Formal Semantics For Pythoṇ

Guido van Rossum, 2022

## Introduction

Obviously this cannot be done in a single blog post.
Brett has blogged about a similar topic
[here](https://snarky.ca/tag/syntactic-sugar/).

We shouldn't specify details of GC or reference counting.
Nor should we specify tracing and profiling.
(These would be nice, but too complicated, and too dependent on implementation.)

We also can't specify all stdlib modules (or even all builtin functions).
But certain builtin types are part of the specification.

[TODO: Go over all examples and add type annotations.]

## Calculations, actions and state

Think of Python execution as a combination of *calculations* (computing a value) and *actions* (having side effects).

The part about computing values is relatively straightforward -- e.g. we compute the value of `a + b` by first computing the values of `a` and `b` to serve as the operands, and then invoking some operation `ADD(a, b)` on these.

Actions have side effects on carefully defined *state*.
The state is divided into interpreter state, module state, frame state, and so on.
Most state is stored in some *namespace*, which has the semantics of a Python dictionary with string keys (though most methods aren't needed -- we mostly just need `__getitem__`, `__setitem__` and `__delitem__`).

The compiler plays an important role.
It translates Python code into operations that are defined in the formal semantics.
It also analyzes variable scopes.

Code (actions and calculations) always executes in a *frame*.
A frame (and this may be surprising) is just an array of namespaces, with `f[0]` being namespace for the local scope, `f[1]` being the namespace for the immediately surrounding scope, and so on.
The last namespace (`f[-1]`) is a chainmap combining the module namespace and the builtin namespace.
Class scopes are also represented by chainmaps.
The compiler assigns each variable reference an index into the frame.
(Frames do not need to contain a "return address" -- the formal semantics handle that concept differently.)

We can unify actions and calculations by defining an action as a calculation that returns None.

## Results and exceptions

Now that we've established state and frames, we need to talk about exceptions.
Everything that produces a value (an action or a calculation) may also raise an exception.
We will redefine the return values as having the following structure
(making up syntax as we go):

```py
class $Result:
    @overload
    def __init__(self, ok: True, val: object):
        self.ok = True
        self.err = None
        self.val = val
    @overload
    def __init__(self, ok: False, err: $Throwable):
        self.ok = False
        self.val = None
        self.err = err
```

[This is a very clumsy tagged union definition;
if we use these a lot we'll need to invent a better syntax.]

[TODO: Use `$Success(val)` and `$Failure(err)` aliases.]

Here class `$Throwable` is a superclass of `BaseException`.
There are a few throwable objects that can't be caught using `except`.
These are used by `return`, `break` and `continue`.

## Translating `pass`

Brett's version is
[here](https://snarky.ca/unravelling-the-pass-statement/).

The translation of a `pass` statement is a successful empty result:
`$Result(True, None)`.

## Intrinsics

Note the use of `$`.
Identifiers containing a `$` are *intrinsics*.
They are only known by the compiler and interpreter.

A useful intrinsic is `$bool`, which behaves the same as the builtin `bool`,
but cannot be overridden by shenanigans like updating the `__builtins__` dict.
It returns a `$Result` instance.
It guarantees the following:
- either `ok` is `False`, `val` is `None`, and `err` is a `$Throwable`;
- or `ok` is `True`, `err` is `None`, and `val` is either `True` or `False`.

## Call-by-name intrinsics

We will eventually translate all of Python into intrinsic function calls,
using a new type of functions with call-by-name arguments.
To demonstrate this, here's the definition of `if$`.
The trailing `$` defines an intrinsic with call-by-name arguments.
It is also used for the call-by-name arguments themselves.

```py
def if$(cond$, then$, else$):
    c = $bool(cond$)
    if not c.ok:
        return c
    if c.val:
        return then$
    return else$
```

Ignoring the recursive definition for now, this first evaluates the condition.
If that's an exception, that is propagated.
Otherwise, the result value is inspected,
and either the then-part or the else-part is evaluated.
To avoid recursion in the definition of intrinsics,
statements like `if` and `return` in an intrinsic function definition
always refer to the basic builtin operations.

[Question: would it be better to explicitly *call* the call-by-name arguments?
E.g. `c = $bool(cond$())`.]

## Translating `if` statements and expressions

Brett's version is
[here](https://snarky.ca/unravelling-elif-else-from-if-statements/).
However Brett sees the challenge is to implement `else`,
for which he introduces a helper flag
(and with multiple `elif` clauses it gets hairy).

Here's a sketch of how the compiler translates various forms of `if` statements.

Basic `if` with `else`.
Input:

```py
if foo():
    bar()
else:
    baz()
```

Translation:

```py
if$(foo(), bar(), baz())
```

Basic `if` without `else`.
Input:

```py
if foo():
    bar()
```

Intermediate translation:

```py
if foo():
    bar()
else:
    pass
```

Final translation:

```py
if$(foo(), bar(), $Result(True, None))
```

One or more `elif` clauses.
Input:

```py
if c1():
    a1()
elif c2():
    a2()
elif c3():
    a3()
else:
    a4()
```

Intermediate translation:

```py
if c1():
    a1()
else:
    if c2():
        a2()
    else:
        if c3():
            a3()
        else:
            a4()
```

Then each individual `if` statement is translated.
Nobody wants to see what the final translation looks like. :-)

Finally, conditional expressions translate likewise:

```py
foo() if cond() else bar()
```

becomes

```py
if$(cond(), foo(), bar())
```

## Translations for `A and B`, `A or B`

Brett's version is
[here](https://snarky.ca/unravelling-boolean-operations/).

In an expression context, `A and B` translates to `and$(A, B)`,
and `A or B` translates to `or$(A, B)`.
It so happens that for `A and B and C` it doesn't matter
whether we group that as `(A and B) and C` or as `A and (B and C)`.
Here are the call-by-name intrinsics used:

```py
def and$(left$, rite$):
    c = left$  # This is a $Result
    if not c.ok:
        return c  # Propagate exception
    if not $bool(c.val):
        return c  # Return first false result
    return rite$

def or$(left$, rite$):
    c = left$
    if not c.ok:
        return c
    if $bool(c.val):
        return c  # Propagate first true result
    return rite$
```

There's an exception when these occur in a Boolean context.
Two additional transformations are applied first.

- `$bool(A and B)` translates to `$bool(A) and $bool(B)`
- `$bool(A or B)` translates to `$bool(A) or $bool(B)`

For example, since `if` is a Boolean context, this input:

```py
if A and B:
    foo()
else:
    bar()
```

first transforms to

```py
if$($bool(A and B), foo(), bar())
```

which then becomes

```py
if$($bool(A) and $bool(B), foo(), bar())
```

[TODO: Clarify Boolean context.]

## Translating `not`

Brett's version is
[here](https://snarky.ca/unravelling-not-in-python/).

Input:

```py
not X
```

Translation:

```py
$not($bool(X))
```

Definition of intrinsic function `$not`:

```py
def $not(x):
    r = $bool(x)
    if not r.ok:
        return r
    return $Result(True, not r.val)
```

As usual, the uses of `not` inside the intrinsic function are not expanded.

## Translating `while` statements

Input:

```py
while foo():
    bar()
else:
    baz()
```

Translation uses a new call-by-name intrinsic:

```py
while$(foo(), bar(), baz())
```

Here's the (recursive) definition:

```py
def while$(cond$, body$, else$):
    c = if$(cond$,
            seq$(body$,
                 while$(cond$, body$, else$)),
            else$)
    if not c.ok:
        return c
    return $Result(True, None)
```

Note that no result is returned upon completion.
In particular, neither the body nor the else-part's return value is used.
However, exceptions are propagated immediately.

See below for `break` and `continue`, which cause us to revisit this.

## The `seq$` utility

The definition of `while$` uses the call-by-name intrinsic `seq$`,
which is a simple convenience to combine multiple actions:

```py
def seq$(first$, second$):
    c = first$
    if not c.ok:
        return c
    return second$
```

[Is it useful to return the result?]

We may occasionally call `seq$` with more than two arguments.
The intention is that `seq$(A, B, C)` means `seq$(A, seq$(B, C))`,
and so on.

## Translating arithmetic expressions

Brett's version is
[here](https://snarky.ca/unravelling-binary-arithmetic-operations-in-python/).

For each binary arithmetic operator (`+`, `-` etc.)
we define a corresponding intrinsic function (`$add`, `$sub`, etc.).
This includes bitwise and shift operators, but not comparisons.
For example,

```py
a + b * c
```

translates to

```py
$add(a, $mul(b, c))
```

Note that these intrinsics are not call-by-name.
The arguments are evaluated strictly from left to right,
so the example evaluates first `a`, then `b`, finally `c`.

[Alternatively, we could force order by making these call-by-name.]

The arithmetic intrinsics are all defined in a similar way.
We show `$sub` (because it's not commutative).
(Technically `$add` isn't either, e.g. `"a" + "b" == "ab" != "b" + "a"`,
but it's easier to think of arithmetic while going over this code.)

```py
def $__sub__(t, x, y):
    if not $hasattr(t, "__sub__"):
        return $NotImplemented
    return t.__sub__(x, y)

def $__rsub__(t, x, y):
    if not $hasattr(t, "__rsub__"):
        return $NotImplemented
    return t.__rsub__(x, y)

def $sub(a, b):
    ta = $type(a)
    tb = $type(b)
    if ta is not tb and $issubclass(tb, ta):
        # Try __rsub__ before __sub__ if RHS is more derived
        r = $__rsub__(tb, b, a)  # TO DO: expand call semantics
        if not r.ok:
            return r
        if r.val is not $NotImplemented:
            return r
        r = $__sub__(ta, a, b)
        if not r.ok:
            return r
        if r.val is $NotImplemented:
            raise TypeError("unsupported operand type etc.")
        return r
    # Normal case, try __sub__, then __rsub__
    r = $__sub__(ta, a, b)
    if not r.ok:
        return r
    if r.val is not $NotImplemented:
        return r
    if ta is tb:
        # Don't bother with __rsub__ if the same class
        raise TypeError("unsupported operand type etc.")
    r = $__rsub__(tb, b, a)
    if not r.ok:
        return r
    if r.val is $NotImplemented:
        raise TypeError("unsupported operand type etc.")
    return r
```

[TO DO: Brett's version is better.]

Here `$hasattr`, `$type`, `$issubclass` and `$NotImplemented`
are intrinsic counterparts of the corresponding builtins.
A fully formal specification needs to define these,
and also check their error returns.

## Translating `try`

See also Brett's [post](https://snarky.ca/unravelling-finally-and-else-from-try/).

First, like Brett, we change

```py
try:
    foo()
except ...:
    bar()
finally:
    baz()
```

into two separate forms:

```py
try:
    try:
        foo()
    except ...:
        bar()
finally:
    baz()
```

Similarly, we replace

```py
try:
    foo()
except ...:
    bar()
else:
    baz()
```

with the equivalent

```py
$1 = False
try:
    foo()
    $1 = True
except ...:
    bar()
if $1:
    baz()
```

### Translating `try` ... `finally`

Input:

```py
try:
    foo()
finally:
    bar()
```

Translation:

```py
try_finally$(foo(), bar())
```

Intrinsic definition:

```py
def try_finally$(body$, cleanup$):
    b = body$  # This is a $Result
    c = cleanup$  # This too
    if c.ok:
        return b
    if b.ok:
        return c
    b.err.__context__ = c.err
    return b
```

### Translating `try` ... `except`

Input:

```py
try:
    body()
except E1 as v1:
    handle1()
```

Translation:

```py
try_except1$(body(), E1, 0, "v1", handle1())
```

Intrinsic:

```py
# Arguments pos1, var1 are call-by-value
def try_except1(body$, exc1$, pos1, var1, handle1$):
    b = body$
    if b.ok:
        return b
    # TODO: Check for errors from following operations
    exc1 = exc1$
    if $exception_matches(b.err, exc1):
        if pos1 >= 0 and var1 != None:
            $set_var(pos1, var1, exc1)
        h1 = handle1$
        if pos1 >= 0 and var1 != None:
            $set_var(pos1, var1, None)
            $del_var(pos1, var1)
        if not h1.ok:
            h1.err.__context__ = b.err
        return h1
    # TODO: Repeat for exc2, exc3 etc. if present
    return b

def $exception_matches(err, exc):
    return $isinstance(err, exc)
```

(The `$set_var` and `$del_var` intrinsics set and delete a variable.
The integer argument is the index for the scope in the frame.)

If the `as var` clause is missing, `pos1` is `-1` and `var1` is `None`.
if the exception is missing (i.e., `except:`), `exc1` is `$BaseException`.

If there are multiple except clauses, we call `try_exceptN$`
(where `N` is the number of except clauses)
with `N` sequences of `excK$, posK, varK, handleK$` arguments.
This is just boring so we don't show the details here.

[TO DO: We could use varargs call-by-name intrinsics for this.]

## Loops with `break` and `continue`

I took the original idea for this approach from Modula-3.
Brett's take is [here](https://snarky.ca/unravelling-break-and-continue/).

We implement `break` and `continue` as special `$Throwable` subclasses
(uncatchable exceptions).

The compiler translates `break` and `continue` into calls to
`$break()` and `$continue()`.
The compiler rejects these outside loops.

```py
class $BreakThrowable($Throwable):
    pass

class $ContinueThrowable($Throwable):
    pass

def $break():
    return $Result(False, $BreakThrowable())

def $continue():
    return $Result(False, $ContinueThrowable())
```

Now we revisit the code for `while$`.

```py
def while$(cond$, body$, else$):
    c = $bool(cond$)
    if not c.ok:
        return c
    if not c.val:
        return else$
    b = body$
    if b.ok:
        return while$(cond$, body$, else$)
    if $isinstance(b.err, $BreakThrowable):
        return $Result(True, None)
    if $isinstance(b.err, $ContinueThrowable):
        return while$(cond$, body$, else$)
    return b
```

## Translating `for` loops

Brett's version is [here](https://snarky.ca/unravelling-for-statements/).

Brett explains how `iter()` and `next()` are defined along the way,
which I'll put off (or maybe I'll borrow his definitions).
We use `$iter` and `$next` to avoid namespace games.

### Translating `for` without `else`

Input:

```py
for var in iterable():
    body()
```

Intermediate translation:

```py
$it = $iter(iterable())
while True:
    try:
        var = $next($it)
    except $StopIteration:
        break
    $body()
```

We can then translate the `while` loop.
This supports `break` and `continue` in the body.
The `$it` variable is unique to each loop
(i.e. two nested loops use different variables).

### Translating `for` with `else`

Input:

```py
for var in iterable():
    body()
else:
    otherwise()
```

Intermediate translation (first iteration):

```py
$it = $iter(iterable())
while True:
    try:
        var = $next($it)
    except $StopIteration:
        otherwise()
        break
    $body()
```

However, this is wrong if there's a `break` or `continue` in `otherwise()`.
This is legal if there is an outer loop.
In that case the `break` or `continue` should affect the outer loop.

So we use Brett's solution:

```py
$it = $iter(iterable())
$looping = True
while $looping:
    try:
        var = $next($it)
    except $StopIteration:
        $looping = False
        continue
    $body()
else:
    $otherwise()
del $it, $looping
```

And then we translate the `while` loop.

## Translating functions and calls

Functions have several issues that make them very complex to specify.
The most complex part is sorting out keyword arguments and defaults.
There are also complexities around generators and `async` functions.
Decorators provide another slight bump in the road
(Brett addressed decorators [here](https://snarky.ca/unravelling-decorators/)).
Finally there are subtleties around "callables" and `__call__`.

When a pure Python functions gets called a new empty dict is created.
The parameters are placed in this dict and a new frame is constructed
(not necessarily in that order).
Remember a frame is just an array of scopes, item 0 referencing the locals.
The remaining scopes are copied not from the caller
but from the _defining_ scope (where the `def` statement ran).

[Maybe we should redefine frames as a linked list?
That would make frame creation faster, but accessing nonlocals slower.]

Once the frame is created we execute the code of the function in it.
When the code finishes executing we have a `$Result` representing
either a return value or an exception.

We don't discuss memory management, but it is possible that
the frame and/or the locals dict are still referenced.

### Translating `return`

Like `break` and `continue`, we implement `return` using a `$Throwable`
that cannot be caught.

```py
class $ReturnThrowable($Throwable):
    def __init__(self, val):
        self.val = val

def $return(val=None):
    return $Result(False, $ReturnThrowable(val))
```

The translation of a function body is then as follows:

```py
r: $Result = BODY
if r.ok:
    return $Result(True, None)
if $isinstance(r.err, $ReturnThrowable):
    return $Result(True, r.err.val)
return r  # Propagate exception
```

Here `BODY` is a (low-level) function representing the function body.
If execution "falls through the end" it returns a success,
if an error occurs or a `return` is executed it returns a failure.
We turn failures raised by `$return` into successes.
This gives the precise semantics of `return` statements
in the presence of `finally` clauses,
even if the `finally` clause contains another `return`
or a `break` or `continue`.
(Those all override the `return` in the `try` block.)

### Translating `raise`

We translate `raise X` to `$raise(X)`.
We translate `raise X from Y` to `$raise_from(X, Y)`.
We translate `raise` to `$reraise()`.
Definitions:

```py
def $raise(exc):
    return $Result(False, exc)

def $raise_from(exc, cause):
    exc.__cause__ = cause
    return $Result(False, exc)

def $reraise():
    exc = $active_exception()
    if exc is None:
        return $Result(False, $RuntimeError("No active exception to raise")
    return $Result(False, exc)
```

[I will owe the reader the definition of `$active_exception`.
This lives in the thread state
and is set whenever an exception is being handled.
There is a stack of these.]

### Translating calls

Calls contain up to four types of arguments:

- positional: `f(1, 2)`
- keyword: `f(x=1, y=2)`
- varargs: `f(*args)`
- varargs keywords: `f(**kwds)`

The syntax allows these to be combined (almost) freely.
By the time the function is being called,
positional and vararg arguments have been combined into a single tuple,
and keywords and vararg keywords have been combined into a single dict.
Duplicate keywords have also been diagnosed at this point.

Now the function is called and the fireworks begin.
In the formal semantics (as in very early Python)
the function always receives a tuple and a dict,
and it is up to the function to initialize the locals from those.
The function also has a tuple of default values.

For now, we ignore keywords but show what kind of code
the compiler can generate for positional arguments.
Suppose the definition is

```py
def foo(x, y, z=xyzzy):
    BODY
```

The compiler generates something like this:

```py
def foo($args, $defaults):
    x = $posarg($args, 0, $defaults, -3)
    y = $posarg($args, 1, $defaults, -2)
    z = $defarg($args, 2, $defaults, -1)
    BODY
```

The `$defaults` argument is a tuple of (precomputed) default values
passed from `foo.__defaults__` by the caller.
Note that this is mutable!

Here are the intrinsics:

```py
def $posargs(args, i, defaults, j):
    assert i >= 0
    if i < len(args):
        return args[i]
    assert j < 0
    if j + len(defaults) >= 0:
        return defaults[j]
    raise TypeError(...)  # mandatory argument i missing
```

### Translating function definitions

A function definition constructs a function object.
It has a `__code__` attribute which we won't specify for now.
It has an attribute `__dict__` initialized to `{}`.
It has an attribute `__doc__` set by the compiler from the docstring literal.
It has metadata attributes `__name__`, `__qualname__` and `__module__`,
set by the compiler to values determined at compile time.
It also has attributes `__annotations__`, `__defaults__` and `__kwdefaults__`,
set by the compiler to values computed at function definition time.
It has an attribute `__closure__` which reveals nested scopes.
Finally it has attributes `__builtins__` and `__globals__`,
which cause complications we'll put off till later.
