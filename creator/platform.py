# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

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
  platform_name = 'Windows'
elif sys.platform.startswith('darwin'):
  platform_standard = 'Posix'
  platform_name = 'Darwin'
else:
  raise EnvironmentError('unsupported Platform "{0}"'.format(sys.platform))

if (sys.maxsize >> 31) > 0:
    architecture = 'x64'
else:
    architecture = 'x86'
