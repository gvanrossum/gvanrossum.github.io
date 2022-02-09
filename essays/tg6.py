import asyncio

class TaskGroup:
    def __init__(self):
        self.tasks = []

    async def __aenter__(self):
        return self

    def create_task(self, coro):
        t = asyncio.get_event_loop().create_task(coro)
        self.tasks.append(t)
        return t

    async def __aexit__(self, typ, exc, tb):
        errors = []
        for fut in asyncio.as_completed(self.tasks):
            try:
                await fut
            except BaseException as err:
                if not errors:
                    for t in self.tasks:
                        t.cancel()
                errors.append(err)
        if errors:
            eg = BaseExceptionGroup("EG(TaskGroup)", errors)
            cancelled, other = eg.split(asyncio.CancelledError)
            if other is not None:
                raise other
            assert cancelled is not None
            raise BaseExceptionGroup("EG(TaskGroup cancelled)",
                                     [asyncio.CancelledError()])


def test_run():
    async def coro1():
        print("coro1: enter")
        await asyncio.sleep(0.1)
        print("coro1: crash")
        # raise asyncio.CancelledError
        1/0  # Crash
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
