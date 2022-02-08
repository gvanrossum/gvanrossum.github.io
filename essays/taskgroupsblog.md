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

[tg1]: tg1.py

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
Some simple bugs (in the usage of task groups) would be things like trying to use a task group to create a task before the `async with` statement is entered, or while `__exit__()` is already running.
We could easily catch those by introducing some flag attributes, e.g. `self.entered` and `self.exiting`.
Also, Trio nurseries don't seem to consider that a bug.
Anyway, I'll skip checking for these bugs for now.

So, errors.
What if one of the coroutines raises an exception?
In this case, `gather()` by default bubbles up the exception as soon as it happens, leaving the other tasks running, unwaited-for.
And what if several of the tasks raise exceptions?
There's a flag to `gather()`, `return_exceptions=True`, which changes its behavior so that instead of raising on the first error, it returns the exception objects in the list of results.
In this case it waits for all tasks to finish or error out.
Let's put a debugging `print()` call in too:

```py
    async def __aexit__(self, typ, exc, tb):
        print(await asyncio.gather(*self.tasks,
                                   return_exceptions=True))
```

This will print something like:

```
[ZeroDivisionError('division by zero'), None]
```

In Python 3.11 we can easily translate this into raising an `ExceptionGroup` that bundles all the exceptions (if any).
For example:

[tg2]: tg2.py

```py
    async def __aexit__(self, typ, exc, tb):
        res = await asyncio.gather(*self.tasks,
                                   return_exceptions=True)
        errors = [r for r in res
                    if isinstance(r, BaseException)]
        if errors:
            raise BaseExceptionGroup("EG(TaskGroup)", errors)
```

We could probably just add that functionality to `gather()`.
According to PEP 654 it's an API incompatibility if an API that used to raise exceptions is changed to raise `ExceptionGroup`, so we'd have to add a new flag to `gather()`, e.g. `raise_group=True`.
Then we could change our little `TaskGroup` class to use that:

[tg3]: tg3.py

```py
    async def __aexit__(self, typ, exc, tb):
        # This doesn't work yet
        await asyncio.gather(*self.tasks, raise_group=True)
```

However, we really want the other tasks to be cancelled when one of them fails.
This is what Trio nurseries do.
Trio is big on usability, and I'm sure they have thought a lot about the ergonomics of the situation.

Do we make that another flag to `gather()`?
I'd worry that this would weigh `gather()` down with too many different types of behavior to document and implement correctly, so let's say that that's specific to task groups.
We can't just subsume all of `gather()`'s functionality into task groups; `gather()` exists to collect the results from its arguments, but task groups have nowhere to put the API for that.

We could also look into other waiting primitives, like `asyncio.wait()` or `asyncio.as_completed()`.
Here's the code with `wait()`:

[tg4]: tg4.py

```py
    async def __aexit__(self, typ, exc, tb):
        done, pending = await asyncio.wait(self.tasks)
        assert not pending
        assert done == set(self.tasks)
        errors = [err for task in done
                      if (err := task.exception())]
        if errors:
            raise BaseExceptionGroup("EG(TaskGroup)", errors)
```

This is slightly longer than the `gather()` version only because I added assertions -- IIRC the `pending` return value is empty unless a timeout is specified, but you never know.
But it has the same problem too: it doesn't give us a way to cancel all other tasks when one task raises an exception.

It looks like `as_completed()` can do that, though:

[tg5]: tg5.py

```py
    async def __aexit__(self, typ, exc, tb):
        errors = []
        for fut in asyncio.as_completed(self.tasks):
            try:
                await fut
            except BaseException as err:
                errors.append(err)
                for t in self.tasks:
                    t.cancel()
        if errors:
            raise BaseExceptionGroup("EG(TaskGroup)", errors)
```

(Note that the `t.cancel()` call is a no-op if `t` is already done or cancelled.)

We may get a ton of `asyncio.CancelledError` instances in the exception group, if there are many tasks that get cancelled.
We probably want to ignore those.
(Subtle: what if the first error is a cancellation?)
Also, we probably should not cancel tasks more than once, so we would need a flag to keep track of that.
(Actually, we could just check whether `errors` was empty or not.)

A final requirement is that if the task containing the `async with` statement (the "parent task") itself is cancelled, that cancellation should be propagated into all tasks managed by the `TaskGroup`.
Does `as_completed()` do this?
I don't recall how we did this in the beginning, I can't find it in the docs, and the code is complex.
A little experiment makes me think that this works though, so we really should be able to do it this way.
I end up with this version:

[tg6]: tg6.py

```py
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
                                     [CancelledError])
```

This ignores `CancelledError` if there are also other errors, and raises an exception group of a single (fresh) `CancelledError` if there are only `CancelledError` errors.
There are other choices though, and we're not quite done.

- We totally ignore the `typ, exc, tb` arguments, which means that a plain old exception raised in the `async with` block is ignored unless all tasks already created succeed.
- We don't distinguish between "spontaneous cancellation" (the first exception caught is `CancelledError`) and cancellation due to the `t.cancel()` calls.
- We still don't do anything special when the parent task is cancelled.

All these could be addressed, and at that point our implementation's complexity approaches that of EdgeDb's.
I do have some open questions for Yury and Irit:

- Is it worth the extra flag to prevent `create_task()` calls before `__aenter__()` is called? I can't tell whether Trio forbids this.
- Should we prevent `create_task()` calls after `__aexit__()` is called? I don't believe Trio does (but I didn't try).
- Is the implementation using `as_completed()` simpler than EdgeDb's version, which does everything using callbacks? Or does this just hide more edge cases?
- When the parent task is cancelled, should we end up just raising `CancelledError`, or should that be wrapped in an exception group too?
- If the first exception caught is `CancelledError`, but the parent task wasn't cancelled, what should we do? (Can we even tell the difference?)

(I suppose I could read the EdgeDb implementation more carefully and find some of the answers. Maybe later.)
