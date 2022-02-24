def f():
    x = 0
    def g():
        nonlocal x
        return x
