""" Emulation for the runtime concept of a namespace.

Namespaces form a tree, starting with RootNamespace, which has a RootScope.
Under that is a GlobalNamespace, which has a GlobalScope.

There are two ways to build the tree up to this point.
1.	Make a RootScope, make a RootNamespace with this scope.
	Call main namespace.add_module(optional name, key, etc.).
		This makes a GlobalScope and returns the new GlobalNamespace.
2.	Make a GlobalScope, which will create a RootScope as a parent.
	Call GlobalNamespace(this scope, optional key).

"""

from __future__ import annotations
from typing import *
from abc import *

from scopes import *

NsT = TypeVar('NsT', bound='Namespace')
ValT = TypeVar('ValT')
BuildT = Callable[[NsT, ScopeT, RefT, Iterator[ScopeT]], None]

def null_builder(space: NsT, scope: ScopeT, ref: RefT, nested: Iterator[ScopeT]): pass

class Namespace(Generic[RefT, ValT]):
	""" Abstract base class.
	Able to bind, rebind, or unbind identifiers.
	Associated with a Scope object.
	Part of a tree, where every Namespace other than the RootNamespace has a parent.
	A Namespace doesn't necessarily keep track of its children.  The client has the
	option of making an index of some or all of the children it creates.

	Namespaces are related to Scopes, which are regions of a python source.
	A Namespace has an associated Scope object.
	Scopes also form a tree, and the structure of the Namespace tree matches that of
	the Scope tree.  That is,

						RootNamespace        RootScope
							  ^                  ^
							 ...                 ...
	                      Namespace     -->    Scope
							  ^                  ^
							  |  parent          |  parent
						  Namespace     -->    Scope

	Variables and Bindings.

	Every Variable (or "var") is an occurrence of an identifier in the python source.
	It is is found in some particular Scope.
	As the program runs, the value of that Var can be asigned to it or
	removed from it.  In the latter case, the Var is "unbound".

	In the scopes.py module, the concept of "binding scope" is discussed.  For any var which
	appears in a "current scope", the binding scope is some enclosing Scope, possibly the
	same as the current scope.  The Namespace associated with the binding scope is known as
	the "binding namespace", and this namespace keeps track of the current value, if any,
	of that var.

	The Var is always Local in the binding scope.

	Now, a Binding is simply a container which is either "bound" or "unbound".
	If it is bound, it has a value (any python object).
	(Note, an unbound Binding is NOT the same as a having value of None).
	The attribute Binding.value can be gotten, set, or deleted.  If it is unbound, then
	get and delete will raise AttributeError.  bool(Binding) is True if bound, False if unbound.
  
	The Binding for the Var is stored in its binding namespace.  This is a runtime concept, not compile time.

	A Namespace contains a Binding for every Var which is local to its own Scope.

	The procedure for finding the binding namespace for a var from the current namespace is to go up the
	parent chain until finding the namespace whose scope is the binding scope.  See this diagram:

						binding namespace     -->      binding scope
						       ^                            ^
						       | 0 or more parents          | binding_scope(Var)
						current namespace     -->      current scope

	The current Namespace can get the value (or raise an exception) for a Var known to the
	current scope by delegating this operation to the binding namespace.
	This step is implemented differently in different types of namespaces (corresponding to
	different types of scopes).

	In a closed namespace (i.e. a function):
		The value, or the exception, is obtained from the Binding for the Var.
		If the Binding is bound, return its value.
		Else the exception will be UnboundLocalError if the current namespace is the binding namespace,
		otherwise it will be NameError.

	In an open namespace (i.e. a class):
		This will always be the current namespace as well, because python's scope resolution
		prevents it from being the binding namespace for something else.
		If the Binding is bound, return the value.
		Otherwise, the operation is delegated to global Namespace.

	In the global namespace (i.e. a module):
		If the Binding is bound, return the value.
		Otherwise, the operation is delegated to the main namespace.

	In the main namespace (i.e. the entire program):
		There is a mapping of builtin names to their values, taken from the program-wide builtins module.
		An alternate mapping can be provided to the main namespace constructor.
		This mapping is read-only and the values are always bound.
		If there a Binding for the Var, then it returns its value.
		Otherwise, it raises NameError.

	The current namespace sets the value of a Var, or unbinds the Var, by delegating this operation
	to the binding namespace.  It is never further delegated to a different namespace.
	In the binding namespace, the value of the binding for the Var is bound or unbound, respectively.

	Building a Namespace tree:

	This is a recursive operation, starting from a RootNamespace.  It uses a builder function, which
	will be provided by the client in constructing the GlobalNamespace.  The same builder can be used
	for all branches of the tree, but the client may also specify a different builder for a given branch.

	The builder function is called to process a namespace.  For convenience, it is also given:
		the reference object contained in the scope, and
		the nested scopes.  These are in the form of an iterator, so that the builder can get
			the nested scopes one at a time without needing a 'for' loop.
			An example would be a builderwhich traverses a syntax tree for the scope.
			Whenever it visits something which creates a nested scope, it can get the corresponding
			Scope object (assuming that the Scopes tree was build in the same order,
			such as by traversing the same syntax tree).

	The Namespace.nest() method does the recursive build of a nested namespace.  It is given:
		one of the nested scopes (or the iterator from which it gets the next scope),
		an optional key for indexing the new nested namespace in the current namespace, and
		an optional builder to use instead of self.
	The nested namespace is created, and the builder.build() method is called for it immediately.
	This is in contrast to building Scopes, where the build of a nested scope is delayed.

	"""
	scope: Scope
	parent: Namespace | None
	vars: Mapping[str, Binding[ValT]]
	# Optional place where client can find nested namespaces by name or some other key.
	nested: Mapping[object, Namespace]
	scope_class: ClassVar[Type[Scope]]
	builder: BuildT
	global_ns: GlobalNamespace | None

	def __init__(self, scope: Scope, parent: Namespace | None, *,
				 build: BuildT = null_builder, key: object = None):
		assert isinstance(scope, self.scope_class)
		self.scope = scope
		self.parent = parent
		if parent:
			assert scope.parent is parent.scope
			if key is not None:
				parent.nested[key] = self
			self.global_ns = parent.global_ns
		else:
			assert scope.parent is None
			self.global_ns = None

		# Create bindings for local names in the scope.
		self.vars = {}
		for var in scope.vars:
			self.vars[var] = Binding()
		self.builder = build
		self.nested = {}

	def build(self):
		""" Builds entire tree, using the builder recursively. """
		self.builder(self, self.scope, self.scope.ref, iter(self.scope.nested))

	# Methods called by the builder...

	def load(self, var: str) -> ValT:
		binding_ns = self._binding_namespace(var)
		binding = binding_ns._load_binding(var)
		if binding: return binding.value
		if self is binding_ns:
			raise UnboundLocalError(f"local variable '{var}' referenced before assignment")
		else:
			raise NameError(f"name '{var}' is not defined")

	def has(self, var: str) -> bool:
		""" True if there is a Binding for Var and the Binding is bound. """
		return bool(self._binding_namespace(var)._load_binding(var))

	def store(self, var: str, value: ValT) -> None:
		self._binding_namespace(var).vars[var].bind(value)

	# Same as store(), except in ComprehensionNamespace
	store_walrus = store

	def delete(self, var: str) -> None:
		if self.has(var):
			self._binding_namespace(var).vars[var].unbind()
			return
		# This will raise the appropriate exception.
		self.load(var)

	def nest(self, nested: ScopeT | Iterator[ScopeT], **kwds) -> NsT:
		""" Create a nested Namespace using a nested Scope. """
		if not isinstance(nested, Scope):
			nested = next(nested)
		newspace = self._nest_scope(nested, **kwds)
		newspace.builder(newspace, nested, nested.ref, iter(nested.nested))
		return newspace

	# Helper methods...

	def _binding_namespace(self, var: str) -> Namespace:
		scope: Scope = self.scope.vars[var]
		while True:
			if scope is self.scope: return self
			self = self.parent

	@abstractmethod
	def _load_binding(self, var: str) -> Binding | None:
		""" Find the Binding, if any, containing the value of Var.
		self is a binding namespace for Var, but the result might not always
		be the binding stored here.
		The main namespace is not a binding namespace, and is handled differently.
		"""
		...

	def _nest_scope(self, scope: ScopeT, build: BuildT = None, **kwds) -> NsT:
		""" Create a nested Namespace for given Scope. """
		cls: Type[NsT] = scope_to_ns.get(type(scope))
		if not cls:
			raise TypeError("Scope must be a standard Scope subclass, not 'type(scope).__name__'")
		return cls(scope, self, build=build or self.builder, **kwds)


