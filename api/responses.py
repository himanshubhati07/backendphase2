"""Response facade.

``success_response`` is implemented by :mod:`config.responses`; this module
re-exports that canonical helper without defining a second response envelope.
"""

from config.responses import success_response

__all__ = ("success_response",)
