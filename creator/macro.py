# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import abc
import weakref


class ContextProvider(object, metaclass=abc.ABCMeta):
  """
  The *ContextProvider* is the interface class for rendering macros
  providing the data necessary, eg. the value of variables. Some macro
  functions, like ``$(wildcard ...)`, expect the context does provide
  a macro ``$ProjectPath`` which should provide the directory that
  contains the project files.
  """

  @abc.abstractmethod
  def has_macro(self, name):
    """
    Args:
      name (str): The name of the macro to check for existence.
    Returns:
      bool: True if the macro exists, False if not.
    """

    raise NotImplementedError

  @abc.abstractmethod
  def get_macro(self, name, default=NotImplemented):
    """
    Args:
      name (str): The name of the macro to retrieve.
      default (any): The default value to be returned if the macro
        can not be served. The default value is :class:`NotImplemented`
        which causes this function to raise a :class:`KeyError` instead.
    Returns:
      Macro: The macro associated with the specified *name*.
    Raises:
      KeyError: If there is no macro with the specified name and the
        *default* parameter has the value :class:`NotImplemented`.
    """

    raise NotImplementedError


class MutableContextProvider(ContextProvider):
  """
  This implementation of the :class:`ContextProvider` interface
  enables reading and writing macros via the Python ``__getitem__()``
  and ``__setitem__()`` interface and stores these internally. If a
  string is set with ``__setitem__()``, it will automatically be parsed
  into a :class:`Macro` and bound to this :class:`ContextProvider`.

  Attributes:
    macros (dict of str -> Macro): The internal dictionary mapping the
      macro names with the actual macro objects.
  """

  def __init__(self):
    super().__init__()
    self.macros = {}

  def __getitem__(self, name):
    return self.get_macro(name)

  def __setitem__(self, name, value):
    if isinstance(value, str):
      # TODO
      raise NotImplementedError('parsing of macros not implemented')
    elif isinstance(value, ExpressionNode):
      value = Macro(value, self)
    elif not isinstance(value, Macro):
      message = 'value must be str, ExpressionNode or Macro'
      raise TypeError(message, type(value))
    self.macros[name] = value

  def has_macro(self, name):
    return name in self.macros

  def get_macro(self, name, default=NotImplemented):
    if name in self.macros:
      return self.macros[name]
    elif default is not NotImplemented:
      return default
    else:
      raise KeyError(name)


class ExpressionNode(object, metaclass=abc.ABCMeta):
  """
  Base class for macro expression nodes that can be evaluated with
  a :class:`ContextProvider` and rendered to a string.
  """

  @abc.abstractmethod
  def eval(self, context, args):
    """
    Evaluate the expression node given the specified context and
    function call arguments into a string.

    Args:
      context (ContextProvider): The context to evaluate with.
      args (list of ExpressionNode): A list of arguments that should
        be taken into account for the evaluation.
    Returns:
      str: The evaluated macro.
    """

    raise NotImplementedError


class TextNode(ExpressionNode):
  """
  The *TextNode* simply evaluates into the same text it was initialized
  with. It does not the context to evaluate.
  """

  def __init__(self, text):
    if not isinstance(text, str):
      raise TypeError('text must be str', type(text))
    super().__init__()
    self.text = text

  def eval(self, context, args):
    return self.text


class Macro(object):
  """
  Container for a macro expression tree bound to a :class:`ContextProvider`.

  Attributes:
    node (ExpressionNode): The root node of the evaluation hierarchy.
    context (ContextProvider): The context that the macro is bound to.
  """

  def __init__(self, node, context):
    super().__init__()
    self.node = node
    self.context = weakref.ref(context)

  def get_node(self):
    return self._node

  def set_node(self, node):
    if not isinstance(node, ExpressionNode):
      raise TypeError('node must be ExpressionNode', type(node))
    self._node = node

  def get_context(self):
    return self._context()

  def set_context(self, context):
    if not isinstance(context, ContextProvider):
      raise TypeError('context must be ContextProvider', type(context))
    self._context = weakref.ref(context)

  node = property(get_node, set_node)
  context = property(get_context, set_context)

  def eval(self, args):
    """
    Evaluates the macro into a string.

    Args:
      args (list of ExpressionNode): A list of arguments that are passed
        to the evaluation of the macro. Without arguments, it is a simple
        variable expansion.
    Returns:
      str: The evaluated macro.
    """

    return self.node.eval(self.context, args)


def pure_text(text):
  """
  Creates a :class:`Macro` from the specified *text* that will evaluate
  into the exactly same text without variable expansion.

  Args:
    text (str): The text to create a macro for.
  Returns:
    Macro: The macro that will evaluate exactly into the specified *text*.
  """

  node = TextNode(text)
  return Macro(node, MutableContextProvider())
