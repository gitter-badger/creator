# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.
"""
Creator - software build automation tool
========================================

Visit https://github.com/NiklasRosenstein/py-creator/wiki.
"""

__author__ = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'
__version__ = '0.0.1'
__url__ = 'https://github.com/NiklasRosenstein/py-creator/wiki'

import sys
if sys.version_info[0] != 3:
  raise EnvironmentError('Creator {0} requires Python 3'.format(__version__))

from creator import macro
from creator import platform
from creator import unit
from creator import utils
