# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import creator.macro
import creator.utils
import abc
import threading


class Target(object, metaclass=abc.ABCMeta):
  """
  Interface for target declarations. A target is basically just a process
  that will be executed when its dependencies are met. Multiple targets can
  be run from multiple threads as long as their member access is synchronized
  with the :attr:`condition` variable.

  Attributes:
    dependencies (list of Target): A list of targets that are required
      to be executed before this target.
    status (str): The status of the target. One of the following values:
      ``'pending', 'running', 'finished', 'failed'``.
    condition (threading.Condition): A condition variable that should
      be used in case some implementation wants to run targets in multiple
      threads.
  """

  def __init__(self):
    super().__init__()
    self.dependencies = []
    self.status = 'pending'
    self.condition = threading.Condition()

  def run_target(self):
    """
    Does what the target needs to do and updates the target status.
    """

    with self.condition:
      if self.status != 'pending':
        raise RuntimeError('{0} target can not be run'.format(self.status))
      self.status = 'running'

    try:
      success = self._run_target()
    except Exception:
      success = False
      raise
    finally:
      with self.condition:
        self.status = 'finished' if success else 'failed'

    return success

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
    unit (creator.unit.Unit): The unit that owns the target.
    name (str): The name of the target.
    func (callable): The Python function that adds content to the target.
    data (list): A list of the data that was added via :meth:`add`.
  """

  def __init__(self, unit, name, func):
    super(ShellTarget, self).__init__()
    self.unit = unit
    self.name = name
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
    self.data.append([input_files, output_files, eval_commands])

  def _run_target(self):
    # TODO
    raise NotImplementedError
