import time

def timing(f, n, a):
    print f.__name__,
    r = range(n)
    t1 = time.clock()
    for i in r:
	f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a)
    t2 = time.clock()
    print round(t2-t1, 3)

def g1(string):
    return map(ord, string)

import array
def g2(string):
    return array.array('b', string).tolist()

testdata = reduce(lambda string, item: string + chr(item), range(256), "")
testfuncs = g1, g2
print `testdata`
for g in testfuncs: print g.func_name, g(testdata)
for g in testfuncs: timing(g, 100, testdata)
