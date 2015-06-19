# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import re


def validate_unit_identifier(identifier):
  """
  Args:
    identifier (str): The identifier to test.
  Returns:
    bool: True if the *identifier* is a valid identifier for a unit,
      False if it is not.
  """

  return bool(re.match('^[A-Za-z0-9\-\._]+$', identifier))
