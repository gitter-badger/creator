# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.macro
import creator.utils
import os
import weakref


class Workspace(object):
  """
  The *Workspace* is basically the root of a *Creator* build session.
  It manages loading unit scripts and contains the global macro context.

  Attributes:
    context (ContextProvider): The global macro context.
    units (dict of str -> Unit): A dictionary that maps the full
      identifier of a :class:`Unit` to the actual object.
  """

  def __init__(self):
    super(Workspace, self).__init__()
    self.context = WorkspaceContextProvider(self)
    self.units = {}


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
  """

  def __init__(self, project_path, identifier, workspace):
    super(Unit, self).__init__()
    self.project_path = project_path
    self.identifier = identifier
    self.workspace = workspace
    self.context = UnitContextProvider(self)
    self.aliases = {}

  def get_identifier(self):
    return self._identifier

  def set_identifier(self, identifier):
    if not isinstance(identifier, str):
      raise TypeError('identifier must be str', type(identifier))
    if not creator.utils.validate_unit_identifier(identifier):
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


class WorkspaceContextProvider(creator.macro.MutableContextProvider):
  """
  This class implements the :class:`creator.macro.ContextProvider`
  interface for the global macro context of a :class:`Workspace`.
  """

  def __init__(self, workspace):
    super().__init__()
    self.workspace = weakref.ref(workspace)

  def has_macro(self, name):
    if super().has_macro(name):
      return True
    return name in os.environ

  def get_macro(self, name, default=NotImplemented):
    # First things first, check if a macro with that name was assigned
    # to this context.
    macro = super().get_macro(name, None)
    if macro is None:
      if name in os.environ:
        macro = creator.macro.pure_text(os.environ[name])
      else:
        raise KeyError(name)
    return macro


class UnitContextProvider(creator.macro.MutableContextProvider):
  """
  This class implements the :class:`creator.macro.ContextProvider`
  interface for the local macro context of a :class:`Unit`.
  """

  def __init__(self, unit):
    super().__init__()
    self.unit = weakref.ref(unit)
    self['ProjectPath'] = unit.project_path

  def has_macro(self, name):
    if super().has_macro(name):
      return True
    return self.unit.workspace.context.has_macro(name)

  def get_macro(self, name, default=NotImplemented):
    macro = super().get_macro(name, None)
    if macro is None:
      macro = self.unit.workspace.context.get_macro(name, None)
    if macro not None:
      return macro
    elif default is not NotImplemented:
      return default
    else:
      raise KeyError(name)
