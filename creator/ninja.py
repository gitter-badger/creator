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

import creator.utils
import re

from creator.vendor.ninja_syntax import Writer


def export(fp, workspace, unit, default_targets=()):
  """
  Exports the build definitions for all units in the :class:`Workspace`
  to the file-like object *fp*.

  Args:
    fp (file-like): The file-like object to write to.
    workspace (Workspace): The workspace to export.
    unit (Unit): The main unit which should be used to resolve relative
      identifiers.
    default_targets (list of str): A list of target names, or None to
      let ninja build everything on default invokation.

  Raises:
    ValueError: If any of the targets do not exist.
  """

  writer = Writer(fp, width=1024)

  for unit in sorted(workspace.units.values(), key=lambda x: x.identifier):
    if not unit.targets:
      continue
    writer.comment('Unit: {0}'.format(unit.identifier))
    writer.newline()
    for target in sorted(unit.targets.values(), key=lambda x: x.name):
      target.export(writer)

  if default_targets:
    defaults = set()
    for target in default_targets:
      namespace, varname = creator.utils.parse_var(target)
      if namespace is None:
        targets = unit.targets
      else:
        targets = workspace.get_unit(namespace).targets
      if varname not in targets:
        raise ValueError('no such target', target)

      # Append all output files of the target to the defaults.
      for entry in targets[varname].command_data:
        defaults |= set(entry['outputs'])

    # Write the defaults.
    writer.default(list(defaults))


def ident(s):
  """
  Converts the string *s* into an identifier that is acceptible by
  ninja by replacing all invalid characters with an underscore.
  """

  return re.sub('[^A-Za-z0-9_]+', '_', s)
