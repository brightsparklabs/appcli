# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

import sys
from contextlib import contextmanager

import pyfiglet

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

__BANNER = pyfiglet.figlet_format("DEV MODE", font="tinker-toy")

# ------------------------------------------------------------------------------
# METHODS
# ------------------------------------------------------------------------------


@contextmanager
def wrap_dev_mode():
    """
    Creates a context which prints DEV MODE markings around all output shown on terminal.

    EXAMPLE:

      The below code:

        if dev_mode_enabled:
          with wrap_dev_mode:
            ...
            logger.info("DEV MODE operation successfuly")

      Would result in everything printed by code in the `with` block being bookended by DEV MODE
      markings.
    """

    print(
        f"""
{"<" * 70} DEV MODE BEGIN

{__BANNER}
""",
        file=sys.stderr,
    )

    yield

    print(
        f"""
{">" * 70} DEV MODE END
""",
        file=sys.stderr,
    )
