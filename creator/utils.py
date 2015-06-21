# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import os
import re
import shlex


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
