"""Python's scoping rules, as code.

There are lots of invariants and ideas not yet expressed in code:

- scopes form a tree with a GlobalScope at the root
- there are no GlobalScopes elsewhere in the tree
- locals/nonlocals/globals are disjunct
- everything about comprehensions
- translating the AST into a tree of scopes
- Using a subset of Python

"""


from __future__ import annotations


class Scope:
    scope_name: str
    parent: Scope | None
    locals: set[str]
    nonlocals: set[str]
    globals: set[str]

    def __init__(self, scope_name: str, parent: Scope | None):
        self.scope_name = scope_name
        self.parent = parent
        self.locals = set()
        self.nonlocals = set()
        self.globals = set()
        # locals, nonlocals and globals are all disjunct

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.scope_name!r})"

    def store(self, name: str) -> None:
        if name in self.locals or name in self.nonlocals or name in self.globals:
            return
        self.locals.add(name)

    def add_nonlocal(self, name: str) -> None:
        if name in self.locals:
            raise SyntaxError("name assigned before nonlocal declaration")
        if name in self.globals:
            raise SyntaxError("name is global and nonlocal")
        self.nonlocals.add(name)

    def add_global(self, name: str) -> None:
        if name in self.locals:
            raise SyntaxError("name assigned before global declaration")
        if name in self.nonlocals:
            raise SyntaxError("name is nonlocal and global")
        self.globals.add(name)

    def global_scope(self) -> GlobalScope:
        # GlobalScope overrides this
        assert self.parent is not None
        return self.parent.global_scope()

    def enclosing_scope(self) -> ClosedScope | None:
        if self.parent is None:
            return None
        elif isinstance(self.parent, ClosedScope):
            return self.parent
        else:
            return self.parent.enclosing_scope()

    def lookup(self, name: str) -> Scope | None:
        # Implemented differently in OpenScope, GlobalScope and ClosedScope
        raise NotImplementedError


class OpenScope(Scope):
    def lookup(self, name: str) -> Scope | None:
        if name in self.locals:
            return self
        else:
            return self.global_scope().lookup(name)


class GlobalScope(OpenScope):
    def __init__(self):
        super().__init__("<globals>", None)

    def global_scope(self) -> GlobalScope:
        return self

    def lookup(self, name: str) -> Scope | None:
        if name in self.locals:
            return self
        else:
            return None

    def add_nonlocal(self, name: str) -> None:
        raise SyntaxError("nonlocal declaration not allowed at module level")

    def add_global(self, name: str) -> None:
        return self.store(name)


# For modules, exec and eval
ToplevelScope = OpenScope


class ClassScope(OpenScope):
    def __init__(self, name: str, parent: Scope):
        super().__init__(name, parent)
        parent.store(name)


class ClosedScope(Scope):
    def lookup(self, name: str) -> Scope | None:
        # TODO: If there's a nonlocal x, there must be an x in a closed scope;
        # otherwise, it may be global or missing.
        # (add_global() and add_nonlocal() already check for inconsistency.)
        if name in self.locals:
            return self
        elif name in self.globals:
            return self.global_scope()
        elif name in self.nonlocals:
            s = self.enclosing_scope()
            if s is None:
                raise SyntaxError("no enclosing scope for nonlocal")
            res = s.lookup(name)
            if res is None:
                raise SyntaxError("name not found in enclosing scope")
            return res
        else:
            t: Scope | None = self.enclosing_scope()
            if t is None:
                t = self.global_scope()
            return t.lookup(name)


class FunctionScope(ClosedScope):
    def __init__(self, name: str, parent: Scope):
        super().__init__(name, parent)
        parent.store(name)


# No rules distinguish between lambda and function scope
LambdaScope = FunctionScope


class ComprehensionScope(ClosedScope):
    # TODO
    pass


def test():
    # Set up a sample program
    # class C:
    #   def foo(self, a = blah):
    #     global x
    #     x = a

    globals = GlobalScope()
    c = ClassScope("C", globals)
    foo = FunctionScope("foo", c)
    foo.store("self")
    foo.store("a")
    foo.add_global("x")

    assert foo.lookup("C") is globals
    assert c.lookup("C") is globals

    assert foo.lookup("foo") is None
    assert c.lookup("foo") is c

    assert foo.lookup("self") is foo
    assert c.lookup("self") is None

    assert foo.lookup("a") is foo
    assert c.lookup("a") is None

    assert foo.lookup("blah") is None
    assert c.lookup("blah") is None

    assert foo.lookup("x") is globals
    assert c.lookup("x") is None


if __name__ == "__main__":
    test()
