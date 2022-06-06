from __future__ import annotations

import sys, os
from contextlib import contextmanager
from io import StringIO
from typing import NamedTuple, Iterable, Iterator

from enum import *
import attrs

from scopes import(
	Scope,
	FunctionScope,
	ClassScope,
	GlobalScope,
	ComprehensionScope,
	BuildT as ScopeBuildT,
	)

from namespaces import(
	BuildT as NsBuildT,
	GlobalNamespace,
	)


# Parameters at the current level, will be saved/restored by various context managers.
level = 0

@contextmanager
def indent(lev: int):
	# Set the current level during the context.
	global level
	oldlevel = level
	level = lev
	yield
	level = oldlevel

# Writing the output file...
out = StringIO()
lineno = 1

def write(s: str):
	breaklines = [ 23 ]
	print('    ' * level + s, file=out)
	global lineno
	lineno += len(s.split('\n'))


class VarMode(Enum):
	""" Defines how a scope uses the variable 'x'.
	Except for LocalNoCapt, makes no restrictions on nested classes.
	"""
	Unused = 'none'
	Used = 'use'
	Nonlocal = 'nloc'		# x is declared nonlocal in the scope. If this is not allowed,
							# the Scope will be left as Unused, but the genenrated code will
							# verify that the nonlocal declaration is a syntax error.
	Global = 'glob'
	Local = 'loc'			# x will be bound in this scope by an assignment.
	LocalNoCapt = 'ncap'	# same, but nested scopes may not capture x.
							# used as a mode for a nested scope, nested.mode = Local and nested.nocapt = True.

	@classmethod
	def nocapt_modes(cls, nocapt: bool = True) -> Iterable[VarMode]:
		""" Gives all the possible modes, based on whether "no captures" is in effect,
		which defaults to True.
		"""
		if nocapt:
			yield cls.Unused
			yield cls.Global
			yield cls.Local
		else:
			yield from cls.__members__.values()

	@property
	def is_loc(self) -> bool:
		return self in (self.Local, self.LocalNoCapt)

	def name_sfx(self, name: str = '') -> str:
		""" Suffix for a scope name, optionally added to givenname. """
		if self is self.Unused: return name
		return f'{name}_{self.value}'

@attrs.define(frozen=True)
class ScopeParams:
	""" Everything the builder needs to know about building a scope,
	other than attributes of the scope itself.
	"""
	level: int				# How deep in the scope tree.  Global scope is level 0.
	depth: int				# How much deeper to make nested scopes.  0 means no nested.
	mode: VarMode			# How the varible 'x' will be used in this scope.
	nocapt: bool = False	# If true, restricts nested scopes to those that don't capture
							# 'x' from this scope.
	is_class: bool = False

	def nest(self, mode: VarMode, is_class: bool = False) -> ScopeParams:
		""" New object to go with a nested scope. """
		nocapt = self.nocapt
		if mode is mode.LocalNoCapt:
			nocapt = True
		return attrs.evolve(self,
				level=self.level + 1,
				depth=self.depth - 1,
				mode=mode,
				nocapt=nocapt,
				is_class=is_class,
				)

	def nested_params(self) -> Iterable[ScopeParams]:
		""" Characterizes all of the set of nested scopes to generate.
		Tuple of (is class, var type).
		At the bottom nesting level, the iterator is empty.
		"""
		if self.depth:
			for is_class in True, False:
				for mode in self.mode.nocapt_modes(self.nocapt):
					yield self.nest(mode, is_class)

"""
	Functions to initialize given Scope and create nested Scopes.  Does not include operating on
	the nested scopes

	Special functions for a function, or list comprehension, that stores a value in its parent.
"""

def build_scope(scope: Scope, ref: ScopeParams):
	""" Define the static properties of the scope and create (but do not build)
	the nested scopes.
	"""
	# Set the scope's status.  It is currently Unknown
	mode = ref.mode
	if mode is mode.Unused: pass
	if mode is mode.Used:
		scope.load('x')
	if mode is mode.Nonlocal:
		try: scope.add_nonlocal('x')
		# If nonlocal is not allowed, then leave this scope empty.
		except SyntaxError: return
	if mode.is_loc:
		scope.store('x')
	if mode is mode.Global:
		scope.add_global('x')

	# Make nested function and class scopes.  May be called twice.
	def makesubs(suffix: str = ''):
		for nested_ref in ref.nested_params():
			cls = (FunctionScope, ClassScope)[nested_ref.is_class]
			name = makename(nested_ref.is_class, ref.level, nested_ref.mode, suffix)
			scope.nest(cls, name, ref=nested_ref)

	makesubs()

	if mode.is_loc:
		# This scope does some binding operations, then makes a second set of nested scopes.

		# It needs a nested scope which will assign to x in the current scope.
		# We can use a Comprehension if possible, otherwise a Function.
		# It has a [x := ...] to assign to x, before the second set of nested scopes.
		if sys.version_info < (3, 8) or scope.is_class:
			scope.nest(FunctionScope, ref=ref.nest(VarMode.Unused), build=build_set_in_parent_scope)
		else:
			scope.nest(ComprehensionScope, ref=ref.nest(VarMode.Unused), build=build_comp_scope)

		makesubs('2')

def build_comp_scope(scope: ComprehensionScope, ref: ScopeParams):
	""" Define the static properties of the scope.  No nested scopes.
	""" 
	scope.store_walrus('x')

def build_set_in_parent_scope(scope: FunctionScope, ref: ScopeParams):
	""" Define the static properties of the scope.  No nested scopes.
	""" 
	scope.parent.store('x')

"""
	Functions to write code based on given Namespace, including nested Namespaces.

	Special functions for a function, or list comprehension, that stores a value in its parent.
"""

