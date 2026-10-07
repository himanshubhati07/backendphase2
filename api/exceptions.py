"""Exception facade.

The response-envelope exception handler and ``Conflict`` domain exception are
canonically owned by :mod:`config.exceptions` and are re-exported here.
"""

from config.exceptions import Conflict, api_exception_handler

__all__ = ("Conflict", "api_exception_handler")
