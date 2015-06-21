# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.unit
import creator.utils
import creator.target
import creator.vendor.ninja_syntax as ninja
import argparse
import os
import glob
import re
import sys
import traceback


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


ninja_parser = subparser.add_parser('ninja')
ninja_parser.add_argument(
  '--stdout', help='Outputs to stdout instead of to build.ninja',
  action='store_true')
ninja_parser.add_argument(
  '-o', '--output', help='Target output file. Will be ignored if '
  '--stdout is passed.', default='build.ninja')
ninja_parser.add_argument(
  '-f', '--force', help='Force overwrite the output file.',
  action='store_true')


def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  args = parser.parse_args(argv)
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
  if args.stdout:
    writer = ninja.Writer(sys.stdout)
  elif os.path.isfile(args.output) and not args.force:
    ninja_parser.error('file "{0}" already exists.'.format(args.output))
  else:
    writer = ninja.Writer(open(args.output, 'w'))

  # Export the ShellTarget's in all units to the Ninja file.
  for unit in sorted(workspace.units.values(), key=lambda x: x.identifier):
    if not unit.targets:
      continue
    writer.comment('Unit: {0}'.format(unit.identifier))
    writer.newline()
    for target in sorted(unit.targets.values(), key=lambda x: x.name):
      writer.comment('Target: {0}'.format(target.identifier))
      if not isinstance(target, creator.target.ShellTarget):
        print('# Warning: Can not translate {0} "{1}" to ninja'.format(
          type(target).__name__, target.identifier), file=sys.stderr)
        continue
      phonies = []
      for index, entry in enumerate(target.data):
        if len(entry['commands']) != 1:
          print("# Warning: Target {0} lists multiple commands which is"
            "not supported by ninja".format(target.identifier), file=sys.stderr)
          continue
        phonies.extend(entry['outputs'])
        rule_name = ninja_ident(target.identifier + '_{0:04d}'.format(index))
        writer.rule(rule_name, entry['commands'])
        writer.build(entry['outputs'], rule_name, entry['inputs'])
        writer.newline()
      writer.build(ninja_ident(target.identifier), 'phony', phonies)

  if not args.stdout:
    print("creator: Exported to", args.output)


def ninja_ident(s):
  """
  Converts the string *s* into an identifier that is acceptible by
  ninja by replacing all invalid characters with an underscore.
  """

  return re.sub('[^A-Za-z0-9_]+', '_', s)


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
