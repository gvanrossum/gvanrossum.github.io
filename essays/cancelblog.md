# Thinking Alout About Cancel Scopes

GvR, Feb 2022

Trying to understand how Trio cancel scopes could work in asyncio (with or without [task groups](https://github.com/python/cpython/pull/31270)).

The basic idea is this:

```py
async def some_coro(args):
    <pre>
    async with Timeout(dt):
        <stuff>
    <post>
```

In this coroutine (executed as part of a task), `<stuff>` may take some time and if it takes more than `dt` seconds it should be cancelled.
If it finishes before the deadline it proceeds immediately to `<post>`.
The cancellation throws `CancelledError` into whatever is blocking and once that bubbles out again it raises `TimeoutError` (skipping `<post>`).
There are some variants, e.g. where instead of a duration an absolute deadline is given (similar to `loop.call_at()` vs. `loop.call_later()`), or where if everything is successfully cancelled the `async with` statement exits successfully (so `<post>` is executed even if `<stuff>` is cancelled).

How do we do this typically in asyncio?
If `<stuff>` is a single `await <future_or_task>` statement, we could use `wait()`:

```py
done, pending = asyncio.wait([<future_or_task>], timeout=dt)
if pending:
    for f in pending:
        f.cancel()
    raise TimeoutError
```

However, we should probably also wait for the cancelled items to actually complete their cancellation.
Most things respond to cancellation by either exiting cleanly or re-raising `CancelledError`, but sometimes some other error occurs.
(It's also possible that something ignores the cancellation and stubbornly keeps on going. In asyncio, we will just keep waiting; in Trio, such things keep getting cancelled as soon as they block in `await` again. There are pros and cons to each approach, but it's unlikely that we will change asyncio.)

But before we get excited about using `wait()`, it's not really a solution if `<stuff>` is something more complex.
Suppose we have this:

```py
def read_bytes(sock, n):
    # Read n bytes from socket, timeout in 10 seconds
    buf = b""
    nread = 0
    async with Timeout(10):
        while n > 0:
            data = await sock.recv(n - nread)
            nread -= len(data)
            buf += data
    return buf
```

The async context manager `Timeout(dt)` should roughly look like this:

```py
class Timeout:
    def __init__(self, dt):
        self.dt = dt
    
    async def __aenter__(self):
        self.task = asyncio.current_task()
        self.timer = asyncio.get_running_loop().call_later(
            self.dt, self.callback
        )
        self.did_cancel = False
        return self

    def callback(self):
        self.did_cancel = self.task.cancel()

    async def __aexit__(self, tp, ex, tb):
        self.timer.cancel()
        if ex is None:
            return
        if self.did_cancel and isinstance(ex, asyncio.CancelledError):
            raise TimeoutError from None
```

What could possibly go wrong? :-)

For simple cases this seems to work -- if `<stuff>` completes before the timeout, `<post>` executes, otherwise `TimeoutError` is raised.
If some other exception is raised inside `<stuff>`, that gets propagated.
I tried cancelling the task in `<stuff>` and that seems to have the desirable effect as well (in this case `CancelledError` is raised -- that's what the `did_cancel` flag is for).

What if we were to *nest* cancel scopes?
This seems to work reasonably too, even if I put `try` / `except TimeoutError` around the inner cancel scope.
(Maybe asyncio's "edge-triggered" cancellation saved the day here. The task is cancelled by the inner `Timeout` context manager, but since exactly one `await` call in the inner `<stuff>` receives the cancellation, the task happily continues afterwards, since the `CancelledError` is replaced by a `TimeoutError` by `__aexit__()`, and that `TimeoutError` is caught by the `except TimeoutError`.)

Maybe there's a problem in the interaction between cancel scopes and task groups?
I tried a task group inside a cancel group, and it appears to behave as expected.

So now let me read the code for [`async-timeout`](https://github.com/aio-libs/async-timeout/blob/master/async_timeout/__init__.py).
I don't see any surprises here (it's basically what I do above, with a bunch of convenience APIs).

Concluding, on the [question asked in the PR](https://github.com/python/cpython/pull/31270#issuecomment-1037360984):

> The problem arises when the task is cancelled as a whole and the timeout expires, both before the event loop has a chance to raise the cancellation exception in the task. How, then, do you know if you need to simply exit the timeout() context manager or the entire task?

I think the answer lies in the monkey-patching of the parent task to make its `cancel()` method set a new flag, `__cancel_requested__`, and the checking around it.
