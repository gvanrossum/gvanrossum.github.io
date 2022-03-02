# Python Interpreter State

GvR, February 2022

## Intro

Previously I've teased apart Python [scopes](scopesblog.html).
I found some interesting things.
Today I'm going to try the same for the interpreter state.

_State_ is a formal term for "the contents of memory".
Sometimes we distinguish state from _code_, but in the end,
code is also stored in memory, so the (Python) code that is running
is also considered to be state.
(The code of the interpreter itself is not included in our state,
though.)
A Python interpreter has lots of state.
This is roughly organized across three dimensions:
_global state_, _module state_, and _thread state_.

- Global state is state that is shared between all modules and threads;
  this includes the set of all modules and the test of threads.
  Global state that doesn't have an obvious home is typically housed in
  or accessed via the `sys` modules (for example, `sys.stdout`).
- Module state refers to state stored in the `__dict__` of a specific
  module. This includes a module's global variables, but also all code
  defined in a module. Often most of the code is defined in a class.
  We can refer to this code and class variables as _class state_;
  this gives module state the shape of a tree (with classes as nodes).
- Thread state is more closely associated with code execution.
  Apart from a small amount of per-thread metadata (e.g. its name),
  most thread state is stored in the form of _frames_.

## Global state

Also known as _interpreter state_.
This is modeled by the following class:

```py
class InterpreterState:
    modules: dict[str, object]
    builtins: Namespace
    threads: dict[int, ThreadState]
```

The `modules` dict maps module names
(which are technically _dotted names_, e.g. `foo.bar.baz`)
to objects.
There is no constraint on module objects --
typically these are instances of the `Module` class,
but they may be instances of any other class,
as long as it has a `__dict__` attribute
that evaluates to a dict.
Documented module attributes like `__name__` and `__file__`
are stored as corresponding entries in the module's `__dict__`.
The module's `__dict__` is also used (by reference)
as the `globals` dict for all code defined in the module,
with the exception of code compiled using `eval()` or `exec()`
when passing an explicit globals argument.

The `builtins` attribute gives the namespace used to look up
builtin functions, classes and other objects (e.g. exceptions).
All code belonging to a given interpreter uses the same namespace
for builtins.
(In CPython this can be overridded in various ways;
that is not part of the reference semantics though.)

## Thread state

The most elusive state is thread state, so let's focus on that first.
A _thread_ is an object managed by the `threading` module.
There's also the _main_ thread, which is created spontaneously
by the interpreter to run the initial program.
In many cases that's the only thread in a program.

Interesting things happen when a thread starts executing code.
_Code objects_ wrap _executable code_.
Typically that is a form of bytecode, but we don't specify the details.
Executable code is distinct from source code, which is just text.

Code objects exist in several slight variants:

- toplevel code (including `exec` and `eval` code)
- class body code
- function code (including lambda and comprehensions)
- code for generators and coroutines

When a thread starts running the initial code executed is either
a toplevel code object or a _callable_ with some prepared arguments.
Either way a frame is created for the initial code.
(TODO: What if the _callable_ is a builtin?)
A frame has a a _local namespace_,
which is a mapping from variable names to values (objects).
The prepared arguments are placed in the local namespace
according to the function definition.
This placement guarantees that for each argument name there is
always a corresponding value in the local namespace.
Initially, no other values exist in the local namespace.

To support _closures_, each frame has a pointer to
the next enclosing frame (the pointer may be NULL).
This refers to the *statically* or *lexically* enclosing frame,
and is used to access _nonlocal variables_.
(Note that the mechanism described here is quite different
from that used by the CPython implementation.)

(TODO: Explain how to access a nonlocal variable.)

Each frame also has a pointer to its _global namespace_,
where its global variables are stored.
Global variables are shared by all frames for functions and classes
defined within the same toplevel scope.

Frames also have features to support *execution* of code.

