"""Build scope structure from AST."""

import ast
from collections.abc import Sequence

import scopes

LOAD = ast.Load()
STORE = ast.Store()


class Builder:
    globals: scopes.GlobalScope
    current: scopes.Scope

    def __init__(self):
        self.globals = scopes.GlobalScope()
        self.current = self.globals

    def build(self, node: object | None) -> None:
        match node:
            case None | bool() | str() | int() | float() | complex():
                pass
            case list():
                for n in node:
                    self.build(n)
            case ast.Name(id=name, ctx=ast.Store()):
                self.current.store(name)
            case ast.Name(id=name, ctx=ast.Load()):
                self.current.load(name)
            case ast.FunctionDef(name=name, args=args, body=body, returns=returns):
                # TODO: decorator_list
                parent = self.current
                parent.store(name)
                self.build(args)  # Annotations and defaults
                self.build(returns)
                save_current = self.current
                try:
                    self.current = scopes.FunctionScope(name, parent)
                    for a in args.posonlyargs + args.args + args.kwonlyargs:
                        self.current.store(a.arg)
                    self.build(body)
                finally:
                    self.current = save_current
            case ast.ClassDef(name=name, bases=bases, keywords=keywords, body=body):
                # TODO: decorator_list
                parent = self.current
                parent.store(name)
                self.build(bases)
                self.build(keywords)
                save_current = self.current
                try:
                    self.current = scopes.ClassScope(name, parent)
                    self.build(body)
                finally:
                    self.current = save_current
            case ast.AST():
                for key, value in node.__dict__.items():
                    if not key.startswith("_"):
                        self.build(value)
            case _:
                assert False, repr(node)


example = """
class C:
    def foo(self, a = b + 0.1):
        global x
        x = 1
        nonlocal y
        y = 0
"""

def test():
    root = ast.parse(example)
    Builder().build(root)


if __name__ == "__main__":
    test()
