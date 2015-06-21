#!/usr/bin/env python3
# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import setuptools

long_description = ''
setuptools.setup(
  name='creator',
  version='0.0.1',
  description='software build automation tool',
  long_description=long_description,
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  url='https://github.com/NiklasRosenstein/py-creator',
  install_requires=['nr.strex>=1.3'],
  py_modules=['creator'],
  packages=setuptools.find_packages('.'),
  package_dir={'': '.'},
  scripts=['scripts/creator'],
  classifiers=[
    "Development Status :: 5 - Production/Stable",
    "Programming Language :: Python",
    "Intended Audience :: Developers",
    "Topic :: Utilities",
    "Topic :: Software Development :: Libraries",
    "Topic :: Software Development :: Libraries :: Python Modules",
    ],
  license="none",
)
