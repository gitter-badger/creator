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

from creator.vendor.ninja_syntax import Writer
import creator.target
import creator.utils

import re


def export(workspace, fp):
  writer = Writer(fp)

  for unit in sorted(workspace.units.values(), key=lambda x: x.identifier):
    if not unit.targets:
      continue
    writer.comment('Unit: {0}'.format(unit.identifier))
    writer.newline()
    for target in sorted(unit.targets.values(), key=lambda x: x.name):
      target.export(writer)


def ident(s):
  """
  Converts the string *s* into an identifier that is acceptible by
  ninja by replacing all invalid characters with an underscore.
  """

  return re.sub('[^A-Za-z0-9_]+', '_', s)