First, each frame has a _back pointer_ which points to the frame
that called it.
This is NULL for the initial frame of each thread.
It is also NULL for suspended generators and coroutines
(async functions).

Next, a frame may have specific storage for _temporary values_,
to be used by the evaluation of expressions that may be suspended.
These are stored in the local namespace using variable names
made up by the compiler to avoid clashing with actual locals
(for example, ".0", ".1", etc.).

Finally, a frame that is not actively executing code may have
a _code pointer_ which is some way for the execution engine
to record where execution in the frame will continue once it is
resumed.
This may be used for a frame currently involved in a call,
to record where execution continues after the call returns;
or it may be used for a generator function suspended in `yield`,
or for a coroutine suspended in `await`.

The suspension point is an abstraction for the program counter
in a traditional (virtual or real) machine.
Similarly, the temporary values are abstractions for registers
or an evaluation stack which traditionally hold intermediate values.

We do not specify the exact way code is generated or executed;
that will be the topic of a separate treatise.
However, the interpreter state should be all that the code needs;
the code itself should be read-only (once it is generated).
(The code may implicitly use an evaluation stack or registers,
but those should not be counted on to be preserved across calls.)

## Memory model

Now that we are describing threads we should really describe
the _memory model_,
i.e. which operations are atomic with respect to each other.
This is not an easy thing!
It could easily take a Master's or Ph.D. Thesis.

For now I'm taking the position that all dict operations
(at least when the keys are all strings) are atomic,
all list operations are atomic,
and attribute operations are atomic.
That makes pretty much everything atomic.
We may be able to be more open-minded for dict operations,
for example, dict operations involving different keys should commute.
We may also have attributes that never change (e.g. `Frame.enclosing`),
whereas other attributes could change (e.g. `Frame.back`).

A specific example of code that is *not* thread-safe would be:

```py
def get_local(self, name: str) -> object:
    if name not in self.locals:
        raise UnboundLocalError
    return self.locals[name]
```

This may raise `KeyError` on the last line if another thread removes
the key from the dict after the `in` check passes.
So we should write this instead like this:

```py
def get_local(self, name: str) -> object:
    try:
        return self.locals[name]
    except KeyError:
        raise UnboundLocalError
```

