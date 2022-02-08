"""Build scope structure from AST."""

import ast
import contextlib
import os
import sys
import types
from typing import Iterator

from scopes import (
    ToplevelScope,
    ClassScope,
    ComprehensionScope,
    FunctionScope,
    GlobalScope,
    LambdaScope,
    Scope,
)

LOAD = ast.Load()
STORE = ast.Store()


class Builder:
    globals: GlobalScope
    current: Scope
    scopes: list[Scope]

    def __init__(self):
        self.globals = GlobalScope()
        self.current = ToplevelScope(self.globals)
        self.scopes = [self.globals, self.current]

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
            case ast.Nonlocal(names=names):
                for name in names:
                    self.current.add_nonlocal(name)
            case ast.Global(names=names):
                for name in names:
                    self.current.add_global(name)
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
            case ast.comprehension(target=target, ifs=ifs):
                self.build(target)
                # node.iter is built by the next two cases
                self.build(ifs)
            case ast.ListComp(elt=elt, generators=gens) | ast.SetComp(
                elt=elt, generators=gens
            ) | ast.GeneratorExp(elt=elt, generators=gens):
                self.build(gens[0].iter)
                name = f"<{node.__class__.__name__}>"
                with self.push(ComprehensionScope(name, self.current)):
                    self.build(elt)
                    self.build(gens)
                    self.build([g.iter for g in gens[1:]])
            case ast.DictComp(key=key, value=value, generators=gens):
                self.build(gens[0].iter)
                with self.push(ComprehensionScope(f"<DictComp>", self.current)):
                    self.build(key)
                    self.build(value)
                    self.build(gens)
                    self.build([g.iter for g in gens[1:]])

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


tab = "  "


def expand_globs(filenames: list[str]) -> Iterator[str]:
    for filename in filenames:
        if "*" in filename and sys.platform == "win32":
            import glob
            for fn in glob.glob(filename):
                yield fn
        else:
            yield filename


def main():
    dump = False
    files = sys.argv[1:]
    if files and files[0] == "-d":
        dump = True
        del files[0]
    if not files:
        files.append(os.path.join(os.path.dirname(__file__), "test.py"))
    for file in expand_globs(files):
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
            print(f"{indent}{scope}: L={sorted(scope.locals)}", end="")
            if scope.nonlocals:
                print(f"; NL={sorted(scope.nonlocals)}", end="")
            if scope.globals:
                print(f"; G={sorted(scope.globals)}", end="")
            uses = {}
            for name in sorted(scope.uses):
                uses[name] = scope.lookup(name)
            print(f"; U={uses}")


if __name__ == "__main__":
    main()
