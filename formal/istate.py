from __future__ import annotations

from typing import Callable

Namespace = dict[str, object]


class InterpreterState:

    # A module may be any object
    modules: dict[str, object]

    builtins: Namespace

    # Threads have a unique integer ID (t.ident)
    threads: dict[int, ThreadState]


class ThreadState:
    istate: InterpreterState
    ident: int
    current_frame: Frame | None


class Frame:
    tstate: ThreadState
    locals: Namespace  # Includes arguments and temporaries
    enclosing: Frame | None  # static, enclosing *closed* scope
    globals: Namespace  # Shared with other frames
    back: Frame | None  # dynamic, caller
    continuation: Code | None

    def get_local(self, name: str) -> object:
        try:
            return self.locals[name]
        except KeyError:
            raise UnboundLocalError

    def set_local(self, name: str, value: object) -> None:
        self.locals[name] = value

    def delete_local(self, name: str) -> None:
        try:
            del self.locals[name]
        except KeyError:
            raise UnboundLocalError


    def get_name(self, name: str) -> object:
        try:
            return self.locals[name]
        except KeyError:
            return self.get_global(name)

    def set_name(self, name: str, value: object) -> None:
        self.locals[name] = value

    def delete_name(self, name: str, value: object) -> None:
        try:
            del self.locals[name]
        except KeyError:
            raise NameError

    def get_global(self, name: str) -> object:
        try:
            return self.globals[name]
        except KeyError:
            try:
                return self.tstate.istate.builtins[name]
            except KeyError:
                raise NameError

    def set_global(self, name: str, value: object) -> None:
        self.globals[name] = value

    def delete_global(self, name: str) -> None:
        try:
            del self.globals[name]
        except KeyError:
            raise NameError

    def _get_enclosing(self, level: int) -> Frame:
        f = self
        for _ in range(level):
            assert f.enclosing
            f = f.enclosing
        return f

    def get_nonlocal(self, level: int, name: str) -> object:
        f = self._get_enclosing(level)
        try:
            return f.locals[name]
        except KeyError:
            raise NameError

    def set_nonlocal(self, level: int, name: str, value: object) -> None:
        f = self._get_enclosing(level)
        f.locals[name] = value

    def delete_nonlocal(self, level: int, name: str) -> None:
        f = self._get_enclosing(level)
        try:
            del f.locals[name]
        except KeyError:
            raise NameError

    # Get nonlocal in class inside function (cf. LOAD_CLASSDEREF)
    def get_class_nonlocal(self, level: int, name: str) -> object:
        try:
            return self.locals[name]
        except KeyError:
            return self.get_nonlocal(level, name)


class Module:
    __name__: str
    __doc__: str | None
    __file__: str


class Class:
    name: str
    bases: list[Class]
    ns: Namespace
    mro: list[Class]

    def __init__(self, name: str, bases: list[Class], ns: Namespace):
        self.name = name
        self.bases = bases
        self.ns = ns
        self.mro = ...  # Calculated from bases using C4 algorithm

    # The truth is much more complicated,
    # e.g. __module__, __qualname__, metaclasses, slots (both kinds).


class Function:
    enclosing: Frame | None  # Level 1 nonlocals
    code: Code | None  # Continuation, unless exited
    defaults: list[object]
    globals: Namespace


class Code:
    def call(self, f: Frame):
        ...
