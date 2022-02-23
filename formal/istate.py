from __future__ import annotations

from typing import Callable

Namespace = dict[str, object]


class Interpreter:

    # A module may be any object
    modules: dict[str, object]

    builtins: Namespace

    # Threads have a unique integer ID (t.ident)
    threads: dict[int, Thread]


class Thread:
    istate: Interpreter
    ident: int
    current_frame: Frame | None


class Frame:
    tstate: Thread
    locals: Namespace  # Includes arguments and temporaries
    enclosing: Frame | None  # static, enclosing *closed* scope
    globals: Namespace  # Shared with other frames
    back: Frame | None  # dynamic, caller
    continuation: Code | None

    def get_local(self, name: str) -> object:
        if name not in self.locals:
            raise UnboundLocalError
        return self.locals[name]

    def set_local(self, name: str, value: object) -> None:
        self.locals[name] = value

    def delete_local(self, name: str) -> None:
        if name not in self.locals:
            raise UnboundLocalError
        del self.locals[name]

    def get_name(self, name: str) -> object:
        if name in self.locals:
            return self.locals[name]
        return self.get_global(name)

    def set_name(self, name: str, value: object) -> None:
        self.locals[name] = value

    def delete_name(self, name: str, value: object) -> object:
        if name not in self.locals:
            raise NameError
        del self.locals[name]

    def get_global(self, name: str) -> object:
        if name in self.globals:
            return self.globals[name]
        if name in self.tstate.istate.builtins:
            return self.tstate.istate.builtins[name]
        raise NameError

    def set_global(self, name: str, value: object) -> None:
        self.globals[name] = value

    def delete_global(self, name: str) -> None:
        if name not in self.globals:
            raise NameError
        del self.globals[name]

    def _get_enclosing(self, level: int) -> Frame:
        f = self
        for _ in range(level):
            assert f.enclosing
            f = f.enclosing
        return f

    def get_nonlocal(self, level: int, name: str) -> object:
        f = self._get_enclosing(level)
        if name not in f.locals:
            raise NameError
        return f.locals[name]

    def set_nonlocal(self, level: int, name: str, value: object) -> None:
        f = self._get_enclosing(level)
        f.locals[name] = value

    def delete_nonlocal(self, level: int, name: str) -> None:
        f = self._get_enclosing(level)
        if name not in f.locals:
            raise NameError
        del f.locals[name]

    # Get nonlocal in class inside function (cf. LOAD_CLASSDEREF)
    def get_class_nonlocal(self, level: int, name: str) -> value:
        if name in self.locals:
            return self.locals[name]
        return self.get_nonlocal(level, name)


class Function:
    enclosing: Frame | None  # Level 1 nonlocals
    code: Code | None  # Continuation, unless exited
    defaults: list[object]


class Code:
    def call(self, f: Frame):
        ...
