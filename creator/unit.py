# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.macro
import creator.utils
import creator.target
import os
import weakref


class UnitNotFoundError(Exception):
  pass


class Workspace(object):
  """
  The *Workspace* is basically the root of a *Creator* build session.
  It manages loading unit scripts and contains the global macro context.

  Attributes:
    path (list of str): A list of directory names in which unit scripts
      are being searched for. The unit scripts will actually also be
      searched in subdirectories of the specified paths.
    context (ContextProvider): The global macro context.
    units (dict of str -> Unit): A dictionary that maps the full
      identifier of a :class:`Unit` to the actual object.
  """

  def __init__(self):
    super(Workspace, self).__init__()
    self.path = ['.', os.path.join(os.path.dirname(__file__), 'builtins')]
    self.path.extend(os.getenv('CREATORPATH', '').split(os.pathsep))
    self.context = WorkspaceContext(self)
    self.units = {}

  def find_unit(self, identifier):
    """
    Searches for the filename of a unit in the search :attr:`path`.

    Args:
      identifier (str): The identifier of the unit to load.
    Returns:
      str: The path to the unit script.
    Raises:
      UnitNotFoundError: If the unit could not be found.
    """

    filename = identifier + '.crunit'
    for dirname in self.path:
      if not os.path.isdir(dirname):
        continue
      path = os.path.join(dirname, filename)
      if os.path.isfile(path):
        return path
      for item in os.listdir(dirname):
        path = os.path.join(dirname, item, filename)
        if os.path.isfile(path):
          return path

    raise UnitNotFoundError(identifier)

  def load_unit(self, identifier):
    """
    If the unit with the specified *identifier* is not already loaded,
    it will be searched and executed and saved in the :attr:`units`
    dictionary.

    Args:
      identifier (str): The identifier of the unit to load.
    Returns:
      Unit: The loaded unit.
    Raises:
      UnitNotFoundError: If the unit could not be found.
    """

    if identifier in self.units:
      return self.units[identifier]

    filename = self.find_unit(identifier)
    unit = Unit(os.path.dirname(filename), identifier, self)

    # For all macros defined globally that access a namespace,
    # transfer them to the unit now.
    unit_access = identifier + ':'
    for key, value in list(self.context.macros.items()):
      if key.startswith(unit_access):
        del self.context[key]
        key = key[len(unit_access):]
        unit.context[key] = value

    self.units[identifier] = unit
    try:
      unit.run_unit_script(filename)
    except Exception:
      del self.units[identifier]
      raise
    return unit


class Unit(object):
  """
  A *Unit* represents a collection of macros and build targets. Each
  unit has a unique identifier and may depend on other units. All units
  in a :class:`Workspace` share the same global macro context and each
  has its own local context as well as a local mapping of unit aliases
  and target declarators.

  Attributes:
    project_path (str): The path of the units project directory.
    identifier (str): The full identifier of the unit.
    workspace (Workspace): The workspace the unit is associated with.
    context (ContextProvider): The local context of the unit.
    aliases (dict of str -> str): A mapping of alias names to fully
      qualified unit identifiers.
    targets (dict of str -> creator.target.Target): A dictionary
      that maps the name of a target to the target object.
    scope (dict): A dictionary that contains the scope in which the unit
      script is being executed.
  """

  # You can change this on a unit instance to change the behaviour
  # of the target() function which creates an instance of this class.
  ShellTargetCls = creator.target.ShellTarget

  def __init__(self, project_path, identifier, workspace):
    super(Unit, self).__init__()
    self.project_path = project_path
    self.identifier = identifier
    self.workspace = workspace
    self.context = UnitContext(self)
    self.aliases = {}
    self.targets = {}
    self.scope = self._create_scope()

  def _create_scope(self):
    """
    Private. Creates a Python dictionary that acts as the scope for the
    unit script which can be executed with :meth:`run_unit_script`.
    """

    def info(*args, **kwargs):
      items = []
      for arg in args:
        if isinstance(arg, str):
          arg = self.eval(arg, stack_depth=1)
        items.append(arg)
      print(*items, **kwargs)

    return {
      'unit': self,
      'workspace': self.workspace,
      'C': self.context,
      'G': self.workspace.context,
      'defined': self.defined,
      'target': self.target,
      'eval': self.eval,
      'load': self.load,
      'info': info,
      'split': creator.utils.split,
      'join': creator.utils.join,
      'foreach_split': self.foreach_split,
      'raw': creator.macro.TextNode,
    }

  def get_identifier(self):
    return self._identifier

  def set_identifier(self, identifier):
    if not isinstance(identifier, str):
      raise TypeError('identifier must be str', type(identifier))
    if not creator.utils.validate_identifier(identifier):
      raise ValueError('invalid unit identifier', identifier)
    self._identifier = identifier

  def get_workspace(self):
    return self._workspace()

  def set_workspace(self, workspace):
    if not isinstance(workspace, Workspace):
      raise TypeError('workspace must be Workspace instance', type(workspace))
    self._workspace = weakref.ref(workspace)

  identifier = property(get_identifier, set_identifier)
  workspace = property(get_workspace, set_workspace)

  def defined(self, name):
    """
    Returns:
      bool: True if a variable with the specified *name* is defined.
    """

    namespace, varname = creator.utils.parse_var(name)
    context = self.context
    if namespace:
      try:
        context = context.get_namespace(namespace)
      except KeyError:
        return False
    return context.has_macro(varname) or self.workspace.context.has_macro(name)

  def target(self, func):
    """
    Wraps a Python function and returns a :class:`creator.target.FuncTarget`
    object that will be filled with information by the wrapped function.
    Targets are filled after all unit scripts are loaded and not
    immediately when a script is run.
    """

    if not callable(func):
      raise TypeError('func must be callable', type(func))
    if func.__name__ in self.targets:
      raise ValueError('target "{0}" already exists'.format(func.__name__))
    target = self.ShellTargetCls(self, func.__name__, func)
    self.targets[func.__name__] = target
    return target

  def eval(self, text, supp_context=None, stack_depth=0):
    """
    Evaluates *text* as a macro string in the units context.

    Args:
      text (str): The text to evaluate.
      supp_context (creator.macro.ContextProvider): A context that
        will be taken into account additionally to the stack frame
        and unit context or None.
      stack_depth (int): The number of frames to go backwards from
        the calling frame to use the local and global variables from.
    Returns:
      str: The result of the evaluation.
    """

    macro = creator.macro.parse(text)
    context = creator.macro.ChainContext(self.context)
    if stack_depth >= 0:
      sf_context = creator.macro.StackFrameContext(stack_depth + 1)
      context.contexts.insert(0, sf_context)
    if supp_context is not None:
      context.contexts.insert(0, supp_context)
    return macro.eval(context, [])

  def load(self, identifier, alias=None):
    """
    Loads a unit script and makes it available globally. If *alias* is
    specified, an alias will be created in this unit that referers to
    the loaded unit.

    Args:
      identifier (str): The identifer of the unit to load.
      alias (str, optional): An alias for the unit inside this unit.
    Returns:
      Unit: The loaded unit.
    """

    unit = self.workspace.load_unit(identifier)
    if alias is not None:
      if not isinstance(alias, str):
        raise TypeError('alias must be str', type(alias))
      self.aliases[alias] = identifier
    return unit

  def foreach_split(self, inputs, outputs, stack_depth=0):
    """
    Shortcut for ``zip(split(eval(inputs)), split(eval(outputs)))``.
    """

    eval = self.eval
    inputs = creator.utils.split(eval(inputs, stack_depth=stack_depth + 1))
    outputs = creator.utils.split(eval(outputs, stack_depth=stack_depth + 1))
    return zip(inputs, outputs)

  def run_unit_script(self, filename):
    """
    Executes the Python unit script at *filename* for this unit.
    """

    with open(filename) as fp:
      code = compile(fp.read(), filename, 'exec', dont_inherit=True)
    self.scope['__file__'] = filename
    self.scope['__name__'] = '__crunit__'
    exec(code, self.scope)


