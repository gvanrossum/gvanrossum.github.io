# Everything You Always Wanted to Know About Scopes But Were Afraid to Ask

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
In this case, the LEGB rule predicts the result, but the compiler and runtime have to jump through [hoops(https://github.com/python/cpython/blob/a0e55a571cf01885fd5826266c37abaee307c309/Python/ceval.c#L3089-L3123)] to make this happen given how [closures](https://en.wikipedia.org/wiki/Closure_(computer_programming)) are implemented in Python.

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

- Scope
  - OpenScope
    - GlobalScope
    - ClassScope
  - ClosedScope
    - FunctionScope
      - LambdaScope
    - ComprehensionScope

Scopes are organized in a tree using a `parent` link (there is no need for a list of children).
The parent is `None` for `GlobalScope` (and only for that).
There is no "builtin scope" -- Python's compiler doesn't care about it, and at runtime the builtin namespace is always chained from the global namespace.

