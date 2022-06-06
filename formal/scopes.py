"""Python's scoping rules, as code.

There are lots of invariants and ideas not yet expressed in code:

- scopes form a tree with a GlobalScope at the root
- there are no GlobalScopes elsewhere in the tree
- *using* a name before a nonlocal declaration is also an error
- a way to check a scope's invariants
- locals/nonlocals/globals are disjunct
- everything about comprehensions
- translating the AST into a tree of scopes
- Using a subset of Python

"""


from __future__ import annotations

import sys
from typing import *
from typing_extensions import Self, TypeAlias
from abc import *
from enum import *

"""
Everything about scopes:

Every Scope corresponds to a module, a function, or a class.
	A function includes function defs, lambdas, and comprehensions.

Scopes form a tree, starting with a GlobalScope object.  Scope.nested is a list of the subtree Scopes.

A Scope has variables.  A variable (or 'var') is a name which is found in the scope.
	In the global scope, it may also be a name which is declared global in a nested scope.

It provides static status of various Var names seen in the scope.

A scope has a "ref" attribute, which is an arbitrary object supplied to the constructor.
This can be used by a builder function to build the scope and its nested scopes.
The nested scopes will have their own "ref" attributes.

Static status of a var.
	This involves a "binding scope" for the var, which is the same or an enclosing Scope.
	Status is one of the following, and may evolve while the scope is being examined:
		Unknown.  The var does not appear yet.
		Local.  A value is bound somewhere in the scope, including:
			assignment or reassignment,
			deletion,
			a walrus operator in a nested comprehension.
			This is only if var is not already declared nonlocal or global.
			The binding scope is the current scope
		Nonlocal.  The binding scope is a specific enclosing closed scope where the var is Local.
		Global.  The binding scope is the global scope.
		Top.  This is used instead of Local and Global in the global scope for a var that is bound there.
		Used.  The var appears in this scope but it not yet Local, Nonlocal, or Global.
			The binding scope is None.  The purpose of this status is to prevent further
			nonlocal or global declarations.
	Unknown will change to one of the others the first time the var is seen in the scope.
	Used will change to Local the first time the var is used in a binding situation.
	Used will change to Nonlocal or Global otherwise, some time after all uses of the var
		in the current scope have been reported.

Building the Scope: This consists of:
	1.	Note all names in the code for the scope,
		except for nested function and class defs:
			Do not include the body of the def, or any names (such as function
			arguments) which are known in the context of the nested scope.
			Create a scope object for the def.  This will be treated as an assignment
			of the def's name in the current scope.
			Do include other names appearing in the def statement other than the name,
			such as function default values, base classes, etc.
	2.	Do the entire build (recursively) on all the nested scopes.
			A walrus in a nested comprehension can change a var from Used to Local.
			If the binding scope is needed by some nested scope, then this can
			change the var from Used to Nonlocal or Global.
	3.	Resolve all remaining Used vars by finding the binding scopes for them, making them
		either Nonlocal or Global.

	This done with the Scope.build() method.

	It uses a builder function, which is stored in the Scope.builder attribute.
	This is provided to the global scope constructor.
	It is inherited by a nested scope, unless a different builder is provided.

	The function of the builder is to report any use of any var in the Scope which exists.
	It excludes any var which was reported to the parent Scope earlier.
	For functions, classes, and comprehensions,
		Report the nesting of a new scope.  For function and class defs, include the name,
		which will become bound in the current scope.
		Report vars occurring in the following:
			function argument defaults,
			class bases,
			class definition arguments,
			decorators.
			in comprehensions, all walrus operators at any level of nesting.
				If current scope is a class, this is a SyntaxError.

Operations on a Scope performed by its builder:
	Note, all enclosing scopes will have been completely built by this time.
	load(var).  Just reports the fact that this var appears.
	add_global(var).  Declares the var to be in the global scope.
		If earlier loaded in a non-global scope, this is an error.
		Also adds a load(var) to the global scope.
	add_nonlocal(var).  Declares the var to be in an enclosing closed scope.
		If earlier loaded, or the enclosing scope is not found, this is an error.
	store(var).  Notes the fact that the var has been assigned, reassigned or deleted.
	store_walrus(var):  Records an assignment via := operator contained somewhere in an
		immediately nested comprehension.  Same as store(), except SyntaxError in
		certain cases.

	nest(...).  Notes a nested Scope.  Creates a Scope for it and stores the name as well.
		Arguments provided:
			A subclass of Scope to be used.
			A ref object.
			An optional name, for function and class defs only.
			An optional builder for the new Scope, defaults to the builder of the current scope.

After the Scope's builder is complete, these operations are valid:

	binding_scope(var).  Returns the binding scope for the var, if any.
		If one exists for the var, that scope is returned.
		Else the var is Used or Unknown.  The scope is found by looking at enclosing scopes.
			If found, then this is stored in this scope, which makes it Nonlocal or Global.
			If Global, then load(var) is performed on the global scope as well.
			If not found, returns None.

		These are the binding_scope resolution rules:
		1.	If the var is Local, returns itself.
		2.	The global scope returns itself.
		3.	An open scope returns the global scope.
		4.	A closed scope returns its nonlocal_scope() if there is one,
			otherwise returns the global scope.

	nonlocal_scope(var).  Looks for a closed scope which will match a nonlocal declaration
		in a nested scope, using the parent chain.

		These are the nonlocal_scope rules:
		1.	An open scope returns its parent.nonlocal_scope().
		2.	The global scope returns None.
		3.	A closed scope returns itself if var is Local,
			otherwise returns its parent.nonlocal_scope().

"""

