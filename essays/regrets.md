# Python Regrets (New Edition)

- Import is too complex
  (__import__, sys.path, sys.metapath, .pyc/.pyo,
  .dll/.pyd/.so, $PYTHONPATH, current directory, ...)

- Match/case exhaustiveness?

- Extreme introspection vs. evolvability

- Comprehensions vs. scopes

- Metaclasses are too complex (`__prepare__`, ...)

- Maybe 64-bit ints would have been sufficient? (32-bit wasn't!)

- ABI, object layout (e.g. refcount)

- 