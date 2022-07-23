import asyncio
from typing import Any, Awaitable, Type


class TaskGroup:
    def __init__(self):
        self.tasks: set[asyncio.Task[Any]] = set()
        self.errors: list[BaseException] = []
        self.aexit_waiting: asyncio.Event | None = None

    async def __aenter__(self):
        return self

    def create_task(self, coro: Awaitable[Any]) -> asyncio.Task[Any]:
        if self.errors:
            raise RuntimeError("Cannot create tasks after cancellation")
        if self.aexit_waiting is not None and self.aexit_waiting.is_set():
            raise RuntimeError("Too late to create another task")
        task = asyncio.get_event_loop().create_task(coro)
        task.add_done_callback(self.on_task_done)
        self.tasks.add(task)
        return task

    def on_task_done(self, task: asyncio.Task[Any]) -> None:
        self.tasks.remove(task)
        if task.cancelled():
            err: BaseException | None = asyncio.CancelledError()
        else:
            err = task.exception()
        if err is not None:
            if not self.errors:
                for t in self.tasks:
                    t.cancel()
            self.errors.append(err)
        if not self.tasks and self.aexit_waiting is not None:
            self.aexit_waiting.set()

    async def __aexit__(
        self, typ: Type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> None:
        self.aexit_waiting = asyncio.Event()
        if self.tasks:
            await self.aexit_waiting.wait()
        else:
            self.aexit_waiting.set()
        if self.errors:
            eg = BaseExceptionGroup("EG(TaskGroup)", self.errors)
            cancelled, other = eg.split(asyncio.CancelledError)
            if other is not None:
                raise other
            assert cancelled is not None
            raise BaseExceptionGroup(
                "EG(TaskGroup cancelled)", [asyncio.CancelledError()]
            )


def test_run():
    async def coro1():
        print("coro1: enter")
        await asyncio.sleep(0.1)
        print("coro1: crash")
        # raise asyncio.CancelledError
        1 / 0  # Crash
        print("coro1: exit")
        return "coro1"

    async def coro2():
        try:
            print("coro2: enter")
            await asyncio.sleep(0.2)
            print("coro2: exit")
        except asyncio.CancelledError:
            print("coro2: cancelled")
            raise
            return "coro2-cancelled"
        return "coro2"

    async def main():
        async with TaskGroup() as g:
            g.create_task(coro1())
            g.create_task(coro2())
        print("All done")

    try:
        asyncio.run(main())
    except Exception as err:
        print("Caught", err)
        raise
    print("Really done")


test_run()
