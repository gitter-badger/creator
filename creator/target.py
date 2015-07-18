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
"""
This module provides the :class:`Target` class which contains all the
information necessary to generate build commands and export them to a
ninja build definitions file.
"""

import creator.macro
import creator.unit
import creator.utils
import creator.ninja
import weakref


class Target(object):
  """
  This class represents one or multiple build targets under one common
  identifier. It contains all the information necessary to generate the
  required build commands.

  A target has a set-up phase which is invoked after all units were
  loaded and evaluated. After this phase is complete, the target should
  be completely filled with all data.

  Args:
    unit (creator.unit.Unit): The unit this target belongs to.
    name (str): The name of the target.
    on_setup (callable): A Python function that is called on set-up.
    pass_self (bool): True if the target should be passed as the first
      argument to *on_setup*, False if not.
    args (any): List of arguments passed to *on_setup*.
    kwargs (any): List of keyword arguments passed to *on_setup*.

  Attributes:
    unit (creator.unit.Unit): The unit this target belongs to.
    name (str): The name of the target.
    identifier (str): The identifier of the target, which is the
      units identifier and the targets name concatenated.
    is_setup (bool): True if the target is set-up, False if not.
    on_setup (callable)
    pass_self (bool)
    args (any)
    kwargs (any)
    listeners (list of callable): A list of functions listening to
      certain events of the target. The functions are invoked with
      the three arguments ``(target, event, data)``.
  """

  def __init__(
      self, unit, name, on_setup=None, pass_self=True,
      args=(), kwargs=None):
    if not isinstance(unit, creator.unit.Unit):
      raise TypeError('unit must be creator.unit.Unit', type(unit))
    if not isinstance(name, str):
      raise TypeError('name must be str', type(name))
    if not creator.utils.validate_identifier(name):
      raise ValueError('name is not a valid identifier', name)
    if on_setup is not None and not callable(on_setup):
      raise TypeError('on_setup must be None or callable')
    super().__init__()
    self._unit = weakref.ref(unit)
    self._name = name
    self.is_setup = False
    self.dependencies = []
    self.on_setup = on_setup
    self.pass_self = pass_self
    self.args = args
    self.kwargs = kwargs or {}
    self.command_data = []
    self.listeners = []

  @property
  def unit(self):
    return self._unit()

  @property
  def name(self):
    return self._name

  @property
  def identifier(self):
    return self._unit().identifier + ':' + self._name

  def do_setup(self):
    """
    Set up the targets internal data or dependencies. Call the parent
    method after successful exit to set :attr:`is_setup` to True. Raise
    an exception if something fails.

    Raises:
      RuntimeError: If the target is already set-up.
    """

    if self.is_setup:
      raise RuntimeError('target "{0}" is already set-up'.format(self.identifier))

    for listener in self.listeners:
      listener(self, 'do_setup', None)

    if self.on_setup is not None:
      if self.pass_self:
        self.on_setup(self, *self.args, **self.kwargs)
      else:
        self.on_setup(*self.args, **self.kwargs)

    self.is_setup = True
    return True

  def requires(self, target):
    """
    Adds *target* as a dependency for this target. If the *target* is
    not already set-up, it will be by this function.

    Args:
      target (str or Target): The target to build before the other.
        If a string is passed, the target name is resolved in the
        workspace.
    """

    if isinstance(target, str):
      namespace, target = creator.utils.parse_var(target)
      if not namespace:
        namespace = self.unit.identifier
      identifier = creator.utils.create_var(namespace, target)
      target = self.unit.workspace.find_target(identifier)
    elif not isinstance(target, Target):
      raise TypeError('target must be Target object', type(target))
    if not target.is_setup:
      target.do_setup()
    self.dependencies.append(target)

  def add(self, inputs, outputs, *commands):
    """
    Associated the *inputs* with the *outputs* being built by the
    specified *\*commands*. All parameters passed to this function must
    be strings that are automatically and instantly evaluated as macros.

    The data will be appended to :attr:`command_data` in the form of
    a dictionary with the following keys:

    - ``'inputs'``: A list of input files.
    - ``'outputs'``: A list of output files.
    - ``'commands'``: A list of the commands to produce the files.

    Args:
      inputs (str): A listing of the input files.
      outputs (str): A listing of the output files.
      *commands (tuple of str): One or more commands to build the
        outputs from the inputs The special variables ``$<`` and
        ``$@`` are available to the macros specified to this parameter.
        **Note**: Currently, Creator only supports one command per target.
    """

    if len(commands) != 1:
      raise RuntimeError('Creator currently only supports one command per target.')

    data = {'inputs': inputs, 'outputs': outputs, 'commands': commands}
    for listener in self.listeners:
      listener(self, 'add', data)
    inputs, outputs, commands = data['inputs'], data['outputs'], data['commands']

    input_files = creator.utils.split(self.unit.eval(inputs, stack_depth=1))
    input_files = [creator.utils.normpath(f) for f in input_files]
    output_files = creator.utils.split(self.unit.eval(outputs, stack_depth=1))
    output_files = [creator.utils.normpath(f) for f in output_files]

    supp_context = creator.macro.MutableContext()
    supp_context['<'] = creator.macro.TextNode(creator.utils.join(input_files))
    supp_context['@'] = creator.macro.TextNode(creator.utils.join(output_files))
    eval_commands = []
    for command in commands:
      command = self.unit.eval(command, supp_context, stack_depth=1)
      eval_commands.append(command)
    self.command_data.append({
      'inputs': input_files,
      'outputs': output_files,
      'commands': eval_commands
    })

  def export(self, writer):
    """
    Export the target to the ninja file using the *writer*. The target
    and all its dependencies must be set-up.

    Raises:
      RuntimeError: If the target or one of its dependencies is not set-up.
    """

    if not self.is_setup:
      raise RuntimeError('target "{0}" not set-up'.format(self.identifier))

    writer.comment('Target: {0}'.format(self.identifier))

    # The outputs of depending targets must be listed additionally
    # to the actual input files of this target, otherwise ninja can
    # not know the targets depend on each other.
    infiles = set()

    for dep in self.dependencies:
      if not dep.is_setup:
        raise RuntimeError('target "{0}" not set-up'.format(dep.identifier))
      for entry in dep.command_data:
        infiles |= set(map(creator.utils.normpath, entry['outputs']))

    infiles = list(infiles)
    phonies = []

    for index, entry in enumerate(self.command_data):
      if len(entry['commands']) != 1:
        raise RuntimeError('Creator currently only supports one command per target.')

      rule_name = self.identifier + '_{0:04d}'.format(index)
      rule_name = creator.ninja.ident(rule_name)
      writer.rule(rule_name, entry['commands'])

      writer.build(entry['outputs'], rule_name, list(entry['inputs']) + infiles)
      writer.newline()

      phonies.extend(entry['outputs'])

    writer.build(creator.ninja.ident(self.identifier), 'phony', phonies)