RefT = TypeVar('RefT')
ScopeT: TypeAlias = 'Scope[RefT]'
BuildT = Callable[[ScopeT, RefT], None]

def null_builder(s: ScopeT, r: RefT): pass

class VarStatus(Enum):
	Unknown = 0			# name does not appear at all
	Used = auto()		# name appears in the scope but has no static scope
	Local = auto()		# name is in current scope, which is not the global scope
	Nonlocal = auto()	# name is in some scope other than current or global
	Global = auto()		# name is in global scope, which is not the current scope
	Top = auto()		# name is in the global scope which is also the current scope
						# is_local and is_global are both true

	def __bool__(self): return bool(self.value)
	@property
	def is_used(self): return self is self.Used
	@property
	def is_local(self): return self in (self.Local, self.Top)
	@property
	def is_nonlocal(self): return self is self.Nonlocal
	@property
	def is_global(self): return self in (self.Global, self.Top)
	@property
	def is_top(self): return self is self.Top

class Scope(Generic[RefT]):
	scope_name: str
	parent: Self | None
	global_scope: GlobalScope[RefT] = None

	# Mapping of variable names to their binding scopes, for every var that appears in this scope.
	# The location may be self, or some ancestor scope.  It is determined at compile time.
	# The var is Local in its binding scope, which means that in that scope, the var is mapped to itself.
	# The binding scope may temporarily be unknown, but this is eventually resolved by the time the
	# entire scope has been built.
	vars: Mapping[str, ScopeT | None]

	ref: RefT | None
	builder: BuildT
	nested: List[ScopeT]

	# True if this Scope, or any ancestor, is an "in" clause of a comprehension.
	# This makes the walrus operator illegal, as well as in all nested Scopes.
	no_walrus: bool = False

	is_master: ClassVar[bool] = False
	is_global: ClassVar[bool] = False
	is_class: ClassVar[bool] = False
	is_function: ClassVar[bool] = False
	is_comp: ClassVar[bool] = False

	@abstractmethod
	def __init__(self, scope_name: str, parent: Scope | None, *,
				 ref: RefT = None, build: BuildT = null_builder,
				 no_walrus: bool = False):
		self.scope_name = scope_name
		self.parent = parent
		self.global_scope = parent and parent.global_scope
		self.ref = ref
		self.builder = build
		self.vars = dict()
		self.nested = []
		self.vars = dict()
		if no_walrus or (parent and parent.no_walrus): self.no_walrus = True

	def __repr__(self) -> str:
		return f"{self.__class__.__qualname__}({self.scope_name!r})"
	
	def qualname(self, varname: str = '', *, sep: str = '.') -> str:
		""" Fully qualified name of this scope, or given variable name in this scope.
		Optional separator to replace '.'.
		Global scope is part of this name only if it has its own name.
		"""
		names = list(self.scope_names)
		if varname: names.append(varname)
		return sep.join(names)

	@property
	def scope_names(self) -> Iterator[str]:
		""" Iterator for names of self and enclosed scopes, from globals to self.
		Global scope is part of this only if it has its own name.
		"""
		yield from self.parent.scope_names
		yield self.scope_name

	def status(self, name: str) -> VarStatus:
		try: scope = self.vars[name]
		except KeyError: return VarStatus.Unknown
		if not scope: return VarStatus.Used
		if self is self.global_scope: return VarStatus.Top
		if scope is self: return VarStatus.Local
		if scope is self.global_scope: return VarStatus.Global
		return VarStatus.Nonlocal

	def load(self, name: str) -> Scope:
		""" Change from Unknown to Used, otherwise no change.  Returns static scope. """
		return self.vars.setdefault(name, None)

	def store(self, name: str) -> Scope:
		""" Marks the name as being stored in this, or some enclosing Scope.
		In case of global scope, marks the name there too.
		"""
		# Change from Unknown to Used, and get static scope.
		scope = self.load(name)
		if not scope:
			# Change from Used to Local (or Top)
			self.vars[name] = self
			return self
		if self.status(name) is VarStatus.Global:
			scope.store(name)
		return scope

	def store_walrus(self, name: str) -> Scope:
		""" store_walrus() is same as store(), except:
		1. In a ClassScope, it is implemented separately as a SyntaxError.
		2. Anywhere in a comprehension "in" clause, it is a SyntaxError.
		"""
		if self.no_walrus:
			raise SyntaxError('assignment expression cannot be used in a comprehension iterable expression')
		return self.store(name)

	def add_nonlocal(self, name: str) -> Scope:
		""" Change from Unknown to Nonlocal.  Return new static scope.
		SyntaxError if nonlocal scope not found, or if name is not already Nonlocal.
		GlobalScope overrides this method.
		"""
		status = self.status(name)
		if not status:
			# Name Unknown.  Change to Nonlocal, or error if nonlocal scope not found.
			scope = self.nonlocal_scope(name)
			if not scope:
				raise SyntaxError(f"no binding for nonlocal '{name}' found")
			self.vars[name] = scope
			return scope
		# Only Nonlocal is valid.
		if status.is_nonlocal:
			return self.vars[name]
		if status.is_global:
			# Global is an error.
			raise SyntaxError(f"name '{name}' is nonlocal and global")
		else:
			# Used is an error.
			raise SyntaxError("name '{name}' is used prior to nonlocal declaration")

	def add_global(self, name: str) -> Scope:
		""" Change from Unknown to Global or Top.  Return new static scope.
		Error if static scope is not global.
		"""
		status = self.status(name)
		if not status:
			# Name Unknown.  Change to Global
			scope = self.vars[name] = self.global_scope
			return scope
		# Only Global is valid.
		if status.is_global:
			return self.global_scope
		if status.is_nonlocal:
			# Nonlocal is an error.
			raise SyntaxError(f"name '{name}' is nonlocal and global")
		else:
			# Used is an error.
			raise SyntaxError("name '{name}' used prior to global declaration")

	def nest(self, cls: Type[Scope], name: str = None, *,
				 ref: RefT = None, build: BuildT | None = None) -> Self:
		""" Report a nested scope.  Create the Scope object.
		Report the name as assigned in the current scope, except for
			Lambda and Comprehension, which are anonymous.
		Optional keyword to provide builder, otherwise uses current builder.
		"""
		res = cls(name, self, ref=ref, build=build or self.builder)
		self.nested.append(res)
		return res

	def nonlocal_scope(self, name) -> ClosedScope | None:
		""" Try to find a nonlocal scope for a name in some enclosed scope.
		"""
		# Implemented differently in OpenScope, GlobalScope and ClosedScope
		raise NotImplementedError

	# Methods after static build is complete...

	def binding_scope(self, name: str) -> Scope | None:
		""" Tries to find the static scope, setting it if not already known.
		Only valid after all the above static methods have been called.
		"""
		# Implemented differently in NestedScope, GlobalScope.
		raise NotImplementedError

	def build(self):
		""" Builds entire tree statically, using the builder recursively.
		Nested scopes are built by the same or their own individual builders.
		"""
		# Phase 1, implemented by the builder.
		self.builder(self, self.ref)
		# Phase 2, build all the nested scopes.
		for nested in self.nested:
			nested.build()
		# Phase 3, resolve all Used names.
		for name, scope in self.vars.items():
			if scope: continue
			self.binding_scope(name)

