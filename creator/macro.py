# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.utils
import abc
import glob
import nr.strex
import os
import string
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

    return False

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

    if default is NotImplemented:
      raise KeyError(name)
    return default

  @abc.abstractmethod
  def get_namespace(self, name):
    """
    Returns another :class:`ContextProvider` by name.

    Args:
      name (str): The name of the context to retrieve.
    Returns:
      ContextProvider: The context with the specified name.
    Raises:
      KeyError: If the context can not be served.
    """

    raise KeyError(name)


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
      value = Macro(parse(value), self)
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

  def get_namespace(self, name):
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

  Attributes:
    text (str): The text of the node.
  """

  def __init__(self, text):
    if not isinstance(text, str):
      raise TypeError('text must be str', type(text))
    super().__init__()
    self.text = text

  def eval(self, context, args):
    return self.text


class ConcatNode(ExpressionNode):
  """
  This expression node can contain a number of other nodes which are
  simply concatenated on evaluation. It also implements a parse-time
  performance improvement when appending raw text to the node as it
  will simply update the last :class:`TextNode` (if present) instead
  of creating a new node for each chunk.

  Attributes:
    nodes (list of ExpressionNode): The list of nodes.
  """

  def __init__(self):
    super().__init__()
    self.nodes = []

  def append(self, node):
    """
    Appends a :class:`ExpressionNode` or text to this node.

    Args:
      node (ExpressionNode or str): The node or text to add.
    """

    if type(node) is TextNode:
      text = node.text
    elif isinstance(node, str):
      text = node
      node = None
    else:
      text = None

    if text is not None:
      if self.nodes and isinstance(self.nodes[-1], TextNode):
        self.nodes[-1].text += text
        return
      if node is None:
        node = TextNode(text)

    self.nodes.append(node)

  def eval(self, context, args):
    return ''.join(n.eval(context, args) for n in self.nodes)


class VarNode(ExpressionNode):
  """
  This expression node implements a variable expansion or function call.
  """

  def __init__(self, ident, subident, args):
    super().__init__()
    self.ident = ident
    self.subident = subident
    self.args = args

  def eval(self, context, args):
    # Evaluate the arguments to the function.
    sub_args = [TextNode(n.eval(context, args)) for n in self.args]

    # Does the identifier access an argument?
    arg_index = None
    if self.subident is None:
      try:
        arg_index = int(self.ident)
      except ValueError:
        pass
    if arg_index is not None and arg_index >= 0 and arg_index < len(args):
      return args[arg_index].eval(context, sub_args)

    # Are we accessing a namespace? Use that context instead.
    if self.subident is not None:
      context = context.get_namespace(self.ident)
      varname = self.subident
    else:
      varname = self.ident

    # Try to get the macro and evaluate it.
    try:
      return context.get_macro(varname).eval(context, sub_args)
    except KeyError:
      return ''


class Macro(ExpressionNode):
  """
  Container for a macro expression tree bound to a :class:`ContextProvider`.

  Attributes:
    node (ExpressionNode): The root node of the evaluation hierarchy.
    context (ContextProvider): The context that the macro is bound to.
  """

  def __init__(self, node, context):
    super().__init__()
    self.node = node
    self.context = context

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

  def eval(self, context, args):
    return self.node.eval(self.context, args)


class Function(ExpressionNode):
  """
  This class can be used to wrap a Python function to make it a
  function that can be called from a macro. The wrapped function
  must accept the same arguments as :meth:`eval`.
  """

  def __init__(self, func):
    super(Function, self).__init__()
    self.func = func

  @property
  def name(self):
    return self.func.__name__

  def eval(self, context, args):
    return self.func(context, args)


class Parser(object):
  """
  This class implements the process of parsing a string into an
  expression node hierarchy.
  """

  CHARS_WHITESPACE = string.whitespace
  CHARS_IDENTIFIER = string.ascii_letters + string.digits + '-_.#<@'
  CHAR_POPEN = '('
  CHAR_PCLOSE = ')'
  CHAR_NAMESPACEACCESS = ':'
  CHAR_ARGSEP = ','

  def parse(self, text):
    """
    Args:
      text (str): The text to parse into an expression tree.
    Returns:
      ConcatNode: The root node of the hierarchy.
    """

    scanner = nr.strex.Scanner(text.strip())
    return self._parse_arg(scanner, closing_at='')

  def _parse_arg(self, scanner, closing_at):
    root = ConcatNode()
    char = scanner.char
    while scanner and char not in closing_at:
      if char == '$':
        char = scanner.next()
        node = None
        if char != '$':
          node = self._parse_macro(scanner)
        if node:
          root.append(node)
          char = scanner.char
        else:
          root.append('$')
          char = scanner.next()
      elif char == '\\':
        char = scanner.next()
        if char:
          root.append(char)
          char = scanner.next()
        else:
          root.append('\\')
      else:
        root.append(char)
        char = scanner.next()

    return root

  def _parse_macro(self, scanner):
    cursor = scanner.state()

    # This is a function call if we have an opening parentheses.
    is_call = False
    if scanner.char == self.CHAR_POPEN:
      scanner.next()
      is_call = True

    # Read the identifier that is to be accessed.
    ident = scanner.consume_set(self.CHARS_IDENTIFIER)
    if not ident:
      return None

    # Check if a namespace is accessed, read the sub identifier.
    subident = None
    if scanner.char == self.CHAR_NAMESPACEACCESS:
      scanner.next()
      subident = scanner.consume_set(self.CHARS_IDENTIFIER)

    # If its a function call, consume beginning whitespace.
    args = []
    if is_call:
      scanner.consume_set(self.CHARS_WHITESPACE)
      closing_at = self.CHAR_PCLOSE + self.CHAR_ARGSEP
      while scanner.char:
        node = self._parse_arg(scanner, closing_at)
        args.append(node)
        if scanner.char == self.CHAR_ARGSEP:
          scanner.next()
        elif scanner.char == self.CHAR_PCLOSE:
          break
      if scanner.char == self.CHAR_PCLOSE:
        scanner.next()
      else:
        # No closing parenthesis? Bad call.
        scanner.restore(cursor)
        return None

    return VarNode(ident, subident, args)


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


parser = Parser()
parse = parser.parse


class Globals:

  @Function
  def addprefix(context, args):
    if len(args) != 2:
      message = 'addprefix requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    prefix = args[0].eval(context, [])
    items = creator.utils.split(args[1].eval(context, []))
    items = [prefix + x for x in items]
    return creator.utils.join(items)

  @Function
  def addsuffix(context, args):
    if len(args) != 2:
      message = 'addsuffix requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    suffix = args[1].eval(context, [])
    items = creator.utils.split(args[0].eval(context, []))
    items = [x + suffix for x in items]
    return creator.utils.join(items)

  @Function
  def quote(context, args):
    items = [n.eval(context, []) for n in args]
    items = [shell.quote(x) for x in items]
    return ' '.join(items)

  @Function
  def quotelist(context, args):
    items = ';'.join(n.eval(context, []) for n in args)
    items = creator.utils.split(items)
    items = [shell.quote(x) for x in items]
    return ' '.join(items)

  @Function
  def subst(context, args):
    if len(args) != 3:
      message = 'subst requires 3 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    subject, replacement, items = [n.eval(context, []) for n in args]
    items = creator.utils.split(items)
    items = [x.replace(subject, replacement) for x in items]
    return creator.utils.join(items)

  @Function
  def split(context, args):
    if len(args) != 2:
      message = 'split requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    items, sep = [n.eval(context, []) for n in args]
    items = items.split(sep)
    return creator.utils.join(items)

  @Function
  def wildcard(context, args):
    dirname = context.get_macro('ProjectPath').eval(context, [])
    patterns = [n.eval(context, []) for n in args]
    items = []
    for pattern in patterns:
      items.extend(glob.iglob(os.path.join(dirname, pattern)))
    return creator.utils.join(items)

  @Function
  def suffix(context, args):
    if len(args) != 2:
      message = 'suffix requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    items, suffix = [n.eval(context, []) for n in args]
    items = creator.utils.split(items)
    itmes = [creator.utils.set_suffix(x, suffix) for x in items]
    return creator.utils.join(items)
