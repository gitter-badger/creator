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

import os
import sys

if sys.platform.startswith('freebsd'):
  platform_standard = 'BSD'
  platform_name = 'FreeBSD'
elif sys.platform.startswith('bsd'):
  platform_standard = 'BSD'
  platform_name = 'BSD'
elif sys.platform.startswith('linux'):
  platform_standard = 'Posix'
  platform_name = 'Linux'
elif sys.platform.startswith('win32'):
  platform_standard = 'NT'
  platform_name = 'Windows'
elif sys.platform.startswith('cygwin'):
  platform_standard = 'Posix'
  platform_name = 'Cygwin'
elif sys.platform.startswith('darwin'):
  platform_standard = 'Posix'
  platform_name = 'Darwin'
else:
  raise EnvironmentError('unsupported Platform "{0}"'.format(sys.platform))

if (sys.maxsize >> 31) > 0:
    architecture = 'x64'
else:
    architecture = 'x86'
