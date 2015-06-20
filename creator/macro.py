# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.utils
import abc
import glob
import nr.strex
import os
import string
import sys
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
      ExpressionNode: The macro associated with the specified *name*.
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


class MutableContext(ContextProvider):
  """
  This implementation of the :class:`ContextProvider` interface
  enables reading and writing macros via the Python ``__getitem__()``
  and ``__setitem__()`` interface and stores these internally. If a
  string is set with ``__setitem__()``, it will automatically be parsed
  into an expression tree.

  Attributes:
    macros (dict of str -> ExpressionNode): The internal dictionary
      mapping the macro names with the actual macro objects.
  """

  def __init__(self):
    super().__init__()
    self.macros = {}

  def __getitem__(self, name):
    return self.get_macro(name).eval(self, [])

  def __setitem__(self, name, value):
    if isinstance(value, str):
      value = parse(value)
    elif not isinstance(value, ExpressionNode):
      message = 'value must be str or ExpressionNode'
      raise TypeError(message, type(value))
    # Make sure the macro does not contain a reference to itself.
    # It will be resolved by expanding the original value immediately
    # in the expression hierarchy.
    old_value = self.macros.get(name)
    if old_value is not None:
      for ref_name in self.get_aliases(name):
        value = value.substitute(ref_name, old_value)
    self.macros[name] = value

  def __delitem__(self, name):
    try:
      del self.macros[name]
    except KeyError:
      pass

  def get_aliases(self, name):
    """
    This function can be implemented by subclasses to specify under
    what aliases the same macro can be found. The default implementation
    simply returns *name*.

    Args:
      name (str): The name that was passed to :meth:`__setitem__`.
    Returns:
      list of str: A list of aliases.
    """

    return [name]

  def function(self, func):
    """
    Decorator for a Python callable to be wrapped in a :class:`Function`
    expression node and assigned to the *MutableContext*.
    """

    self.macros[func.__name__] = Function(func)
    return self.macros[func.__name__]

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


class ChainContext(ContextProvider):
  """
  This context chains multiple :class:`ContextProvider`s.
  """

  def __init__(self, *contexts):
    super().__init__()
    self.contexts = []
    for context in contexts:
      if context is not None:
        if not isinstance(context, ContextProvider):
          raise TypeError('expected ContextProvider', type(context))
        self.contexts.append(context)

  def has_macro(self, name):
    for context in self.contexts:
      if contexts.has_macro(name):
        return True
    return False

  def get_macro(self, name, default=NotImplemented):
    for context in self.contexts:
      try:
        return context.get_macro(name)
      except KeyError:
        pass
    if default is NotImplemented:
      raise KeyError(name)
    return default

  def get_namespace(self, name):
    for context in self.contexts:
      try:
        return context.get_namespace(name)
      except KeyError:
        pass
    raise KeyError(name)


class StackFrameContext(ContextProvider):
  """
  This :class:`ContextProvider` implementation exposes the contents
  of a Python stack frame.

  Args:
    stack_depth (int): The number of stacks to go backwards from the
      calling stack frame to reach the frame that is supposed to be
      exposed by this context.
  """

  def __init__(self, stack_depth=0):
    super().__init__()
    frame = sys._getframe()
    for i in range(stack_depth + 1):
      frame = frame.f_back
    self.frame = frame

  def has_macro(self, name):
    frame = self.frame
    if name in frame.f_locals or name in frame.f_globals:
      return True
    return False

  def get_macro(self, name, default=NotImplemented):
    frame = self.frame
    if name in frame.f_locals:
      value = frame.f_locals[name]
    elif name in frame.f_globals:
      value = frame.f_globals[name]
    elif default is not NotImplemented:
      return default
    else:
      raise KeyError(name)

    if not isinstance(value, creator.macro.ExpressionNode):
      value = creator.macro.TextNode(str(value))
    return value

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

  @abc.abstractmethod
  def substitute(self, ref_name, node):
    """
    This function must be implemented by nodes that expand a variable
    name like the :meth:`VarNode` and must replace any occurence that
    expands the reference named by *ref_name* with *node*.

    Args:
      ref_name (str): The name of the variable. May contain a double
        colon ``:`` to separate namespace and variable name.
      node (ExpressionNode): The node to insert in place.
    Returns:
      ExpressionNode: *self* or *node*.
    """

    return self


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

  def substitute(self, ref_name, node):
    return self


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

  def substitute(self, ref_name, node):
    for i in range(len(self.nodes)):
      self.nodes[i] = self.nodes[i].substitute(ref_name, node)
    return self


