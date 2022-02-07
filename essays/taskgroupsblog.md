# Developing TaskGroups for Python 3.11

GvR, Feb 2022

For 3.11 we want _task groups_ which are a watered down version of Trio _nurseries_.
Yury already implemented a `TaskGroup` class in EdgeDb, but it's undocumented, and I'd like to develop the ideal API from scratch, just for my personal education.

The typical use case is

```py
async with TaskGroup() as g:
    g.create_task(coro1())
    g.create_tasl(coro2())
print("All done")
```

The key functionality is that `TaskGroup()` is an async context manager, and is `__aexit__()` method waits for all the tasks to complete, so that `All done` is printed after both tasks have finished.
So the minimal version would be something like this (we'll refine it in steps below):

```py
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
        <wait for all the tasks>
```

The first question is, what to do in `__aexit__()`?
Perhaps the simplest, highest-level API in `asyncio` to wait for a bunch of tasks is `gather()`.
Let's try that:

```py
    async def __aexit__(self, typ, exc, tb):
        await asyncio.gather(*self.tasks)
```

And sure enough, it works!

Of course, the next question is, what if there are bugs or errors.
Some simple bugs would be things like trying to use a task group to create a task before the `async with` statement is entered, or while `__exit__()` is already running.
We could easily catch those by introducing some flag attributes, e.g. `self.entered` and `self.exiting`.
That's boring so I'll skip showing the code and move to errors.

What if one of the coroutines raises an exception?
In this case, `gather()` by default bubbles up the exception as soon as it happens, and cancels the other tasks.
Those seem useful semantics, but what if several of the tasks raise exceptions?
There's a flag to `gather()`, `return_exceptions=True`, which changes its behavior so that instead of raising on the first error, it returns the exception objects in the list of results.
Let's put a debugging `print()` call in too:

```py
    async def __aexit__(self, typ, exc, tb):
        print(await asyncio.gather(*self.tasks,
                                   return_exceptions=True))
```

This will print something like:

```
[ZeroDivisionError('division by zero'), 'coro2']
```

In Python 3.11 we can easily translate this into raising an `ExceptionGroup` that bundles all the exceptions.
(If there are no exceptions, we just throw away the return values; tasks shouldn't really have return values anyway.)

But.
We really want the other tasks to be cancelled when one of them fails.
That's the default behavior of `gather()`, and we like it.
(Also, this is what Trio nurseries do.)

Maybe we should just change `gather()` to raise an `ExceptionGroup`.
According to PEP 654 it's an API incompatibility if an API that used to raise exceptions is changed to raise `ExceptionGroup`, so we'd have to add a new flag to `gather()`, e.g. `raise_group=True`.
Then we could change our little `TaskGroup` class to use that:

```py
    async def __aexit__(self, typ, exc, tb):
        # This doesn't work yet
        await asyncio.gather(*self.tasks, raise_group=True)
```

Maybe that's all there is to implementing task groups?
Presumably when one task is cancelled, it will raise `asyncio.CancelledError`, which causes `gather()` to cancel all the other tasks.
And presumably when the `gather()` call itself is cancelled, it will also do that?
These are points to be researched.
But so far I like this!
