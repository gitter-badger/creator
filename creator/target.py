# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.macro
import creator.unit
import creator.utils
import abc
import os
import threading
import weakref


class Target(object, metaclass=abc.ABCMeta):
  """
  Interface for target declarations. A target is basically just a process
  that will be executed when its dependencies are met. Multiple targets can
  be run from multiple threads as long as their member access is synchronized
  with the :attr:`condition` variable.

  Attributes:
    unit (creator.unit.Unit): The unit that the target is owned by.
    name (str): The name of the target in the scope of the unit.
    dependencies (list of Target): A list of targets that are required
      to be executed before this target.
    status (str): The status of the target. One of the following values:
      ``'pending', 'setup', 'running', 'finished', 'failed'``, ``'skipped'``.
      A target will receive these statuses in the order read above where
      it makes sense (from pending to setup to skipped or running then to
      finished or failed).
    message (str): A message that is usually only set when an error occured.
      If an exception is raised during the execution of the target, it will
      be set to the exception message.
    condition (threading.Condition): A condition variable that should
      be used in case some implementation wants to run targets in multiple
      threads.
  """

  def __init__(self, unit, name):
    if not isinstance(unit, creator.unit.Unit):
      raise TypeError('unit must be creator.unit.Unit', type(unit))
    if not isinstance(name, str):
      raise TypeError('name must be str', type(name))
    if not creator.utils.validate_identifier(name):
      raise ValueError('name is not a valid identifier', name)
    super().__init__()
    self._unit = weakref.ref(unit)
    self._name = name
    self.dependencies = []
    self.status = 'pending'
    self.condition = threading.Condition()

  @property
  def unit(self):
    return self._unit()

  @property
  def name(self):
    return self._name

  @property
  def identifier(self):
    return self._unit().identifier + ':' + self._name

  def setup_target(self):
    """
    All targets get the chance to do some setup work. This may finally
    set up all the dependencies of the target or intialize internal data.
    """

    with self.condition:
      if self.status != 'pending':
        raise RuntimeError('{0} target can not be setup'.format(self.status))

    message = None
    success = False
    try:
      success = self._setup_target()
    except Exception as exc:
      message = str(exc)
      raise
    finally:
      with self.condition:
        self.message = message
        self.status = 'setup' if success else 'failed'

    return success

  def run_target(self):
    """
    Does what the target needs to do and updates the target status.
    This method will make sure that all dependencies of the target are
    met, but will only result in an exception instead of running them
    if they're not.
    """

    with self.condition:
      if self.status != 'setup':
        message = '{0} target "{1}" can not be run'
        raise RuntimeError(message.format(self.status, self.identifier))

      # Make sure all dependencies are actually targets and have
      # status "finished"
      for dep in self.dependencies:
        if not isinstance(dep, Target):
          message = 'target "{0}" has an invalid type dependency {1!r}'
          raise RuntimeError(message.format(self.identifier, dep))
        with dep.condition:
          if dep.status not in ('finished', 'skipped'):
            message = 'target "{0}" dependency "{1}" has status "{2}"'
            message = message.format(self.identifier, dep.name, dep.status)
            raise RuntimeError(message)

      self.status = 'running'

    message = None
    success = False
    try:
      success = self._run_target()
    except Exception as exc:
      message = str(exc)
      raise
    finally:
      with self.condition:
        self.message = message
        self.status = 'finished' if success else 'failed'

    return success

  @abc.abstractmethod
  def _setup_target(self):
    """
    Set up the targets internal data or dependencies.

    Returns:
      bool: True on success, False if an error occured.
    """

    return False

  @abc.abstractmethod
  def _run_target(self):
    """
    Do what the target needs to do. This function is called from the
    :meth:`run_target` method which takes care of some status updates
    before and after the target is running.

    Returns:
      bool: True on success, False if an error occured.
    """

    return False


class FuncTarget(Target):
  """
  This :class:`Target` implementation wraps a Python function.
  """

  def __init__(self, func):
    super().__init__()
    self.func = func

  def _run_target(self):
    result = self.func()
    if result is None:
      result = True
    return result


class ShellTarget(Target):
  """
  This :class:`Target` implementation is supposed to be used for targets
  in unit scripts. It associates each zero or more input and output files
  with one or more commands that are supposed to be run in the systems
  command shell.

  The :meth:`add` function evaluates all arguments as macros. Just like
  the :meth:`creator.unit.Unit.eval` function, it takes the scope of the
  calling stack frame into account. Also, for the command macros, the
  special variables ``$<`` and ``$@`` are available which are aliases
  for the input and output file macros.

  Args:
    func (callable): The Python function that adds content to the target.
    data (list): A list of the data that was added via :meth:`add`.
  """

  def __init__(self, unit, name, func):
    super(ShellTarget, self).__init__(unit, name)
    self.func = func
    self.data = []

  def add(self, inputs, outputs, *commands):
    """
    Associated the *inputs* with the *outputs* being built by the
    specified *\*commands*. All parameters passed to this function must
    be strings that are automatically evaluated.

    Args:
      inputs (str): A listing of the input files.
      outputs (str): A listing of the output files.
      *commands (tuple of str): One or more commands to build the
        outputs from the inputs The special variables ``$<`` and
        ``$@`` are available to the macros specified to this parameter.
    """

    input_files = self.unit.eval(inputs, stack_depth=1)
    output_files = self.unit.eval(outputs, stack_depth=1)
    eval_commands = []
    supp_context = creator.macro.MutableContext()
    supp_context['<'] = creator.macro.TextNode(input_files)
    supp_context['@'] = creator.macro.TextNode(output_files)
    for command in commands:
      command = self.unit.eval(command, supp_context, stack_depth=1)
      eval_commands.append(command)
    self.data.append({
      'inputs': creator.utils.split(input_files),
      'outputs': creator.utils.split(output_files),
      'commands': eval_commands
    })

  def _setup_target(self):
    self.func()
    return True

  def _run_target(self):
    import subprocess, shlex
    for entry in self.data:
      # Make sure the directories of the output files exist.
      for fn in entry['outputs']:
        dirname = os.path.dirname(fn)
        if not os.path.exists(dirname):
          os.makedirs(dirname)
      for command in entry['commands']:
        print('$', command)
        command_args = shlex.split(command)
        code = subprocess.call(command_args)
        if code != 0:
          message = '"{0}" exited with returncode {1}'
          raise RuntimeError(message.format(command_args[0], code))
    return True
