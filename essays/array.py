def add(a: int, b: int) -> int:
    ...

def sub(a: int, b: int) -> int:
    ...

def panic(msg: str) -> None:
    ...

class Cell:
    head: object
    tail: "Cons"

    def __init__(self, head: object, tail: "Cons") -> None:
        self.head = head
        self.tail = tail

Cons = Cell | None

# We don't have generics, alas
class Array:
    first: Cons

    def __init__(self) -> None:
        self.first = None
    
    def len(self) -> int:
        n: int = 0
        it: Cons = self.first
        while it is not None:
            n = add(n, 1)
            it = it.tail
        return n
    
    def insert(self, pos: int, data: object) -> None:
        if pos < 0:
            panic("negative position")
        prev: Cons = None
        next: Cons = self.first
        while pos > 0:
            if next is None:
                return panic("position too large")
            pos = sub(pos, 1)
            prev = next
            next = next.tail
        cell: Cons = Cell(data, next)
        if prev is None:
            self.first = cell
        else:
            prev.tail = cell

    def append(self, data: object) -> None:
        self.insert(self.len(), data)

    def delete(self, pos: int) -> None:
        "delete item at pos (similar to insert)"
    
    def getitem(self, pos: int) -> object:
        next = self.first
        while pos > 0 and next is not None:
            pos = sub(pos, 1)
            next = next.tail
        if pos != 0 or next is None:
            panic("index out of range")
            return None
        return next.head