class RootNamespace(Namespace):
	""" The environment for a program and its modules.
	Includes bindings for the builtins module.
	"""
	scope_class = RootScope

	def __init__(self, scope: RootScope = None):
		super().__init__(scope or RootScope(), None)

	def _load_binding(self, var: str) -> Binding | None:
		""" Find the Binding, if any, containing the value of Var.
		self is not a binding namespace.  There might or might not be a Binding for var.
		"""
		return self.vars.get(var)

	def add_module(self, name: str = '', key: object = None) -> GlobalNamespace:
		""" Create a nested GlobalNamespace, using a new GlobalScope. """
		return self._nest_scope(GlobalScope(name, parent=self.scope), key=key)

class GlobalNamespace(Namespace):
	scope_class = GlobalScope

	def __init__(self, scope: GlobalScope | None, parent: RootNamespace = None, **kwds):
		if not scope:
			scope = GlobalScope()
		super().__init__(scope, parent or RootNamespace(scope.parent), **kwds)
		self.global_ns = self

	def _load_binding(self, var: str) -> Binding | None:
		""" Find the Binding, if any, containing the value of Var.
		"""
		binding = self.vars.get(var)
		if binding: return binding				# Binding exists and is bound.
		# Else try the main namespace.
		return self.parent._load_binding(var)

