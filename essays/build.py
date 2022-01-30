"""Build scope structure from AST."""

import ast
import sys
import types

from scopes import Scope, GlobalScope, FunctionScope, ClassScope

LOAD = ast.Load()
STORE = ast.Store()


class Builder:
    globals: GlobalScope
    current: Scope
    scopes: list[Scope]

    def __init__(self):
        self.globals = GlobalScope()
        self.current = self.globals
        self.scopes = [self.globals]

    def build(self, node: object | None) -> None:
        # TODO: MatchAs, who knows what else
        match node:
            case (
                None
                | str()
                | bytes()
                | bool()
                | int()
                | float()
                | complex()
                | types.EllipsisType()
            ):
                pass
            case list():
                for n in node:
                    self.build(n)
            case ast.Name(id=name, ctx=ast.Store()):
                self.current.store(name)
            case ast.Name(id=name, ctx=ast.Load()):
                self.current.load(name)
            case ast.Nonlocal(names=names) | ast.Global(names=names):
                for name in names:
                    self.current.add_nonlocal(name)
            case ast.ImportFrom(names=names):
                for a in names:
                    if a.asname:
                        self.current.store(a.asname)
                    elif a.name != '*':
                        self.current.store(a.name)
            case ast.Import(names=names):
                for a in names:
                    if a.asname:
                        self.current.store(a.asname)
                    else:
                        name = a.name.split('.')[0]
                        self.current.store(name)
            case ast.ExceptHandler(type=typ, name=name, body=body):
                self.build(typ)
                if name:
                    self.current.store(name)
                self.build(body)
            case ast.FunctionDef(
                name=name,
                args=args,
                body=body,
                decorator_list=decorator_list,
                returns=returns,
            ):
                self.build(decorator_list)
                self.build(args)  # Annotations and defaults
                self.build(returns)
                parent = self.current
                try:
                    self.current = FunctionScope(name, parent)
                    self.scopes.append(self.current)
                    for a in args.posonlyargs + args.args + args.kwonlyargs:
                        self.current.store(a.arg)
                    self.build(body)
                finally:
                    self.current = parent
                parent.store(name)
            case ast.ClassDef(
                name=name,
                bases=bases,
                keywords=keywords,
                body=body,
                decorator_list=decorator_list,
            ):
                self.build(decorator_list)
                self.build(bases)
                self.build(keywords)
                parent = self.current
                try:
                    self.current = ClassScope(name, parent)
                    self.scopes.append(self.current)
                    self.build(body)
                finally:
                    self.current = parent
                parent.store(name)
            case ast.AST():
                for key, value in node.__dict__.items():
                    if not key.startswith("_"):
                        self.build(value)
            case _:
                assert False, repr(node)


def depth(s: Scope) -> int:
    n = 0
    while s.parent is not None:
        n += 1
        s = s.parent
    return n


example = """
class C:
    def foo(self, a = b + 0.1):
        global x
        x = 1
        nonlocal y
        y = 0
"""

tab = "    "


def test():
    dump = False
    if sys.argv[1:] and sys.argv[1] == "-d":
        dump = True
        del sys.argv[1]
    if sys.argv[1:]:
        data = open(sys.argv[1]).read()
    else:
        data = example
    root = ast.parse(data)
    if dump:
        print(ast.dump(root, indent=2))
    b = Builder()
    b.build(root)
    for scope in b.scopes:
        indent = tab * depth(scope)
        print(f"{indent}{scope}: L={scope.locals}", end="")
        if scope.nonlocals:
            print(f"; NL={scope.nonlocals}", end="")
        if scope.globals:
            print(f"; G={scope.globals}", end="")
        print(f"; U={scope.uses}")


if __name__ == "__main__":
    test()