class MasterScope(Scope):
	""" Container for all the modules in a program.
	Will be created for a GlobalScope's parent if one is not provided to it.
	"""
	is_master: ClassVar[bool] = True

	def __init__(self, **kwds):
		super().__init__('', None, **kwds)

	def add_module(self, name: str, **kwds) -> Self:
		self.nest(GlobalScope, name, **kwds)

class GlobalScope(Scope):
	parent: MasterScope | None

	is_global: ClassVar[bool] = True

	def __init__(self, name: str = '', *, parent: MasterScope = None, **kwds):
		super().__init__(name, parent or MasterScope(), **kwds)
		self.global_scope = self

	def add_nonlocal(self, name: str) -> None:
		raise SyntaxError("nonlocal declaration not allowed at module level")

	def add_global(self, name: str) -> None:
		return self.store(name)

	def binding_scope(self, name: str) -> Scope | None:
		""" Get the static scope for this name.
		It is always self, and the name is made Local.
		"""
		return self.store(name)

	def nonlocal_scope(self, name) -> None:
		return None

	@property
	def scope_names(self) -> Iterator[str]:
		return []


class NestedScope(Scope):
	""" Any Scope other than GlobalScope.  Subclasses are OpenScope and ClosedScope.
	"""
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
		self.parent.store(self.scope_name)

	def binding_scope(self, name: str) -> Scope | None:
		""" Find the static scope, setting it not already known.
		Only valid after all other static methods have been called.
		"""
		# Change Unknown -> Used.  Get static scope or None if Used.
		scope = self.load(name)
		if scope:
			return scope
		# Used.  Will be in a nonlocal scope, else in globals.
		scope = self.parent.nonlocal_scope(name)
		if not scope: scope = self.global_scope
		self.vars[name] = scope
		return scope

