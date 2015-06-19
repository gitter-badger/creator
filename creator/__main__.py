# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.unit
import argparse
import os


parser = argparse.ArgumentParser(
  description='Creator - software build automation tool')
parser.add_argument(
  '-D', '--define', help='Define a global variable that is accessible'
  'to all unit scripts. If no value is specified, it will be set to'
  'an empty string.', default=[], action='append')
parser.add_argument(
  '-P', '--unitpath', help='Add an additional path to search for unit'
  'scripts to the workspace.', default=[], action='append')


def main():
  args = parser.parse_args()
  workspace = creator.unit.Workspace()
  workspace.path.extend(args.unitpath)
  for define in args.define:
    key, _, value = define.partition('=')
    if key:
      workspace.context[key] = value

  # TODO
  pass


if __name__ == "__main__":
  main()
