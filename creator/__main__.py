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

import creator.unit
import creator.utils
import creator.ninja

import argparse
import os
import glob
import subprocess
import sys
import traceback


parser = argparse.ArgumentParser(
  description='Creator - software build automation tool')
parser.add_argument(
  '-D', '--define', help='Define a global variable that is accessible '
  'to all unit scripts. If no value is specified, it will be set to '
  'an empty string.', default=[], action='append')
parser.add_argument(
  '-M', '--macro', help='The same as -D, --define but evaluates like '
  'a macro. Remember that backslashes must be escaped, etc.', default=[],
  action='append')
parser.add_argument(
  '-P', '--unitpath', help='Add an additional path to search for unit '
  'scripts to the workspace.', default=[], action='append')
parser.add_argument(
  '-I', '--identifier', help='The identifier of the unit script to run. '
  'If it is not specified, the only file with suffix `.crunit` in the current '
  'working directory is used.')
subparser = parser.add_subparsers(dest='command')


build_parser = subparser.add_parser('build')
build_parser.add_argument(
  'targets', help='One or more names of targets that are to be '
  'built by this invocation. If a name contains no namespace access '
  'character `:` it will be assumed relative to the main unit.', nargs='*',
  default=[])
build_parser.add_argument(
  '-S', '--no-summary', help='Do not display a summary after the build '
  'process is complete or failed.', action='store_true')
ninja_parser.add_argument('-D', '--define', action='append')
ninja_parser.add_argument('-M', '--macro', action='append')


ninja_parser = subparser.add_parser('ninja')
ninja_parser.add_argument('-N', '--no-build', action='store_true',
  help="Don't run ninja after exporting the `ninja.build` file.")
ninja_parser.add_argument('args', nargs='*', default=[],
  help="Additional arguments for the ninja invocation.")
ninja_parser.add_argument('-D', '--define', action='append')
ninja_parser.add_argument('-M', '--macro', action='append')


def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  args = parser.parse_args(argv)
  workspace = creator.unit.Workspace()
  workspace.path.extend(args.unitpath)

  # Evaluate the Defines and Macros passed via the command line.
  for define in args.define:
    key, _, value = define.partition('=')
    if key:
      workspace.context[key] = creator.macro.TextNode(value)
  for macro in args.macro:
    key, _, value = macro.partition('=')
    if key:
      workspace.context[key] = value

  # If not Unit Identifier was specified on the command-line,
  # look at the current directory and use the only .crunit that
  # is in there.
  if not args.identifier:
    files = glob.glob('*.crunit')
    if not files:
      parser.error('no *.crunit file in the current directory')
    elif len(files) > 1:
      parser.error('multiple *.crunit files in the current directory')
    args.identifier = creator.utils.set_suffix(os.path.basename(files[0]), '')

  # Load the unit script.
  unit = workspace.load_unit(args.identifier)

  # Set up all unit targets.
  for a_unit in workspace.units.values():
    for target in a_unit.targets.values():
      target.setup_target()

  if args.command is None:
    return 0
  elif args.command == 'build':
    return cmd_build(args, workspace, unit)
  elif args.command == 'ninja':
    return cmd_ninja(args, workspace, unit)
  else:
    raise RuntimeError('unexpected command', args.command)


def cmd_build(args, workspace, unit):
  # Collect a list of all targets, we need to check if any failed.
  all_targets = []
  for unit in workspace.units.values():
    all_targets.extend(unit.targets.values())

  # Collect the targets to be run and run them.
  if not args.targets:
    targets = all_targets
  else:
    targets = []
    for name in args.targets:
      curr_unit = unit
      if ':' in name:
        unit_name, name = creator.utils.parse_var(name)
        if unit_name not in workspace.units:
          parser.error('no unit called "{0}"'.format(unit_name))
        curr_unit = workspace.units[unit_name]

      if name not in curr_unit.targets:
        parser.error('no target called "{0}" in unit "{1}"'.format(
          name, curr_unit.identifier))
      targets.append(curr_unit.targets[name])

  try:
    for target in targets:
      recursively_run_target(target)
  except Exception as exc:
    traceback.print_exc()

  # Print a summary?
  if not args.no_summary:
    print()
    print("Summary:")
    print("==================================================================")
    for target in sorted(all_targets, key=lambda x: x.identifier):
      print("* {0:20s} : {1}".format(target.identifier, target.status), end='')
      if target.message:
        print(" ({0})".format(target.message))
      else:
        print()

  # Check if a target failed.
  for target in all_targets:
    with target.condition:
      if target.status == 'failed':
        return 1

  return 0


def cmd_ninja(args, workspace, unit):
  with open('ninja.build', 'w') as fp:
    creator.ninja.export(workspace, fp)
  print("creator: exported to build.ninja")
  if not args.no_build:
    return subprocess.call(['ninja'] + args.args, shell=True)


def recursively_run_target(target):
  """
  Recursively runs the dependencies of *target* and then the target itself.
  """

  for dep in target.dependencies:
    with dep.condition:
      if dep.status != 'setup':
        continue
    recursively_run_target(dep)

  with target.condition:
    if target.status != 'setup':
      return
  target.run_target()


if __name__ == "__main__":
  sys.exit(main())