class OpenScope(NestedScope):

	def nonlocal_scope(self, name) -> ClosedScope | None:
		return self.parent.nonlocal_scope(name)

# For modules, exec and eval.  Provides a module name, otherwise unnecessary (??)
class ToplevelScope(Scope):
	parent: GlobalScope  # Cannot be None

	def __init__(self, parent: GlobalScope):
		super().__init__("<toplevel>", parent)


class ClassScope(OpenScope):
	parent: Scope  # Cannot be None
	is_class: ClassVar[bool] = True

	def _get_unbound(self, binding: Binding) -> VAL:
		""" Get value, or raise exception, for binding with no value.
		If it is a local name, then look in globals.
		"""
		if binding.scope is self:
			return self.global_scope.get(binding.name)
		binding.raise_error(self)

	def store_walrus(self, name: str) -> Scope:
		""" Reports the name as being used as lvalue in := operator in a directly nested comprehension.
		This is a syntax error.
		"""
		raise SyntaxError('assignment expression within a comprehension cannot be used in a class body')

class ClosedScope(NestedScope):
	parent: Scope  # Cannot be None

	def nonlocal_scope(self, name) -> ClosedScope | None:
		""" Change Unknown to Used.
		Return static scope if Local or Nonlocal, None if Global, go to parent if Used.
		"""
		scope = self.load(name)
		if scope is self.global_scope:
			return None
		if scope:
			return scope
		return self.parent.nonlocal_scope(name)

class FunctionScope(ClosedScope):
	is_function: ClassVar[bool] = True


class LambdaScope(FunctionScope):
	pass


class ComprehensionScope(FunctionScope):
	is_comp: ClassVar[bool] = True

def test():
	# Set up a sample program
	# class C:
	#   def foo(self, a = blah):
	#     global x
	#     x = a

	c = None
	foo = None
	def foo_build(scope: Scope, ref):
		scope.store("self")
		scope.store("a")
		scope.add_global("x")
	def c_build(scope: Scope, ref):
		nonlocal foo
		foo = scope.nest(FunctionScope, "foo", build=foo_build)
	def globals_build(scope: Scope, ref):
		nonlocal c
		c = scope.nest(ClassScope, "C", build=c_build)
	globals = GlobalScope(build=globals_build)
	globals.build()

	assert foo.binding_scope("C") is globals
	assert c.binding_scope("C") is globals

	assert foo.binding_scope("foo") is globals
	assert c.binding_scope("foo") is c

	assert foo.binding_scope("self") is foo
	assert c.binding_scope("self") is globals

	assert foo.binding_scope("a") is foo
	assert c.binding_scope("a") is globals

	assert foo.binding_scope("blah") is globals
	assert c.binding_scope("blah") is globals

	assert foo.binding_scope("x") is globals
	assert c.binding_scope("x") is globals


if __name__ == "__main__":
	test()
