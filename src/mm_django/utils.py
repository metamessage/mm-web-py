"""Utility functions for mm_django.

Provides helpers for creating MetaMessage-encoded responses
and binding request data to models.
"""

from typing import Any, Type, TypeVar

from django.http import HttpRequest, HttpResponse
from metamessage import encode_from_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")


def mm_respond(data: Any, status_code: int = 200) -> HttpResponse:
    """Create a MetaMessage-encoded response.

    Args:
        data: Data to encode (model instance, dict, list, etc.)
        status_code: HTTP status code (default: 200)

    Returns:
        Django HttpResponse with MetaMessage-encoded body

    Example:
        return mm_respond(User(id=1, name="Alice"))
    """
    content = encode_from_value(data)
    return HttpResponse(
        content=content,
        status=status_code,
        content_type=CONTENT_TYPE_METAMESSAGE,
    )


def mm_error(message: str, status_code: int = 400) -> HttpResponse:
    """Create a MetaMessage-encoded error response.

    Args:
        message: Error message
        status_code: HTTP status code (default: 400)

    Returns:
        Django HttpResponse with error body

    Example:
        return mm_error("user not found", 404)
    """
    return mm_respond({"error": message}, status_code)


def mm_body(request: HttpRequest) -> Any:
    """Get decoded MetaMessage body from request.

    Args:
        request: Django request

    Returns:
        Decoded body data, or empty dict if not available
    """
    if hasattr(request, "mm_body"):
        return request.mm_body
    return {}


def bind_body(request: HttpRequest, target_model: Type[T]) -> T:
    """Bind decoded request body to a model.

    Args:
        request: Django request
        target_model: Model class to bind to

    Returns:
        Instance of target_model with request data

    Raises:
        ValueError: If no decoded body is available

    Example:
        user = bind_body(request, CreateUserRequest)
    """
    if not hasattr(request, "mm_body"):
        raise ValueError("No decoded body available. Add MMMiddleware to your Django settings.")

    data = request.mm_body
    if isinstance(data, dict):
        return target_model(**data)
    return target_model(**data)