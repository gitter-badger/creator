# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.unit
import creator.utils
import argparse
import os
import glob


parser = argparse.ArgumentParser(
  description='Creator - software build automation tool')
parser.add_argument(
  '-D', '--define', help='Define a global variable that is accessible '
  'to all unit scripts. If no value is specified, it will be set to '
  'an empty string.', default=[], action='append')
parser.add_argument(
  '-P', '--unitpath', help='Add an additional path to search for unit '
  'scripts to the workspace.', default=[], action='append')
parser.add_argument(
  'identifier', help='The identifier of the unit script to run. If it '
  'is not specified, the only file with suffix `.crunit` in the current '
  'working directory is used.', default=None, nargs='?')
parser.add_argument(
  '-T', '--targets', help='One or more names of targets that are to be '
  'built by this invocation. If a name contains no namespace access '
  'character `:` it will be assumed relative to the main unit.', nargs='+',
  default=[])


def main():
  args = parser.parse_args()
  workspace = creator.unit.Workspace()
  workspace.path.extend(args.unitpath)
  for define in args.define:
    key, _, value = define.partition('=')
    if key:
      workspace.context[key] = value

  if not args.identifier:
    files = glob.glob('*.crunit')
    if not files:
      parser.error('no *.crunit file in the current directory')
    elif len(files) > 1:
      parser.error('multiple *.crunit files in the current directory')
    args.identifier = creator.utils.set_suffix(os.path.basename(files[0]), '')

  unit = workspace.load_unit(args.identifier)

  # Set up all unit targets.
  for unit in workspace.units.values():
    for target in unit.targets.values():
      target.setup_target()

  # Collect the targets to be run and run them.
  targets = []
  for name in args.targets:
    curr_unit = unit
    if ':' in name:
      unit_name, _, name = name.partition(':')
      if unit_name not in workspace.units:
        parser.error('no unit called "{0}"'.format(unit_name))
      curr_unit = workspace.units[unit_name]

    if name not in curr_unit.targets:
      parser.error('no target called "{0}" in unit "{1}"'.format(
        name, curr_unit.identifier))
    targets.append(curr_unit.targets[name])

  for target in targets:
    if target.status == 'setup':
      target.run_target()


if __name__ == "__main__":
  main()
