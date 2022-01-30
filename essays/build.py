"""Build scope structure from AST."""

import ast
import contextlib
import sys
import types
from typing import Iterator

from scopes import Scope, ClassScope, GlobalScope, FunctionScope, LambdaScope

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

    def store(self, name: str) -> None:
        self.current.store(name)

    @contextlib.contextmanager
    def push(self, scope: Scope) -> Iterator[Scope]:
        parent = self.current
        try:
            self.current = scope
            self.scopes.append(scope)
            yield scope
        finally:
            self.current = parent

    def build(self, node: object | None) -> None:
        # TODO: comprehensions, and walrus in comprehensions
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
                self.store(name)
            case ast.Name(id=name, ctx=ast.Load()):
                self.current.load(name)
            case ast.Nonlocal(names=names) | ast.Global(names=names):
                for name in names:
                    self.current.add_nonlocal(name)
            case ast.ImportFrom(names=names):
                for a in names:
                    if a.asname:
                        self.store(a.asname)
                    elif a.name != "*":
                        self.store(a.name)
            case ast.Import(names=names):
                for a in names:
                    if a.asname:
                        self.store(a.asname)
                    else:
                        name = a.name.split(".")[0]
                        self.store(name)
            case ast.ExceptHandler(type=typ, name=name, body=body):
                self.build(typ)
                if name:
                    self.store(name)
                self.build(body)
            case ast.MatchAs(name=name) | ast.MatchStar(name=name):
                if name:
                    self.store(name)
            case ast.Lambda(args=args, body=body):
                self.build(args)  # defaults
                with self.push(LambdaScope("<lambda>", self.current)):
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
                with self.push(FunctionScope(name, self.current)):
                    for a in args.posonlyargs + args.args + args.kwonlyargs:
                        self.store(a.arg)
                    self.build(body)
                self.store(name)
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
                with self.push(ClassScope(name, self.current)):
                    self.build(body)
                self.store(name)
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


tab = "    "


def test():
    dump = False
    if sys.argv[1:] and sys.argv[1] == "-d":
        dump = True
        del sys.argv[1]
    for file in sys.argv[1:]:
        print()
        print(file + ":")
        with open(file, "rb") as f:
            data = f.read()
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
