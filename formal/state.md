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

When we write `add(x, 1)`, how is the code object found?
We require `add` to refer to a variable
whose value is a _function object_.
The function object's `enclosing` attribute is used to set
the frame's `enclosing` attribute.
(This may be NULL.)
The functions `globals` are copied to `frame.globals`,
the current frame (maybe NULL) is used to initialize `frame.back`,
and the function's `code` is placed in `frame.continuation`.

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
