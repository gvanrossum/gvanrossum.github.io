from __future__ import annotations

from typing import ClassVar, NoReturn as Never

Namespace = dict[str, object]


def TRANSFER(code: Code) -> Never:
    "Transfer control to code"


def CALCULATE_C3(bases: list[Class]) -> list[Class]:
    "Calculate MRO using C3 algorithm"


class InterpreterState:

    # A module may be any object
    modules: dict[str, object]

    builtins: Namespace

    # Threads have a unique integer ID (t.ident)
    threads: dict[int, ThreadState]

    # InterpreterState is a singleton
    instance: ClassVar[InterpreterState]


InterpreterState.instance = InterpreterState()


class ThreadState:
    istate: InterpreterState
    ident: int
    current_frame: Frame | None

    current_tstate: ClassVar[ThreadState]

    _id_counter: int = 0

    def __init__(self, istate: InterpreterState):
        self.istate = istate
        ThreadState._id_counter += 1
        self.ident = ThreadState._id_counter


ThreadState.current_tstate = ThreadState(InterpreterState.instance)


class Frame:
    tstate: ThreadState
    locals: Namespace  # Includes arguments and temporaries
    enclosing: Frame | None  # static, enclosing *closed* scope
    globals: Namespace  # Shared with other frames
    back: Frame | None  # dynamic, caller
    continuation: Code

    def __init__(self, func: Function):
        self.tstate = ThreadState.current_tstate
        self.locals = {}
        self.enclosing = func.enclosing
        self.globals = func.globals
        self.back = self.tstate.current_frame
        self.continuation = func.code

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
        self.mro = CALCULATE_C3(bases)

    # The truth is much more complicated,
    # e.g. __module__, __qualname__, metaclasses, slots (both kinds).


class Function:
    enclosing: Frame | None  # Level 1 nonlocals
    code: Code
    defaults: list[object]
    globals: Namespace

    def call(
        self, frame: Frame, args: list[object], kwds: dict[str, object]
    ):
        tstate = ThreadState.current_tstate
        frame = Frame(self)
        frame.locals[".args"] = args
        frame.locals[".kwds"] = kwds
        tstate.current_frame = frame
        TRANSFER(frame.continuation)


class Code:
    "All attributes private"