class VarNode(ExpressionNode):
  """
  This expression node implements a variable expansion or function call.
  """

  def __init__(self, namespace, varname, args):
    super().__init__()
    print("VarNode(%r, %r, %r)" % (namespace, varname, args))
    self.namespace = namespace
    self.varname = varname
    self.args = args

  def eval(self, context, args):
    # Evaluate the arguments to the function.
    sub_args = [TextNode(n.eval(context, args)) for n in self.args]

    # Does the identifier access an argument?
    arg_index = None
    if not self.namespace:
      try:
        arg_index = int(self.varname)
      except ValueError:
        pass
    if arg_index is not None and arg_index >= 0 and arg_index < len(args):
      return args[arg_index].eval(context, sub_args)

    # Are we accessing a namespace? Use that context instead.
    if self.namespace:
      context = context.get_namespace(self.namespace)

    # Try to get the macro and evaluate it.
    try:
      return context.get_macro(self.varname).eval(context, sub_args)
    except KeyError:
      return ''

  def substitute(self, ref_name, node):
    namespace, _, varname = ref_name.partition(':')
    if not varname:
      varname, namespace = namespace, varname
    if self.namespace and self.namespace != namespace:
      return self
    elif not self.namespace and namespace:
      return self
    elif self.varname != varname:
      return self

    return node


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

  def substitute(self, ref_name, node):
    return self


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

    # Read the namespace or variable name identifier.
    varname = scanner.consume_set(self.CHARS_IDENTIFIER)
    if not varname:
      return None

    # Check if a namespace is accessed, read the sub identifier.
    namespace = None
    if scanner.char == self.CHAR_NAMESPACEACCESS:
      scanner.next()
      namespace = varname
      varname = scanner.consume_set(self.CHARS_IDENTIFIER)

    # If its a function call, consume beginning whitespace.
    args = []
    if is_call:
      scanner.consume_set(self.CHARS_WHITESPACE)
      closing_at = self.CHAR_PCLOSE + self.CHAR_ARGSEP
      while scanner.char and scanner.char != self.CHAR_PCLOSE:
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

    return VarNode(namespace, varname, args)


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
    items = [n.eval(context, []).strip() for n in args]
    items = [shell.quote(x) for x in items]
    return ' '.join(items)

  @Function
  def quotelist(context, args):
    items = ';'.join(n.eval(context, []).strip() for n in args)
    items = creator.utils.split(items)
    items = [shell.quote(x) for x in items]
    return ' '.join(items)

  @Function
  def subst(context, args):
    if len(args) != 3:
      message = 'subst requires 3 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    subject, replacement, items = [n.eval(context, []).strip() for n in args]
    items = creator.utils.split(items)
    items = [x.replace(subject, replacement) for x in items]
    return creator.utils.join(items)

  @Function
  def split(context, args):
    if len(args) != 2:
      message = 'split requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    items, sep = [n.eval(context, []).strip() for n in args]
    items = items.split(sep)
    return creator.utils.join(items)

  @Function
  def wildcard(context, args):
    dirname = context.get_macro('ProjectPath').eval(context, [])
    patterns = [n.eval(context, []).strip() for n in args]
    items = []
    for pattern in patterns:
      items.extend(glob.iglob(os.path.join(dirname, pattern)))
    return creator.utils.join(items)

  @Function
  def suffix(context, args):
    if len(args) != 2:
      message = 'suffix requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    items, suffix = [n.eval(context, []).strip() for n in args]
    items = creator.utils.split(items)
    items = [creator.utils.set_suffix(x, suffix) for x in items]
    return creator.utils.join(items)


  @Function
  def move(context, args):
    if len(args) != 2:
      message = 'move requires 2 arguments, got {0}'.format(len(args))
      raise TypeError(message)
    items, dirname = [n.eval(context, []).strip() for n in args]
    if not os.path.isabs(dirname):
      proj_path = context.get_macro('ProjectPath').eval(context, [])
      dirname = os.path.join(proj_path, dirname)
    result = []
    for item in creator.utils.split(items):
      relpath = os.path.relpath(item, proj_path)
      result.append(os.path.join(dirname, item))
    print(items)
    print(result)
    return creator.utils.join(result)