class WorkspaceContext(creator.macro.MutableContext):
  """
  This class implements the :class:`creator.macro.ContextProvider`
  interface for the global macro context of a :class:`Workspace`.
  """

  def __init__(self, workspace):
    super().__init__()
    self._workspace = weakref.ref(workspace)

  @property
  def workspace(self):
    return self._workspace()

  def __setitem__(self, name, value):
    namespace, varname = creator.utils.parse_var(name)
    if namespace and namespace in self.workspace.units:
      self.workspace.units[namespace].context[varname] = value
    else:
      super().__setitem__(name, value)

  def has_macro(self, name):
    if super().has_macro(name):
      return True
    return name in os.environ

  def get_macro(self, name, default=NotImplemented):
    # First things first, check if a macro with that name was assigned
    # to this context.
    macro = super().get_macro(name, None)
    if macro is not None:
      return macro
    if name == 'Platform':
      return creator.macro.TextNode(creator.platform.platform_name)
    elif name == 'PlatformStandard':
      return creator.macro.TextNode(creator.platform.platform_standard)
    elif name == 'Architecture':
      return creator.macro.TextNode(creator.platform.architecture)
    if not name.startswith('_') and hasattr(creator.macro.Globals, name):
      return getattr(creator.macro.Globals, name)
    if name in os.environ:
      return creator.macro.TextNode(os.environ[name])
    raise KeyError(name)

  def get_namespace(self, name):
    return self.workspace.units[name].context


class UnitContext(creator.macro.MutableContext):
  """
  This class implements the :class:`creator.macro.ContextProvider`
  interface for the local macro context of a :class:`Unit`.
  """

  def __init__(self, unit):
    super().__init__()
    self._unit = weakref.ref(unit)
    self['ProjectPath'] = unit.project_path

  @property
  def unit(self):
    return self._unit()

  @property
  def workspace(self):
    return self._unit().workspace

  def get_aliases(self, name):
    return [name, self.unit.identifier + ':' + name]

  def get_macro(self, name, default=NotImplemented):
    macro = super().get_macro(name, None)
    if macro is None:
      macro = self.unit.workspace.context.get_macro(name, None)
    if macro is not None:
      return macro
    elif default is not NotImplemented:
      return default
    else:
      raise KeyError(name)

  def get_namespace(self, name):
    if name in self.unit.aliases:
      identifier = self.unit.aliases[name]
    else:
      identifier = name
    units = self.unit.workspace.units
    if identifier in units:
      return units[identifier].context
    return super().get_namespace(name)
