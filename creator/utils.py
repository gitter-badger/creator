# Copyright (C) 2015 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import collections
import io
import os
import re
import shlex
import subprocess

try:
  import colorama
except ImportError:
  colorama = None
else:
  colorama.init()


def term_stylize(fg=None, bg=None, attr=(), reset=False):
  """
  Generates ANSI escape sequences for the specified settings.

  Args:
    fg (str): The name of the foreground color to apply or None.
    bg (str): The name of the background color to apply or None.
    attr (str or list of str): The attribute name or a list of
      attribute names to apply.
    reset (bool): True to reset to default. Every other argument
      will be ignored.
  Returns:
    str
  """

  if not colorama:
    return ''
  if reset:
    return colorama.Style.RESET_ALL
  s = ''
  if fg is not None:
    s += getattr(colorama.Fore, fg.upper())
  if bg is not None:
    s += getattr(colorama.Back, bg.upper())
  if isinstance(attr, str):
    attr = []
  for name in attr:
    s += getattr(colorama.Style, name.upper())
  return s


def term_format(text, *args, **kwargs):
  """
  The same as :meth:`ttyv` but takes *text* and wraps it in the
  specified tty visual settings and appends a reset command.
  """

  if not colorama:
    return text
  return ttyv(*args, **kwargs) + text + colorama.Style.RESET_ALL


def term_print(*args, **kwargs):
  """
  Like :func:`print`, but colors the output based on the specified
  *fg*, *bg* and *attr* keyword arguments.
  """

  fg = kwargs.pop('fg', None)
  bg = kwargs.pop('bg', None)
  attr = kwargs.pop('attr', ())
  if not colorama:
    print(*args, **kwargs)
  else:
    end = kwargs.pop('end', '\n')
    kwargs['end'] = ''
    print(term_stylize(fg, bg, attr), end='')
    print(*args, **kwargs)
    print(colorama.Style.RESET_ALL, end=end)


def normpath(x):
  return os.path.normpath(os.path.abspath(os.path.expanduser(x)))


def quote(s):
  """
  Better implementation of :func:`shlex.quote` which uses single-quotes
  on Windows, which are not supported however.
  """

  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s):
      s = '"' + s + '"'
    return s
  else:
    return shlex.quote(s)


def set_suffix(filename, suffix):
  """
  Changes the suffix of the specified *filename* to *suffix*. If the
  suffix is empty, the suffix will only be removed from the filename.
  The dot must not be contained in the suffix.

  Args:
    filename (str): The filename to change.
    suffix (str): The suffix to set.
  Returns:
    str: The filename with the changed suffix.
  """

  index = filename.rfind('.')
  if index > filename.replace('\\', '/').rfind('/'):
    filename = filename[:index]
  if suffix:
    if not suffix.startswith('.'):
      suffix = '.' + suffix
    filename += suffix
  return filename


def validate_identifier(identifier):
  """
  Args:
    identifier (str): The identifier to test.
  Returns:
    bool: True if the *identifier* is a valid identifier for a unit,
      False if it is not.
  """

  return bool(re.match('^[A-Za-z0-9\-\._]+$', identifier))


def parse_var(var):
  """
  Parses a variable name with an optional namespace access and
  returns a tuple of ``(namespace, varname)``. If a namespace
  separator is specified, the returned namespace will be an
  empty string (as there should be a namespace but there were
  no characters for it).
  """

  namespace, sep, varname = var.partition(':')
  if not varname:
    namespace, varname = varname, namespace
  if not sep:
    namespace = None
  return (namespace, varname)


def create_var(namespace, varname):
  """
  Returns the full identifer to access the variable *varname* in
  *namespace*.
  """

  if namespace is not None:
    return namespace + ':' + varname
  return varname


def split(text):
  """
  Splits text by semicolon and returns a list of the result. The semicolon
  separated format is used in *Creator* to implement lists. Backslashes may
  be used to escape semicolons.

  Args:
    text (str): The text to split into a list.
  Returns:
    list of str: The resulting list.
  """

  items = []
  while text:
    index = text.find(';')
    while index > 0 and (index - 1) == text.find('\\;', index - 1):
      index = text.find(';', index + 1)

    if index < 0:
      item = text
      text = None
    else:
      item = text[:index]
      text = text[index + 1:]

    if item:
      items.append(item.replace('\\;', ';'))
  return items


def join(items):
  """
  Joins a list of strings into a single string by putting semicolons
  between the items. This string can later be split with the :func:`split`
  function. Semicolons are escaped using backslashes.

  Args:
    items (list of str): The items to join into a single string.
  Returns:
    str: The semicolon separated list of the specified *items*.
  """

  return ';'.join(item.replace(';', '\\;') for item in items if item)


class Response(object):
  """
  This class represents a subprocess execution and provides some
  function to process the result or even get the complete output.

  Args:
    command (list of str): The command to execute.
  Raises:
    OSError: If an error occured executing the command, usually if
      the program could not be found.
    ValueError: If *command* is an empty list.
    Response.ExitCodeError: If the program exited with a non-zero exit-code.
  """

  class ExitCodeError(Exception):
    pass

  def __init__(self, command, shell=False):
    if not command:
      raise ValueError('empty command sequence')
    super().__init__()
    self.command = command
    self.process = subprocess.Popen(command, stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, shell=shell)
    self.content = self.process.communicate()[0].decode()
    self.buffer = io.StringIO(self.content)
    self.returncode = self.process.returncode
    if self.returncode != 0:
      raise self.ExitCodeError(command[0], self.returncode)

  def __str__(self):
    return self.content

  def read(self, n=None):
    return self.buffer.read(n)

  def readline(self):
    return self.buffer.readline()


Cursor = collections.namedtuple('Cursor', 'position lineno colno')


class Scanner(object):

  def __init__(self, content):
    self._content = content
    self.position = 0
    self.lineno = 1
    self.colno = 0

  def __repr__(self):
    return '<Scanner at {} line:{} col:{}>'.format(*self.state())

  def __bool__(self):
    return self.position < len(self._content)

  __nonzero__ = __bool__

  def state(self):
    return Cursor(self.position, self.lineno, self.colno)

  def restore(self, state):
    self.position, self.lineno, self.colno = state

  @property
  def char(self):
    if self.position < len(self._content):
      return self._content[self.position]
    else:
      return type(self._content)()

  def next(self):
    char = self.char
    if not char:
      return char
    if char == '\n':
      self.lineno += 1
      self.colno = 0
    else:
      self.colno += 1
    self.position += 1
    return self.char

  def match(self, regex):
    match = regex.match(self._content, self.position)
    if not match:
      return None

    text = match.group()
    lines = text.count('\n')

    self.position = match.end()
    self.lineno += lines
    if lines:
      self.colno = 0
      self.colno = len(text) - text.rfind('\n') - 1
    else:
      self.colno += len(text)

    return match

  def consume_set(self, charset, invert=False, maxc=-1):
    """
    Consumes all characters that occur in the *charset* up to a
    total number of *maxc* characters.
    """

    result = type(self._content)()
    char = self.char
    while char:
      if maxc >= 0 and len(result) >= maxc:
        break
      if not invert and char in charset:
        result += char
      elif invert and char not in charset:
        result += char
      else:
        break
      char = self.next()
    return result
