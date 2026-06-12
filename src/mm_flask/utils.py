"""Utility functions for flask_mm.

Provides Respond, error handling utilities
similar to mm-gin's middleware.go patterns.
"""

from typing import Any, Type, TypeVar

import flask
from flask import Response
from metamessage import encode_from_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")


def mm_respond(data: Any, status_code: int = 200) -> Response:
    """Create a MetaMessage-encoded response."""
    content = encode_from_value(data)
    return Response(
        response=content,
        status=status_code,
        content_type=CONTENT_TYPE_METAMESSAGE,
    )


def mm_error(message: str, status_code: int = 400) -> Response:
    """Create a MetaMessage-encoded error response."""
    return mm_respond({"error": message}, status_code)


def mm_options_handler(model_instance: Any) -> Response:
    """Create an OPTIONS response for Schema discovery."""
    if hasattr(model_instance, "__dict__"):
        data = model_instance.__dict__
    else:
        data = dict(model_instance)
    return mm_respond(data, status_code=200)


def mm_body() -> Any:
    """Get decoded body from flask.g."""
    if hasattr(flask.g, "mm_body"):
        return flask.g.mm_body
    if hasattr(flask.g, "_mm_raw"):
        return flask.g._mm_raw
    return {}


def bind_body(target_model: Type[T]) -> T:
    """Bind request body to a model.

    Args:
        target_model: Model class to bind to

    Returns:
        Instance of target_model with request data

    Raises:
        ValueError: If binding fails
    """
    if not hasattr(flask.g, "mm_body"):
        raise ValueError("No decoded body available. Add MMMiddleware to your app.")

    data = flask.g.mm_body
    if isinstance(data, dict):
        return target_model(**data)
    return target_model(**data)