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
  prog='creator', description='Creator - software build automation tool')
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


ninja_parser = subparser.add_parser('ninja')
ninja_parser.add_argument('-t', '--target', default=[], action='append',
  help="Specify one or more default targets to build when ninja is "
  "invoked without a specific target. If omitted, ninja will build "
  "everything.")
ninja_parser.add_argument('-N', '--no-build', action='store_true',
  help="Don't run ninja after exporting the `ninja.build` file.")
ninja_parser.add_argument('-D', '--define', default=[], action='append')
ninja_parser.add_argument('-M', '--macro', default=[], action='append')
ninja_parser.add_argument('args', nargs='*', default=[],
  help="Additional arguments for the ninja invocation.")


run_parser = subparser.add_parser('run')
run_parser.add_argument('tasks', nargs='+', help='One or more tasks to run.')
run_parser.add_argument('-D', '--define', default=[], action='append')
run_parser.add_argument('-M', '--macro', default=[], action='append')


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
      parser.error('multiple *.crunit files in the current '
        'directory, use -I/--identifier to specify which.')
    args.identifier = creator.utils.set_suffix(os.path.basename(files[0]), '')

  # Load the unit script.
  unit = workspace.load_unit(args.identifier)

  # Set up all unit targets.
  workspace.setup_targets()

  if args.command is None:
    return 0
  elif args.command == 'ninja':
    return cmd_ninja(args, workspace, unit)
  elif args.command == 'run':
    for task in args.task:
      unit.run_task(task)
  else:
    raise RuntimeError('unexpected command', args.command)


def cmd_ninja(args, workspace, unit):
  with open('build.ninja', 'w') as fp:
    creator.ninja.export(fp, workspace, unit, args.target)
  print("creator: exported to build.ninja")
  if not args.no_build:
    return subprocess.call(['ninja'] + args.args)


if __name__ == "__main__":
  sys.exit(main())
