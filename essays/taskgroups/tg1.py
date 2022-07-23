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
        await asyncio.gather(*self.tasks)


def test_run():
    async def coro1():
        print("coro1: enter")
        await asyncio.sleep(0.1)
        print("coro1: exit")
    async def coro2():
        print("coro2: enter")
        await asyncio.sleep(0.2)
        print("coro2: exit")
        
    async def main():
        async with TaskGroup() as g:
            g.create_task(coro1())
            g.create_task(coro2())
        print("All done")
    
    asyncio.run(main())


test_run()
