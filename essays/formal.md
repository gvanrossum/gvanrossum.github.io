# Towards Semi-formal Semantics For Pythoṇ

Guido van Rossum, 2022

[This is not yet an essay.
It's more like a stream of consciousness, where I explore different ideas.]

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
    c.err.__context__ = b.err
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
def $posarg(args, i, defaults, j):
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


# A Virtual Machine Of Sorts

All this made me realize that we might have to start in a different place.
Let's define a tiny language which can be used to specify
the runtime library (lists, dicts etc.)
as well as being the compilation target
(including interpreter and thread state).

I'll call it _Tiny Python_.
It should be a subset of Python that can be type-checked using mypy.
Everything should be static though, so it can be translated to C.
There should be no or very few arithmetic;
instead we'll use function calls.

Here's an attempt at specifying the grammar:

```
program: program_statement+

program_statement: class | function | variable | alias

class: 'class' NAME ['(' NAME ')'] ':' class_block
class_block: NEWLINE INDENT class_statement+ DEDENT
class_statement: method | variable

method: 'def' NAME '(' 'self' [',' parameters]) '->' type ':' block

function: 'def' NAME '(' [parameters] ')' '->' type ':' optional_block
optional_block: NEWLINE INDENT '...' DEDENT | block
# The body of an intrinsics is replaced by ellipsis

parameters: parameter | parameters ',' parameter
parameter: NAME ':' type

variable: NAME ':' type '=' expression NEWLINE

alias: NAME '=' optional_type NEWLINE

block: NEWLINE INDENT statement+ DEDENT

statement: variable | if | while | return | assignment | side_effect

if: 'if' condition ':' block ['else' ':' block]

while: 'while' condition ':' block

return: 'return' expression NEWLINE
# Only allowed inside a function

assignment: target '=' expression NEWLINE
# target must refer to a local variable or an attribute of one

side_effect: call NEWLINE | STRING NEWLINE
# STRING is allowed so we can have docstrings

type: optional_type | atomic_type | 'object' | 'None'
optional_type: atomic_type '|' None
atomic_type: 'bool' | 'int' | 'float' | 'str' | STRING | NAME
# NAME must be a class name

# Syntax for condition, comparison and expression may need improvement
condition:
    | comparison 'and' comparison
    | comparison 'or' comparison
    | 'not' comparison
    | comparison

comparison: expression cmpop expression | '(' condition ')'
cmpop: '==' | '!=' | '<' | '<=' | '>' | '>=' | 'is' 'not' | 'is'

expression: call | target | literal | '(' condition ')'

target: NAME | NAME '.' NAME

call: target '(' [arguments[] ')'
# target must refer to a class, function or method
arguments: argument | arguments ',' argument
argument: expression
# arguments must match the target's arguments

literal: INTEGER | FLOAT | STRING | 'True' | 'False' | 'None'
```

I'm hand-waiving about the range of integers:
I don't want to have to implement bignums in Tiny Python,
but I also don't really want to have to have them as primitives.
I'll decide on that later.

Similarly, I'm hand-waiving on strings:
are they byte strings or unicode strings?

Types will probably have to be extended with unions and possibly more.

I'm dropping the silly stuff with dollar signs from before;
name references in proper Python code will be compiled to a call,
e.g. `bool` becomes `load_global('bool')`.

Classes should not require dynamic method lookup at runtime:
single inheritance is supported, but methods cannot be overridden.

Class definitions, function definitions and type aliases
are only allowed at the top level.

There's a big gaping hole around code objects.
I'll fill that when I get to it.

Note the absence of tuples and other data structures.

## A simple array

Let's define an array.
The implementation is actually a linked list:
we don't care about performance (yet).

```py
def add(a: int, b: int) -> int:
    ...

def sub(a: int, b: int) -> int:
    ...

def panic(msg: str) -> None:
    ...

class Cell:
    head: object
    tail: "Cons"

    def __init__(self, head: object, tail: "Cons") -> None:
        self.head = head
        self.tail = tail

Cons = Cell | None

# We don't have generics, alas
class Array:
    first: Cons

    def __init__(self) -> None:
        self.first = None
    
    def len(self) -> int:
        n: int = 0
        it: Cons = self.first
        while it is not None:
            n = add(n, 1)
            it = it.tail
        return n
    
    def insert(self, pos: int, data: object) -> None:
        if pos < 0:
            panic("negative position")
        prev: Cons = None
        next: Cons = self.first
        while pos > 0:
            if next is None:
                return panic("position too large")
            pos = sub(pos, 1)
            prev = next
            next = next.tail
        cell: Cons = Cell(data, next)
        if prev is None:
            self.first = cell
        else:
            prev.tail = cell

    def append(self, data: object) -> None:
        self.insert(self.len(), data)

    def delete(self, pos: int) -> None:
        "delete item at pos (similar to insert)"
    
    def getitem(self, pos: int) -> object:
        next = self.first
        while pos > 0 and next is not None:
            pos = sub(pos, 1)
            next = next.tail
        if pos != 0 or next is None:
            panic("index out of range")
            return None
        return next.head
```

[Well, that was fun. But I'd like to take a different tack again.]

# Transforming and Translating

The difference between _translating_ and _transforming_ is as follows:

- Transforming is a function from Python AST to Python AST.
  For example, the things described in Brett's blog are transformations
  (e.g. rewriting `try`/`except`/`finally` into a `try`/`finally block
  containing a `try`/`except` block).
- Translating is a function from Python AST to Tiny Python AST.
  Example: the translation of a Python `try`/`finally` block
  into a Tiny Python `try_finally$()` call.

The `Translate()` function may occasionally call `Transform()`,
but not the other way around.
For example:

```py
def Transform(a: AST) -> AST:
    ...

def Translate(a: AST) -> TinyCode:
    a = Transform(a)
    ...
```

(As written this example does not make much sense.
Imagine `Transform` and `Translate` being methods on `AST` objects,
or functions using `singledispatch` to specialize on specific `AST` nodes.
A static type checker would accept `a.Transform().Translate()`
and even `a.Transform().Transform()`,
but not `a.Translate().Translate()` or `a.Translate().Transform()`.)

## Transformation example

Let's work through the transformation that separates `except` and `finally`.
As shown earlier, the idea is that we transform

```py
try:
    BLOCK1
except E:
    BLOCK2
finally:
    BLOCK3
```

into

```py
try:
    try:
        BLOCK1
    except E:
        BLOCK2
finally:
    BLOCK3
```

We can define a function to transform any `try` statement as necessary,
as follows:

```py
import ast

def TransformTry(a: ast.Try) -> ast.Try:
    if not a.finalbody:
        return a
    if not a.handlers:
        return a
    return ast.Try(
        body=ast.Try(body=a.body, handlers=a.handlers, orelse=a.orelse),
        finally=a.finalbody
    )
```

This leaves a `Try` node without a `finally` clause alone,
and also leaves a `Try` node with only a `finally` clause alone,
but separates the two when both `except` and `finally` are present.
(The grammar ensures that `orelse` is only present with `handlers`.)

Now we can also sketch out the translation for `try` statements.

```py
def TranslateTry(a: ast.Try) -> TinyCode:
    if a.handlers and a.finalbody:
        a = TransformTry(a)
    if a.finalbody:
        assert not a.handlers
        return TranslateTryFinally(a)
    assert a.handlers
    return TranslateTryExcept(a)

def TranslateTryFinally(a: ast.Try) -> TinyCode:
    ...

def TranslateTryExcept(a: ast.Try) -> TinyCode:
    ...
```

Before we can flesh out the latter two functions we'll need to come up
with an API for generating TinyCode.
I tried constructing AST nodes, but this is too verbose,
so instead I'll assume some API thatr translates to text.

```py
def TranslateTryFinally(a: ast.Try) -> TinyCode:
    assert not a.handlers
    body1 = Translate(a.body)
    body2 = Translate(a.finalbody)
    return generate_tiny_code(
        "b: Result = {body1}\n"
        "c: Result = {body2}\n"
        "if c.ok:\n    return b\n"
        "if b.ok:\n    return c\n"
        "c.err.__context__ = b.err\n"
        "return b",
        locals()
    )
```

We'll leave the translation for `try`/`except` to the imagination.

There are some details here that are probably wrong --
we generate some statements that form a function body.
This should presumably be wrapped in a function definition,
but really the translation would have to be a *call* to that function,
and then we'd need to come up with a mechanism to return two things:
a function definition and an expression to call.
The assumption here is that Python *statements* are translated to
Tiny Python *expressions* with type `Result`.
It might be easier if Tiny Python had something like function blocks,
but then it wouldn't be a subset of Python.
(I guess this is why academics usually resolve to lambda calculus. :-)

Anyway, before we're getting too excited,
let me point out a complication.

## Generators and Async Functions

Tiny Python doesn't have exceptions.
Thus, the translation for even the simplest piece of Python code
requires using the `Result` class (introduced above as `$Result`),
and Python statements are translated into Tiny Python expressions.

This is mildly annoying,
but it's useful because it lets us specify exception semantics.
Many other things are also missing (e.g. dynamic lookup, nested scopes).
All those things are thus specified rigorously by their translation.

Much more annoying, Tiny Python doesn't have generators or async functions.
Hence, no `yield`, `yield from` or `await`.
Why is this so annoying?
Because it means that a sequence of statements containing `yield` cannot
actually be translated to a function in Tiny Python!
Take this example:

```py
def f(a):
    x = a + 1
    print(x)
    yield 42
    x = x + 1
    print(x)
```

How do we translate this?
One possibility would be to first transform it into a class definition:

```py
class f:
    def __init__(self, a):
        self.a = a
        self.__state__ = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.__state__ == 0:
            self.x = self.a + 1
            print(self.x)
            self.__state__ = 1
            return 42
        if self.__state__ == 1:
            self.x = self.x + 1
            print(self.x)
            self.__state__ = 2
        raise StopIteration
```

This might actually work,
although it requires translating all local variable references
to instance variable references.

How would it work with `yield` inside some other statement?
For example

```py
def f(a):
    if a:
        print("before")
        yield 42
        print("after")
    yield 100
```

Here the `__next__` method would have to look like this:

```py
    def __next__(self):
        if self.__state__ == 0:
            if self.a:
                print("before")
                self.__state__ = 1
                return 42
            self.__state__ = 2
        if self.__state__ == 1:
            print("after")
            self.__state__ = 2
        if self.__state__ == 2:
            self.__state__ = 3
            return 100
        raise StopIteration
```

There are also complications related to `send()` and `throw()`,
but I think those can all be handled.
(The arguments to `send` and `throw` become arguments to `__next__`,
that default to `None`.)

The principal annoyance is that
we need to translate local variables to instance variables.
Another major annoyance is how `__next__` must manipulate the `__state__`.
Both these complicate all other translation code.

Should we treat this as a translation or a transformation?
I'm not sure yet.

The translation of `yield from` is complicated but uses the same approach.
Async functions and `await` are just a special case of that
(with some extra bits to avoid mixing generators and async functions).

**Alas, the above approach is likely to fail when there are loops
or `try`/`except` statements.**
The authors of
[[1]](http://cs.brown.edu/research/plt/dl/lambda-py/lambda-py.pdf)
appear to have solved this by using continuations,
but Tiny Python doesn't (and IMO shouldn't) have those.
Another approach would be to translate everything to a bytecode VM,
but that sounds like a very complex target.
I'm still hoping for inspiration to strike.
