# Everything You Always Wanted to Know About Scopes But Were Afraid to Ask

Guido van Rossum (February 2022)

The [Faster CPython](https://github.com/faster-cpython/ideas) project made me think about how we can be sure that we don't accidentally change the language.
The standard answer to this question is usually a thorough test suite, and I don't want to dismiss the importance of that.

But there are complementary approaches that help us *think through* proposed changes to the implementation, and one thing that I believe is essential to all approaches is a thorough *definition* of the language semantics.
(After all, if you don't know what it is, how can you test for it?)

Here my thoughts immediately went to the [Language Reference](https://docs.python.org/3.11/reference/), but unfortunately that document is far from unambiguous, and many edits over the years have not improved its clarity.
I asked around and was pointed to an interesting [paper by Joe Gibbs Politz et al.](http://cs.brown.edu/research/plt/dl/lambda-py/lambda-py.pdf) which developes formal semantics for (a subset) of Python.
Unfortunately that approach is a little *too* abstract and full of Greek letters for me, so I kept looking.
I also looked at Brett Cannon's [desugaring blog](https://snarky.ca/tag/syntactic-sugar/), which is more to my liking.

In the end I was distracted by a subproblem: _how do Python scopes actually work_.
I decided to write that up before tackling any larger problems.

So, Python scopes.
You can easily find tutorials that explain Python's "LEGB" (Locals, Enclosing, Globals, Builtins) lookup rule for variables, but that skips many details that are important for compatibility.

For example, class scopes differ from function scopes:
A class inside a function can see that function's locals, but a function inside a class can't see the class variables without a `self` or class name prefix.
This difference is actually intentional.
Consider this example:

```py
class C:
    def f1(self, a):
        return a+1
    def f2(self):
        return f1(10)
```

On the last line you might think you are calling the `f1` method.
In fact, if this was C++ or Java, that would be how you'd spell it.
But Python's classes work differently, and if that line could see `f1`, it would call `f1` without passing `self`, which would cause a confusing error message: "TypeError: f1() missing 1 required positional argument: 'self'".
As it is, because inside `f2` we cannot see `f1` at all, we get a different error: "NameError: name 'f1' is not defined".

We can argue about which error is better, but this is how Python is defined to work, so we better be able to model this precisely; without epicycles, the LEGB rule doesn't explain it.
As I was investigating Python's precise scope rules, I realized that I didn't recall all the ins and outs myself!
For example, I was surprised when I found that there's a special bytecode instruction that is used when the body of a class defined inside a function references a local variable of that function, like this:

```py
def f(s):
    n = 1
    class C:
        exec(s)
        print(n)
```

If we call this function as `f("pass")`, it will print `1`, but if we call `f("n = 2")` it will print `2`!
In this case, the LEGB rule predicts the result, but the compiler and runtime have to jump through [hoops](https://github.com/python/cpython/blob/a0e55a571cf01885fd5826266c37abaee307c309/Python/ceval.c#L3089-L3123) to make this happen given how [closures](https://en.wikipedia.org/wiki/Closure_(computer_programming)) are implemented in Python.

Another odd case is a walrus operator (`:=`) in a comprehension.
Here we find that the walrus target goes in the scope *outside* the comprehension.
[PEP 572](https://www.python.org/dev/peps/pep-0572/#scope-of-the-target) explains why and how.
It also lists around a half dozen situations where certain uses of the walrus in a comprehension are forbidden, in an attempt to rule out confusing code.
(In retrospect I think PEP 572 went a little too far there, as this introduces yet more irregularities in the scoping rules.)

Anyway, below I will sketch a few classes that can model Python scopes.
But first I need to get something fundamental out of the way: there's a difference between scopes and namespaces.

- A *scope* is a compile time concept, referring to a region of the source code.
  (The term is sometimes also used to refer to the lifetime of a variable, but in Python that's a totally separate concept, and I will not dwell on it here.)
  When the compiler looks something up in a scope, it is essentially looking through a section of the source code (for example, a function body).
  In practice the compiler doesn't literally search the text of the source code, but an AST (Abstract Syntax Tree).

- A *namespace* is a runtime concept, you can think of it as a dictionary mapping variable names to values (objects).
  When the intepreter looks something up in a namespace, it is essentially looking for a key in a dictionary.
  Function namespaces are implemented without using an actual dictionary, but this is an implementation detail.
  In fact, that other namespaces are implemented using dictionaries is *also* an implementation detail.
  For the description of formal semantics, we don't care about these implementation details -- we just use the term namespace.

When compiling source code, the compiler uses the scope of a variable to decide what kind of code to generate for the interpreter to look up that variable's value or to store a value into it.
This generated code refers to one or more namespaces, never to scopes (which don't exist at runtime).

Below, I will just talk about scopes.
The class hierarchy for scopes is as follows:

- `Scope`
  - `OpenScope`
    - `GlobalScope`
    - `ToplevelScope`
    - `ClassScope`
  - `ClosedScope`
    - `FunctionScope`
      - `LambdaScope`
    - `ComprehensionScope`

The `Scope`, `OpenScope` and `ClosedScope` classes are abstract; the others are concrete.

Scopes are organized in a tree using a `parent` link (there is no need for a list of children).
The parent is `None` for `GlobalScope` (and only for that).
There is no "builtin scope" -- Python's compiler doesn't care about it, and at runtime the builtin namespace is always chained from the global namespace.

The difference between `GlobalScope` and `ToplevelScope` is only apparent when using `exec()` or `eval()` with separate `globals` and `locals` namespaces; in that case the `locals` namespace corresponds to the `ToplevelScope`.
Since the compiler doesn't know or care whether these namespaces are different, it always distinguishes between these two scopes (both unique).

All scopes have three attributes that are sets of variable names:

- `locals`: variables owned by this scope
- `nonlocals`: variables for which this scope has a `nonlocal` declaration
- `globals`: variables for which this scope has a `global` declaration

A single top-down pass on the AST creates all scope objects for a compilation unit and fills these sets.
Filling the sets is done by three methods:

- `store(name)`: called for each assignment to a variable
- `add_nonlocal(name)`: called for each variable in a `nonlocal` declaration
- `add_global(name)`: called for each variable in a `global` declaration

Their definitions are as follows (some details simplified):

```py
class Scope:
    ...
    def store(self, name: str) -> None:
        if name not in (self.locals | self.nonlocals | self.globals):
            self.locals.add(name)

    def add_nonlocal(self, name: str) -> None:
        if name in (self.locals | self.globals):
            raise SyntaxError
        self.nonlocals.add(name)

    def add_global(self, name: str) -> None:
        if name in (self.locals | self.nonlocals):
            raise SyntaxError
        self.globals.add(name)
```

The term "assignment" is interpreted broadly here: it includes function names, argument names, `for` control variables, and so on.
It even includes deletions.
Thus, the following code raises `SyntaxError`, because `del x` adds `"x"` to the `locals` set, which makes the subsequent `add_nonlocal()` call fail:

```py
def f():
    del x
    nonlocal x
```

The `GlobalScope` class overrides `add_nonlocal()` to always raise.
(It doesn't override `add_global()`, since that is legal -- if redundant -- at the top level.)

It is also illegal to *use* a variable prior to a `nonlocal` or `global` declaration.
This can be solved by an additional `uses` attribute managed by a `load()` method.
I am leaving this out for now because it just adds clutter and doesn't affect valid programs.
(Note that scope is determined by assignments and `nonlocal`/`global` declarations, not by use.)

Once the Scope tree has been created and populated, the compiler is ready to generated code.
This is done by another pass over the AST.
During code generation, a key operation is looking up the scope of a variable, as this determines what code to generate for both loads and stores.
For this purpose we define a method `lookup()` that various subclasses override.
A few helpers are also defined.

The simplest version is `GlobalScope.lookup()`:

```py
class GlobalScope(OpenScope):
    ...
    def lookup(self, name: str) -> GlobalScope:
        if name in self.locals:
            return self
        else:
            raise LookupError
```

For other `OpenScope` subclasses we use `OpenScope.lookup()`:

```py
class OpenScope(Scope):
    def lookup(self, name: str) -> OpenScope:
        if name in self.locals:
            return self
        else:
            return self.global_scope().lookup(name)
```

This requires a helper method, `global_scope()`:

```py
class Scope:
    ...
    def global_scope(self) -> GlobalScope:
        assert self.parent is not None
        return self.parent.global_scope()
```

To end the recursion, `GlobalScope` overrides this:

```py
class GlobalScope(OpenScope):
    ...
    def global_scope(self) -> GlobalScope:
        return self
```

(Why not use a loop? The recursive version let a static type checker prove more properties of the code. :-)

For open scopes (global, toplevel, and class scopes) this is the whole story.
Before we tackle closed scopes, let's look at the code generation a bit.
Suppose we're generating code for the body of a class `C`, and we're encountering a load of a variable `x`.
There are only two possibilities:

- it's a local variable in `C`
- it's a global

(The compiler doesn't know or care about builtins. It generates the same code for them as for globals.)

Looking through the above method definitions, we see that there are actually three outcomes when you call `s.lookup("x")`, if `s` is an `OpenScope` instance:

- it can return the local scope
- it can return the global scope
- it can raise `LookupError`

If it returns the local scope, the compiler emits a chained load operation that searches through the local, global, and builtin namespaces, in that order.
If it returns the global scope, the compiler emits a chained load operation searching through globals and builtins.
If the `lookup()` call raises `LookupError`, the compiler treats this as if it returned the local scope.

However, something seems wrong with this description!
Consider this example:

```py
x = 0
class C:
    locals()["x"] = 1
    print(x)
```

If you run this, it prints `1`.
But the `s.lookup("x")` call returns the global scope, because `x` is a global!
Or does it?
No, it doesn't -- `x` is defined in the *toplevel* scope, not in the *global* scope.
(When the `x = 0` statement is recorded in the Scope tree, it calls the toplevel scope's `store()` method, not the global scope's!)
Phew. (I almost started doubting myself there for a moment. For real.)

We'll see this when we look at what the compiler emits for stores.
The compiler uses the same `lookup()` method, which can return the same three things (the local scope, the global scope, or raise `LookupError`).
If it returns the local scope, it emits a local store operation.
If it returns the global scope, it emits a global store operation.
If it raises `LookupError`, again it treats this as the local scope, and returns a local store operation.
Store operations are never chained -- this is a fundamental Python rule.

What I've shown so far is how *all* scopes used to work in very early versions of Python, back in 1990.
Local variables were stored in a dictionary, and lookups used the "LGB" (Locals, Globals, Builtins) lookup rule.
This was nice and simple.

Unfortunately it was also very slow.
Soon (I don't recall when exactly) we redesigned variable lookup in functions to rely on a simple form of scope analysis in the compiler.
The namespace for function locals is now implemented as an array, and the compiler assigns each local variable a unique index in this array.
This is done by a pass over the function body that collects all assignments (in the wider sense mentioned above), and honoring `global` declarations.
(Nothing changed for globals and builtins.)

When this redesign was done, we changed the semantics, to make things easier for the bytecode compiler and interpreter!
The "LGB" search at runtime was abandoned (or better, moved to the compiler).
Under the new rule, for any variable found to be a local, *only* the "slot" in the local namespace (i.e., the array mentioned above indexed by the variable's index) is checked at runtime.
If the slot is empty (in CPython, `NULL`), the interpreter doesn't search the global and builtin namespaces -- it just raises `UnboundLocalError`.

I don't recall whether this semantic change was entirely by choice, or if it was simply expedient for the implementation.
Apparently backward compatibility was a small price to pay.
(True, `LOAD_FAST` is still one of the fastest bytecodes. :-)
In any case, it's too late to change (backward compatibility is the law now :-).

On top of this, in Python 2.1, we implemented a new feature, *nested scopes*, that led to the modern "LEGB" lookup rule -- at compile time.
The implementation used something called *cells*, but for the formal description of scopes we don't need those (they are only an optimization).
Other (later) additions included the `nonlocal` declaration (added in Python 3.0 by PEP 3014) and the peculiar scoping rules for comprehensions, and later the walrus.

Anyway, the point of this blog is to write down the exact scoping rules in unambiguous code.

This is where the the `ClosedScope` class becomes relevant.
`FunctionScope`, `LambdaScope` and `ComprehensionScope` are just marker classes, they don't add new functionality beyond `ClosedScope`.
The `store()`, `add_nonlocal()` and `add_global()` methods are also unchanged from before.
The only difference is the `lookup()` method, which has to implement `LEGB`.
Here's the code:

```py
class ClosedScope(Scope):
    parent: Scope  # Cannot be None

    def lookup(self, name: str) -> Scope | None:
        if name in self.locals:
            return self
        elif name in self.globals:
            return self.global_scope()
        else:
            res: Scope | None = None
            p: Scope | None = self.enclosing_closed_scope()
            if p is None:
                res = None
            else:
                res = p.lookup(name)
            if name in self.nonlocals and not isinstance(res, ClosedScope):
                # res could be None or GlobalScope
                raise SyntaxError(f"nonlocal name {name!r} not found")
            else:
                return res
```

The `enclosing_closed_scope()` helper is defined recursively on the base class, `Scope`:

```py
class Scope:
    ...

    def enclosing_closed_scope(self) -> ClosedScope | None:
        if self.parent is None:
            return None
        elif isinstance(self.parent, ClosedScope):
            return self.parent
        else:
            return self.parent.enclosing_closed_scope()
```

I am fairly confident that the above code correctly describes scope lookups when starting in a function scope: in particular, enclosing class scopes are ignored.
(I was 100% confident until I found and fixed a bug. :-)

However. we need to adjust `OpenScope.lookup()`, because when a class is nested inside a function, that function's locals are visible in the class!
Here's the new and improved code:

```py
class OpenScope(Scope):
    def lookup(self, name: str) -> Scope | None:
        if name in self.locals:
            return self
        else:
            s = self.enclosing_closed_scope()
            if s is not None:
                return s.lookup(name)
            else:
                return self.global_scope()
```

And I think that's it, as far as the scopes themselves go.
You can check out the complete code: [scopes.py](scopes.py).

But of course there's more to scopes than lookup.
We also need to define the mapping from the AST to `Scope` instances, and that's slightly more involved.
I wrote the code, and I think it's decent, but I don't want to explain it from first principles.
You can look at it here: [build.py](build.py).

The basic idea is that there's a recursive function `build(node)` which takes an AST node and contains a big `match` statement (so it requires Python 3.10 or higher to run).
Especially important here is the default case:

```py
            case ast.AST():
                for key, value in node.__dict__.items():
                    if not key.startswith("_"):
                        self.build(value)
```

which matches any AST node type that isn't explicitly specified in an earlier case and just invokes `build() ` recursively for all public attributes.
Other cases mostly speak for themselves (atomic types are ignored, `Name` nodes are classified as loads or stores, and so on).
One interesting case handles the walrus, which contains some special code for comprehension scopes:

```py
            case ast.NamedExpr(target=target, value=value):
                # TODO: Various other forbidden cases from PEP 572,
                # e.g. [i := 0 for i in a] and [i for i in (x := a)].
                assert isinstance(target, ast.Name)
                self.build(value)
                s = self.current
                while isinstance(s, ComprehensionScope):
                    s = s.parent
                if isinstance(s, ClassScope):
                    raise SyntaxError("walrus in comprehension cannot target class")
                s.store(target.id)
```

The rest of the cases should speak for themselves.
Note for example that function annotations and argument default values are "evaluated" in the parent scope.
