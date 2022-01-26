from __future__ import annotations

class Context:
    type: str

    def __init__(self, type: str):
        self.type = type
    
    def __repr__(self) -> str:
        return self.type

Load = Context("Load")
Store = Context("Store")

class Scope:
    scope_name: str
    stores: set[str]
    nonlocals: set[str]
    globals: set[str]
    bindings: set[str]
    parent: Scope | None

    def __init__(self, scope_name: str, parent: Scope | None):
        self.scope_name = scope_name
        self.stores = set()
        self.nonlocals = set()
        self.globals = set()
        self.bindings = set()  # TODO: Compute this
        self.parent = parent
    
    def __repr__(self) -> str:
        return f"Scope({self.scope_name!r})"
    
    def store(self, name: str) -> None:
        self.stores.add(name)
    
    def add_nonlocal(self, name: str) -> None:
        assert name not in self.globals
        self.nonlocals.add(name)
        self.store(name)
    
    def add_global(self, name: str) -> None:
        assert name not in self.nonlocals
        self.globals.add(name)
        self.store(name)

    def lookup(self, name: str) -> Scope | None:
        s = self
        is_nonlocal = False
        while s is not None:
            # print(f"  Looking for {name} in {s}")
            if name in s.stores and name not in s.globals and name not in s.nonlocals:
                return s  # It's a local
            if name in s.globals:
                assert not is_nonlocal
                # It's a global, skip to the global scope
                while not isinstance(s, GlobalScope):
                    s = s.parent
                return s
            if name in s.nonlocals:
                is_nonlocal = True
            s = s.parent
            # Skip class scopes after the first
            while isinstance(s, ClassScope):
                s = s.parent
        return None  # It's a global by default

class OpenScope(Scope):
    pass

class GlobalScope(Scope):
    def __init__(self):
        super().__init__("<globals>", None)

class ClosedScope(Scope):
    pass

class ClassScope(OpenScope):
    def __init__(self, name: str, parent: Scope):
        super().__init__(name, parent)
        parent.store(name)

class FunctionScope(ClosedScope):
    def __init__(self, name: str, parent: Scope):
        super().__init__(name, parent)
        parent.store(name)

# No rules distinguish between lambda and function scope
LambdaScope = FunctionScope

class ComprehensionScope(ClosedScope):
    pass

# Set up a sample program
# class C:
#   def foo(self, a = blah):
#     global x
#     x = a

globals = GlobalScope()
class_c = ClassScope("C", globals)
def_foo = FunctionScope("foo", class_c)
def_foo.store("self")
def_foo.store("a")
def_foo.parent.store("blah")
def_foo.add_global("x")

for name in "a", "self", "x", "blah", "C", "foo":
    print("The scope of", name, "in foo is", def_foo.lookup(name))
