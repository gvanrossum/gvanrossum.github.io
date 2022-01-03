# Towards Formal Semantics For Pythoṇ

Obviously this cannot be done in a single blog post.
Brett has blogged about a similar topic (XXX link).

We shouldn't specify details of GC or reference counting.
Nor should we specify tracing and profiling.

We also can't specify all stdlib modules (or even all builtin functions).
But certain builtin types are part of the specification.

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