class ClassNamespace(Namespace):
	scope_class = ClassScope

	def _load_binding(self, var: str) -> Binding | None:
		""" Find the Binding, if any, containing the value of var.
		"""
		binding = self.vars[var]
		if binding: return binding
		# Else try the global namespace.
		return self.global_ns._load_binding(var)

class FunctionNamespace(Namespace):
	scope_class = FunctionScope

	def _load_binding(self, var: str) -> Binding | None:
		""" Find the Binding, if any, containing the value of var.
		"""
		return self.vars.get(var)

class LambdaNamespace(FunctionNamespace):
	scope_class = LambdaScope

class ComprehensionNamespace(FunctionNamespace):
	scope_class = ComprehensionScope

	def store_walrus(self, var: str, value: ValT) -> None:
		self.parent.store(var, value)

scope_to_ns: Mapping[Scope, Namespace] = {}

for Ns in (
	RootNamespace,
	GlobalNamespace,
	ClassNamespace,
	FunctionNamespace,
	LambdaNamespace,
	ComprehensionNamespace,
	):
	scope_to_ns[Ns.scope_class] = Ns

class Binding(Generic[ValT]):
	""" The current value (if any) of a Var in a Namespace.
	"""
	# The value attribute only exists if the Binding is bound.
	value: ValT

	class Unbound: pass
	_unbound: Final = Unbound()					# Sentinel for constructor or bind().

	def __init__(self, value: ValT | Unbound = _unbound):
		if value is not self._unbound:
			self.value = value

	def __bool__ (self) -> bool:
		return hasattr(self, 'value')

	def bind(self, value: ValT | Unbound = _unbound):
		if value is not self._unbound:
			self.value = value
		else:
			self.unbind()

	def unbind(self):
		del self.value

	def __repr__(self) -> str:
		if self:
			return repr(self.value)
		else:
			return '<unbound>'

x = RootNamespace()

y = x.add_module('foo', key=42)

z = GlobalNamespace(GlobalScope('bar'), key=43)

x
