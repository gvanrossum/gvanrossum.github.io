# Semantics for generators

I took a break but I kept thinking about this idea I had for formal semantics of generators.
This will naturally lead to the semantics of async functions as well.

The key problem I am trying to solve is that it's hard to describe Python's formal semantics using some lower-level structured programming language.
Typically it's easy to propose a translation for various Python constructs into something lower-level: for example, `x = a + b` is translated to something like
`x = __add__(a, b)`.

Such translations are easily combined, so that translating things like
`a[k] = x + f(a, b + 1)`
is fairly straightforward: Basically, assuming your target language has function calls, most Python constructs are easy to translate.
In first approximation, this becomes
`__setitem(a, k, __add__(x, f(a, __add__(b, 1))))`.

However, for `yield` there are complications.
Take the latter example but replace `b + 1` with `yield b + 1`.
This would give us `a[k] = x + f(a, (yield b + 1))`.
Could the translation be as simple as
`__setitem(a, k, __add__(x, f(a, __yield__(__add__(b, 1)))))`?
Unfortunately that would require `__yield__()` to do something clever with stack frames in order to _suspend_ the current frame, _resume_ the "calling" frame (really the frame that called `__next__()` or `send()` on the generator object), and later _resume_ the current frame once another call to `__next__()` or `send()` is made (possibly from an entirely different call site).
Oh, and if `throw()` is called, `__yield__()` needs to raise an exception, of course.

The complication here is that we now need the target language (which might be something like C or Rust, or a very tiny subset of Python) to be able to manipulate stack frames in order to implement the _suspend_ and _resume_ operations.
If we were targeting a hypothetical "Tiny Python" language, it would seem that Tiny Python would need to have a `yield` primitive built-in.
(This is the conclusion that Brett Cannon comes to in his series of blog posts on [Unravelling Python](https://snarky.ca/tag/syntactic-sugar/).)

My solution may come as a surprise: I propose to use *threads*.
A proper Python implementation requires threads anyway, and given that OS primitives for thread management exist and are accessible from most languages, we might as well require Tiny Python to support threads.
(It is fine if it also has a GIL.
The GIL pretty much defines Python's [memory model](https://en.wikipedia.org/wiki/Memory_model_(programming)) anyway.)

So here's my proposal for generator semantics.
When a generator is started, conceptually a new thread is created and the generator executes in that thread.
A relatively simple synchronization object which I name an _exchange_ is used to ensure that the generator's thread is blocked until is is awakened by a `next()`, `send()` or `throw()` call, blocking the calling thread until the generator yields a value or raises an exception.

An exchange contains two symmetrical channels called _rendezvous_, one for input (i.e., _to_ the generator) and one for output (_from_ the generator).

```py
import threading

class Rendezvous:
    def __init__(self):
        self.lock = threading.Lock()
        self.lock.acquire()  # Default state is locked
        self.value = None
        self.full = False
    def put(self, value):
        assert self.lock.locked()
        assert not self.full
        self.value = value
        self.full = True
        self.lock.release()
    def get(self):
        self.lock.acquire()
        assert self.full
        value = self.value
        self.full = False
        return value
```

A rendezvous implements the synchronized transfer of a value from the consumer thread to the producer thread.
The producer calls `put()` and the consumer calls `get()`, and these calls may occur in either order.
If the consumer goes first, it is blocked until the producer releases the lock.
If the producer goes first, the value is buffered in the rendezvous (this may be somewhat unorthodox for a "rendezvous").

A rendezvous cannot handle multiple producers or consumers.
This is ensured by the exchange itself on the caller side (since there *might* be multiple concurrent attempts to call e.g. `next()` on the same generator).
On the generator side it is ensured statically -- exchanges are never shared between generators.

```py
class Exchange:
    def __init__(self):
        self.lock = threading.Lock()
        self.busy = False
        self.input = Rendezvous()
        self.output = Rendezvous()
    def put_request(self, value):
        with self.lock:
            if self.busy:
                raise ValueError
            self.busy = True
        self.input.put(value)
    def get_request(self):
        return self.input.get()
    def put_response(self, value):
        self.output.put(value)
    def get_response(self):
        value = self.output.get()
        with self.lock:
            self.busy = False
        return value
```

The values sent and received through the exchange are not unconstrained -- they represent the protocol that exists between a generator and its caller.
We'll call the protocol values _messages_.
Each protocol message is a `(flag, value)` tuple.
(Yeah, I know, ADTs would he handy here. :-)

For input messages (i.e., from caller to generator), `flag` is either `SEND`, `THROW` or `CLOSE`, and `value` is either the value being sent or the exception to be thrown (a `GeneratorExit` instance for `CLOSE`).

```py
import enum

class IQ(enum.Enum):
    SEND = 1
    THROW = 2
    CLOSE = 3
```


For output messages, `flag` can be `YIELD` or `RAISE`, and `value` is the yielded value or the raised exception.
(Remember, returning from a generator is the same as raising `StopIteration`.)

```py
class OQ(enum.Enum):
    YIELD = 4
    RAISE = 5
```

A protocol has a _grammar_, which describes which message types are allowed to occur in which order.
The input protocol's grammar can be summarized as follows:
```
SEND (SEND | THROW)* CLOSE
```
The initial `SEND` must have a value of `None`.

The output protocol's grammar is:
```
YIELD* RAISE
```
(Note that returning from a generator raises `StopIteration`.)

These grammars do not describe the interleaving of input and output messages.
Fortunately this is straightforward: input and output messages alternate, starting with input, and ending with output.
If the output stream terminates before the input stream has sent a `CLOSE` message, the input is terminated.
If the response to a `CLOSE` message is not `RAISE`, the generator is in violation of the protocol.
(In CPython, you can keep sending values and exceptions in this case.)

A generator wraps an exchange and ensures the protocols are followed.

```py
class Generator:
    def __init__(self):
        self.exchange = Exchange()
        self.starting = True
    def __next__(self):
        return self.send(None)
    def send(self, value):
        if self.starting:
            if value is not None:
                raise TypeError
            self.starting = False
        return self.__send(IQ.SEND, value)
    def throw(self, exc):
        return self.__send(IQ.THROW, value)
    def close(self):
        flag, value = self.__send(IQ.CLOSE, GeneratorExit())
        if flag == RAISE:
            if isinstance(value, (StopIteration, GeneratorExit)):
                return
        raise RuntimeError
    def __send(self, iflag, ivalue):
        self.exchange.put_request((iflag, ivalue))
        oflag, ovalue = self.exchange.get_request()
        if oflag == OQ.RAISE:
            raise ovalue
        else:
            return ovalue
```
