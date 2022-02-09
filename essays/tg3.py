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
        # This doesn't work yet
        await asyncio.gather(*self.tasks, raise_group=True)


def test_run():
    async def coro1():
        print("coro1: enter")
        await asyncio.sleep(0.1)
        1/0  # Crash
        print("coro1: exit")
        return "coro1"
    async def coro2():
        try:
            print("coro2: enter")
            await asyncio.sleep(0.2)
            print("coro2: exit")
        except asyncio.CancelledError:
            print("coro2 cancelled")
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
