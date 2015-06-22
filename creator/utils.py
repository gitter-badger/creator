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

import io
import os
import re
import shlex
import subprocess


def quote(s):
  """
  Better implementation of :func:`shlex.quote` which uses single-quotes
  on Windows, which are not supported however.
  """

  if os.name == 'nt' and os.sep == '\\':
    return '"' + s.replace('"', '\\"') + '"'
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
  returns a tuple of ``(namespace, varname)``.
  """

  namespace, _, varname = var.partition(':')
  if not varname:
    namespace, varname = varname, namespace
  return (namespace, varname)


def create_var(namespace, varname):
  """
  Returns the full identifer to access the variable *varname* in
  *namespace*.
  """

  if namespace:
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
    while index >= 0 and (index - 1) == text.find('\\;', index - 1):
      index = text.find(';', index + 1)

    if index < 0:
      item = text
      text = None
    else:
      item = text[:index]
      text = text[index + 1:]

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

  return ';'.join(item.replace(';', '\\;') for item in items)



class Shell(object):
  """
  This class represents a subprocess execution and provides some
  function to process the result or even get the complete output.

  Args:
    command (list of str): The command to execute.
  Raises:
    OSError: If an error occured executing the command, usually if
      the program could not be found.
    ValueError: If *command* is an empty list.
    Shell.ExitCodeError: If the program exited with a non-zero exit-code.
  """

  class ExitCodeError(Exception):
    pass

  def __init__(self, command):
    if not command:
      raise ValueError('empty command sequence')
    super(Shell, self).__init__()
    self.command = command
    self.process = subprocess.Popen(command, stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, shell=False)
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
