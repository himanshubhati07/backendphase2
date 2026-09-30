from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import secrets
from typing import Any
from flask import request
from app.errors import AuthenticationError


def require_api_key(api_keys: tuple[str, ...]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            candidate = request.headers.get("X-API-Key", "")
            if not candidate or not any(secrets.compare_digest(candidate, key) for key in api_keys):
                raise AuthenticationError("Missing or invalid API key")
            return view(*args, **kwargs)
        return guarded
    return decorator
