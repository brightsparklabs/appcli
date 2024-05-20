# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

import sys
from contextlib import contextmanager

import pyfiglet

from appcli.logger import configure_default_logging, enable_dev_mode_logging

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
          with wrap_dev_mode():
            ...
            logger.info("DEV MODE operation completed successfully")

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

    enable_dev_mode_logging()
    yield
    configure_default_logging()

    print(
        f"""
{">" * 70} DEV MODE END
""",
        file=sys.stderr,
    )