Note that frame locals may be shared,
e.g. a nested function may be called in another thread.
(In CPython, this implies that *cells* require protection,
while _fast locals_ don't.)

That's all I'm saying about the memory model for now.

## Functions

Functions are the basic building blocks for code execution.
They form the connection between the dynamic and static worlds.
Consider a simple function definition:

```py
def add(a, b):
    return a + b
```

When this definition is encountered in the source code,
the compiler generates a _code object_ for it.
The internals of a code object are opaque
(what details CPython exposes are implementation dependent),
except that we know that when the function is called,
the following things happen:

- A new Frame object is created (see below for details).
- The arguments are placed in the frame's locals.
- The current frame is updated.
- The function's code object is executed, given the new frame.

Eventually the function either returns a value or raises an exception.

### Function objects

When we write `add(x, 1)`, how is the code object found?
We require `add` to refer to a variable
whose value is a _function object_.
The function object's `enclosing` attribute is used to set
the frame's `enclosing` attribute.
(This may be NULL.)
The function's `globals` are copied to `frame.globals`,
the current frame (maybe NULL) is used to initialize `frame.back`,
and the function's `code` is placed in `frame.continuation`.

### Calling a function

Then the arguments are placed in the frame for the code to find.
The exact mechanism is unspecified (only the code cares),
but for now, let's say that positional arguments are put in
`locals[".args"]` and keyword arguments in `locals[".kwds"]`.
In our case, the positional arguments are a list of two items,
the value obtained from the variable `x` and the constant 1.
(CPython actually uses a tuple, but that's an implementation detail.)
The keyword arguments are an empty dict in this example.

Once the new frame is initialized, the caller sets its own frame's
`continuation` field to a new code object that determines
where execution should continue after the call returns.
(We'll describe exception handling later.)

Next we set the thread state's `current_frame` field to the new frame.
and then we transfer control to the new frame's code.
The first thing this code must do is validate the arguments
(not too few and not too many, and just the right kind),
and then transfer then into local variables.
Here, the bytecode compiler would generate something like this:

```py
args = frame.locals[".args"]
kwds = frame.locals[".kwds"]
if len(args) != 2 or len(kwds) != 0:
    raise TypeError
frame.set_local("a", args[0])
frame.set_local("b", args[1])
```

(It's actually an implementation choice whether the arguments
are copied into the corresponding local variables of the frame
by the caller or by the callee,
but it's simpler to specify to do this in the callee.)

### Returning from a function

When the code has computed its result, the calling frame is resumed.
The calling frame is identified by the current frame's `back` pointer.
We copy that into the thread state's `current_frame` field,
and transfer control to the (new current) frame's continuation.

How does the return value get transferred from the callee
to the caller?
This is again up to the bytecode compiler,
but since all storage must be represented in the thread state,
let's propose a mechanism:

- The callee puts the result in its `locals[".result"].
- The caller copies it from there into its own `locals[".value"]`.

(The names differ to avoid accidentally setting the caller's result.)

### Summary in code

The interpreter code for calling a function object could be this:

```py
    def call(
        self: Function, args: list[object], kwds: dict[str, object]
    ) -> Never:
        tstate = ThreadState.current_threadstate
        frame = Frame(func)
        frame.locals[".args"] = args
        frame.locals[".kwds"] = kwds
        tstate.current_frame = frame
        TRANSFER(frame.continuation)  # Magic, transfers control to code
```

The constructor for `Frame` is defined like this:

```py
class Frame:
    ...
    def __init__(self, func: Function):
        self.tstate = ThreadState.current_threadstate
        self.locals = {}
        self.enclosing = func.enclosing
        self.globals = func.globals
        self.back = self.tstate.current_frame
        self.continuation = func.code
```

The interpreter code for returning from a function could be this:

```py
class Frame:
    ...
    def return_(self) -> Never:
        result = self.locals[".result"]
        ThreadState.current_frame = caller = self.back
        if caller is not None:
            caller[".value"] = result
            TRANSFER(caller.continuation)
        # else, the return value is lost
```

## Thoughts on code generation

Interpreter state and code generation are tightly linked
(more than I previously appreciated).
The generated code must access the runtime state
using the APIs provided (no matter how informal or undocumented).

APIs themselves are implemented in some language,
and it is useful if this is (mostly) the same language
that is used as the target for the code generator.
For example, take the compilation of the expression `a + b`.
The specification for such a binary operator is pretty complex:
one has to call `type(a).__add__()` and/or `type(b).__radd__()`,
and which is called first depends on the subclass relationship
between `type(a)` and `type(b)`.

Therefore it would be nice
if the generated code could be as simple as `ADD(A, B)`,
where `A` and `B` are the code generated
to load the expressions `a` and `b`, respectively,
and `ADD()` is some API function taking care of the details.
(In CPython, the bytecode compiler targets a different language,
and the result is that there must be bytecode instructions
corresponding to all the necessary helper functions,
from addition to loading variables of different kinds.)

### Tiny Python

Let's name our compilation target _Tiny Python_,
to be defined as a very small subset of Python that is still
usable for this purpose.
(The idea is that it is much easier to reason about
correctness of Tiny Python code than about Python code.)

Tiny Python must obviously support function definitions and calls,
else `ADD(a, b)` could not be a Tiny Python function call.
It must have a `return` statement so that functions can return values.
It must also support function pointers (!) so we can refer to code
(for example, in the `continuation` of a function object, see above).

It must also support some basic control structures,
at least `if` and `while`,
and local and global variables
(maybe the latter can only be read, not written, inside functions).

In terms of data types it will need at least Booleans, integers,
strings, some form of arrays, and some form of records.
(Records could be emulated using arrays,
but the code would be miserable.)
Integers don't need to have unlimited range -- 64-bit is fine.

Tiny Python must support function-local memory,
to hold local (to a Tiny Python function) variables
and intermediate values (for e.g. `x + 1`).

Ideally we could write things like `get_local()` (see above)
in Tiny Python, although the `try`/`except` statement
would have to be replaced with something else;
and we'd either need a built-in `dict` type
or a way to implement it using arrays and records.

Tiny Python's memory model may require some thought,
since functions like `get_global()` and `set_global()`
have critical sections that need to be locked
(ideally the locking is per-dict and per-name).

Finally, Tiny Python may have to have some form of
extension mechanism whereby certain functionality
or data types (e.g. `float` or bignum)
would be implemented outside Tiny Python.

### What does Tiny Python lack?

Tiny Python lacks introspective features.
It does however use dynamic memory allocation.

Tiny Python might not have classes and methods
(records and functions may suffice).
It might not have tuples (records would do).
It may not have a `for`-loop (`while` can do it).

It most definitely won't have `try` or exceptions
-- these are complex functionality whose implementation
should be possible using Tiny Python's primitives.
This means there won't be a `with` statement either.

### Error checking in Tiny Python

Python code that may raise exceptions (i.e., all Python code)
will have to be translated into an idiom that uses
explicit error checks.

For operations returning arbitrary values (objects)
we can use a record with the following fields:

```py
ok: bool  # True if the calculation was a success
value: object  # Value, if a success (else NULL)
error: object  # Exception, if a failure (else NULL)
```

For operations returning a bool (or an error)
we can use a variant with a field `truth: bool` instead of `value`.
(There may also be other variants, e.g. one for integer returns.)

For example, the statement `y = f(x)` might translate to

```py
# 'frame' is the current frame (tstate.current_frame).
x = frame.get_local("x")
if not x.ok:
    <error handling>
newf = new_frame(<code for f>)
args = array(1)
args[0] = x.value
newf.set_local(".args", args)
kwds = array(0)
newf.set_local(".kwds", kwds)
newf.back = frame
# call() transfers control to the code in the frame,
# and returns when that code exits.
# It adjusts tstate.current_frame both ways.
res = newf.call()
if not res.ok:
    <error handling>
frame.set_local("y", res.value)
```

(This assumes slightly different primitives than I have above.)

The `<error handling>` sections should probably use `return`
with an error indicator (possibly just `return x`).

The `<code for f>` blank should be a function pointer
to the code generated for the function `f`.
This should actually be constructed from a function object
(briefly described earlier).

### Loops in Tiny Python

How would we translate a `while` loop from Python to Tiny Python?
Since Tiny Python (being a subset of Python) doesn't have `goto`,
we'll have to translate it to a Tiny Python `while` loop.
Let's say we have

```py
while x != 0:
    <body>
```

This might translate into

```py
ok = True
while ok:
    x = frame.get_local("x")
    if not x.ok:
        <error handling>
    # 'zero' must be a global object with value 0
    cmp = cmp_ne(x.value, zero)
    if not cmp.ok:
        <error handling>
    ok = cmp.truth
    if ok:
        <translation of <body>>
```

(This would be slightly more elegant
if Tiny Python had a "loop-and-a-half" construct,
but since Python doesn't have one, neither does Tiny Python.)

### What to do for generators and async functions

In an earlier [document](informal.md) I've already rambled
about generators and async functions,
in particular the `yield`, `yield from` and `await` constructs.
The key thing to understand here is that a generator function
with two `yield` expressions in it will be split into three
separate Tiny Python functions.
For example, if the input is

```py
def f():
    <part A>
    yield x
    <part B>
    yield y
    <part C>
```

Then the compiler must produce one function
for `<part A>` and `yield x`,
a second function for `<part B>` and `yield y`,
and a third function for `<part C>`.
(There are many complications, but they can all be dealt with.)
