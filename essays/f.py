import time

def timing(f, n, a):
    print f.__name__,
    r = range(n)
    t1 = time.clock()
    for i in r:
	f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a)
    t2 = time.clock()
    print round(t2-t1, 3)

def f1(list):
    string = ""
    for item in list:
	string = string + chr(item)
    return string

def f2(list):
    return reduce(lambda string, item: string + chr(item), list, "")

def f3(list):
    string = ""
    for character in map(chr, list):
	string = string + character
    return string

def f4(list):
    string = ""
    lchr = chr
    for item in list:
	string = string + lchr(item)
    return string

def f5(list):
    string = ""
    for i in range(0, 256, 16): # 0, 16, 32, 48, 64, ...
	s = ""
	for character in map(chr, list[i:i+16]):
	    s = s + character
	string = string + s
    return string

import string
def f6(list):
    return string.joinfields(map(chr, list), "")

import array
def f7(list):
    return array.array('B', list).tostring()

testdata = range(256)
print `testdata`
testfuncs = f1, f2, f3, f4, f5, f6, f7
for f in testfuncs: print f.func_name, f(testdata)
for f in testfuncs: timing(f, 100, testdata)
