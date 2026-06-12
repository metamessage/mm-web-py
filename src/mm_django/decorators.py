"""Django view decorators for MetaMessage.

Provides:
- mm_view: Decorator for function-based views that binds params and encodes responses
"""

import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from django.http import HttpRequest, HttpResponse
from metamessage import encode_from_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def _is_mm_model(cls: type) -> bool:
    """Check if a class is an MM model."""
    return hasattr(cls, "_mm_schema") or (
        hasattr(cls, "__annotations__") and hasattr(cls, "_mm_fields")
    )


def _create_instance(param_type: Type[T], data: dict) -> Optional[T]:
    """Create an instance of param_type from data dict."""
    if not data:
        return None
    try:
        # If it's an mm model or regular class, construct from kwargs
        if _is_mm_model(param_type) or hasattr(param_type, "__init__"):
            return param_type(**data)
    except (TypeError, Exception):
        pass
    # Fallback: return data as-is
    return data  # type: ignore


def _bind_params(request: HttpRequest, param_type: type) -> Any:
    """Bind parameters from request body or query.

    Args:
        request: Django request
        param_type: Parameter type annotation

    Returns:
        Bound parameter value, or None if binding is not applicable
    """
    # Basic types are not bound (handled by Django's URL params)
    basic_types = (int, str, bool, float, type(None))
    origin = getattr(param_type, "__origin__", None)
    if param_type in basic_types or origin is Union:
        return None

    method = request.method
    if method in ("POST", "PUT", "PATCH"):
        body = getattr(request, "mm_body", {})
        return _create_instance(param_type, body)

    if method in ("GET", "DELETE"):
        query = getattr(request, "mm_query", {})
        return _create_instance(param_type, query)

    return None


def mm_view(status_code: int = 200) -> Callable[[F], F]:
    """Decorator for Django views that binds MetaMessage params and encodes responses.

    The decorator:
    - Binds request body/query params to model-annotated parameters
    - Encodes the return value as binary MetaMessage
    - Passes through HttpResponse return values unchanged

    Args:
        status_code: HTTP status code for the response (default: 200)

    Returns:
        View decorator

    Example:
        @mm_view()
        def create_user(request, req: CreateUserRequest):
            return CreateUserResponse(id=1, name=req.name, age=req.age)

        @mm_view()
        def list_users(request, req: ListUsersRequest):
            return {"users": [...], "total": 0}
    """
    def decorator(view_func: F) -> F:
        sig = inspect.signature(view_func)

        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            bound_kwargs: Dict[str, Any] = {}

            for name, param in sig.parameters.items():
                if name == "request":
                    bound_kwargs[name] = request
                    continue

                t = param.annotation
                if t is inspect.Parameter.empty:
                    continue

                # URL path params from kwargs
                if name in kwargs:
                    bound_kwargs[name] = kwargs[name]
                    continue

                # Bind from query or body
                v = _bind_params(request, t)
                if v is not None:
                    bound_kwargs[name] = v

            result = view_func(*args, **bound_kwargs)

            if isinstance(result, HttpResponse):
                return result

            try:
                content = encode_from_value(result)
                return HttpResponse(
                    content=content,
                    status=status_code,
                    content_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                return HttpResponse(
                    content=str(e),
                    status=500,
                    content_type="text/plain",
                )

        return wrapper  # type: ignore

    return decorator