def build_ns(space: NsT, scope: Scope, ref: ScopeParams, nested: Iterator[ScopeT]):
	""" Write the python test file for this scope and nested scopes, in the correct order.
	This method is called recursively to generate nested scopes, therefore it cannot keep
	state in this Builder object.
	"""
	def maketest():
		try: value = space.load('x')
		except NameError: value = None
		write(f'try: test(x, {value!r}, {lineno})')
		write(f'except NameError: test(None, {value!r}, {lineno})')

	mode = ref.mode
	objname = scope.qualname(sep="_")
	# 1. Write the function/class definition line.
	if scope.is_class:
		write(f'class {objname}:')
	elif scope.is_function:
		write(f'def {objname}():')

	def writebody():
		""" Write the body of the scope.  This is a separate function in order to bail out early. """
		nonlocal mode
		with indent(ref.level):
			# 2. Write initial setup of the variable.
			if mode is mode.Unused:
				if ref.depth == 0:
					write('pass')
			if mode is mode.Used:
				pass
			if mode is mode.Nonlocal:
				status = scope.status('x')
				if status is status.Nonlocal:
					write(f'nonlocal x')
				else:
					# No nonlocal binding.  There are no enclosed scopes, but generate a test.
					write('# No enclosed binding exists.')
					write('try: compile("nonlocal x", "exec")')
					write(f'except: test(None, None, {lineno})')
					write(f'else: error("Enclosed binding exists", {lineno})')
					n = list(nested)
					assert not n
					return

			if mode.is_loc:
				pass
			if mode is mode.Global:
				write(f'global x')

			if mode is not mode.Unused:
				maketest()

			# 3. Write recursively the first, or only, set of nested scopes.
			for _ in ref.nested_params():
				space.nest(nested)
				#next(nested).build()

			if mode.is_loc:
				# 4. Write the modifications of the variable.

				value = scope.qualname('x')
				write(f'x = "{value}"')
				space.store('x', value)
				maketest()

				write('del x')
				space.delete('x')
				maketest()

				# Set it again.  This time use a nested scope.
				# It might be a list comprehension with a walrus.  Or it might be a function.
				nest = next(nested)
				if nest.is_comp:
					build = build_comp_ns
				else:
					build = build_set_parent_ns
				space.nest(nest, build=build)

				maketest()

				...
				# 5. Write recursively the second set of nested scopes.
				for _ in ref.nested_params():
					space.nest(nested)
	writebody()

	# 6. Call the function, if a function.
	if scope.is_function:
		write(f'{objname}()')

def build_comp_ns(space: ComprehensionNamespace, scope: ComprehensionScope, ref: ScopeParams, nested: Iterator[ScopeT]):
	""" Write code to store value in parent, using a walrus in a list comprehension.  There are no nested scopes.
	"""
	value: str = scope.parent.qualname('x')
	write(f'[x := _ for _ in ["{value}"]]')
	space.store_walrus('x', value)

def build_set_parent_ns(space: FunctionNamespace, scope: FuncionScope, ref: ScopeParams, nested: Iterator[ScopeT]):
	""" Write code to store value in parent, without a walrus in a list comprehension.  There are no nested scopes.
	"""
	value: str = scope.parent.qualname('x')
	# Before assignment expressions were introduced, or when parent is a class,
	# we need an explicit function to perform the store.
	# The method depends on whether the parent scope is a function, class, or global.
	write('def listcomp():')
	with indent(ref.level):
		if scope.parent.is_global:
			write('global x; ' f'x = "{value}"')
		if scope.parent.is_function:
			write('nonlocal x; ' f'x = "{value}"')
		if scope.parent.is_class:
			# For a class, it is necessary to find its stack frame and store in its locals.
			write(f'inspect.stack()[1].frame.f_locals["x"] = "{value}"')
	write('listcomp()')
	space.parent.store('x', value)

def makename(is_class: bool, level: int, mode: VarMode, suffix: str = ''):
	"Name for a nested scope, given the class of the scope and the current nesting level."
	name = 'aA'[is_class]
	name = chr(ord(name) + level)
	name += suffix
	return mode.name_sfx(name)

def gen(depth):
	""" Main function to write most of the output. """

	scope = GlobalScope(ref=ScopeParams(0, depth, VarMode.Local), build=build_scope)
	scope.build()
	ns = GlobalNamespace(scope, key=43, build=build_ns)
	ns.build()

print('Creating file "test.py"... ', end='', flush=True)

write(
'''from __future__ import annotations
import inspect
ntests = 0
def test(value: str | None, comp: str | None, lineno: int):
	if value != comp:
		raise ValueError(f'Line {lineno}: expected {comp!r}, got {value!r}.', lineno) from None
	global ntests
	ntests += 1
	if ntests % 1000 == 0:
		print(f'{ntests:5d}')

def error(msg: str, lineno: int):
	raise ValueError(f'Line {lineno}: {msg}.', lineno) from None

print('done')
print('Running tests. ')
''')
gen(4)

with open(f'{sys.path[0]}/test.py', 'w') as f:
	f.write(out.getvalue())
with open(f'{sys.path[0]}/test.py.txt', 'w') as f:
	f.write(out.getvalue())
print('done')
print('Importing file "test.py"... ', end='', flush=True)

try: import test
except ValueError as exc:
	print()
	msg, lineno = exc.args
	lines = out.getvalue().splitlines()
	print(*lines[max(lineno - 11, 0):lineno], sep='\n')
	print('---- ' + msg)
	print(*lines[lineno: lineno + 10], sep='\n')
else:
	print(' done')
	print(f'All {test.ntests} tests passed.')
