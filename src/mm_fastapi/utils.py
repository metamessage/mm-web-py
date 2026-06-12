"""Utility functions for fastapi-mm server-side helpers.

Provides Respond, OptionsHandler, Validator, and error handling utilities
similar to mm-gin's binding.go middleware.go patterns.
"""

from typing import Any, Type, TypeVar

from fastapi import Request, Response
from metamessage import encode_from_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")


def mm_respond(data: Any, status_code: int = 200) -> Response:
    """Create a MetaMessage-encoded response."""
    content = encode_from_value(data)
    return Response(
        content=content,
        status_code=status_code,
        media_type=CONTENT_TYPE_METAMESSAGE,
    )


def mm_error(message: str, status_code: int = 400) -> Response:
    """Create a MetaMessage-encoded error response.

    Similar to ginmm.AbortWithMetaMessage() in mm-gin.

    Args:
        message: Error message
        status_code: HTTP status code

    Returns:
        FastAPI Response with error body

    Example:
        @app.get("/users/{id}")
        async def get_user(id: int):
            if not user:
                return mm_error("user not found", 404)
    """
    return mm_respond({"error": message}, status_code)


def mm_options_handler(model_instance: Any) -> Response:
    """Create an OPTIONS response for Schema discovery.

    Similar to ginmm.OptionsHandler() in mm-gin.
    Returns MetaMessage-encoded structure of the model, allowing clients
    to discover request format, types, constraints, and descriptions.

    Args:
        model_instance: An instance of the model (with example values)

    Returns:
        FastAPI Response with MetaMessage-encoded schema

    Example:
        @app.options("/users")
        async def options_users():
            return mm_options_handler(CreateUserRequest(name="", email="", age=0))
    """
    if hasattr(model_instance, "__dict__"):
        data = model_instance.__dict__
    else:
        data = dict(model_instance)
    
    return mm_respond(data, status_code=200)


def mm_body(request: Request) -> bytes:
    """Get raw body from request state (set by middleware).

    Similar to c.Get("mm_raw_body") in mm-gin.

    Args:
        request: FastAPI request

    Returns:
        Raw request body bytes
    """
    if hasattr(request.state, "_mm_raw_body"):
        return request.state._mm_raw_body

    # Fallback: body was already consumed, return empty
    return b""


def bind_body(
    request: Request,
    target_model: Type[T],
) -> T:
    """Bind request body to a model.

    Similar to ginmm.Bind() in mm-gin.

    Args:
        request: FastAPI request
        target_model: Model class to bind to

    Returns:
        Instance of target_model with request data

    Raises:
        ValueError: If binding fails

    Example:
        @app.post("/users")
        async def create_user(request: Request):
            user = bind_body(request, User)
            return mm_respond({"created": user.name})
    """
    if hasattr(request.state, "_mm_decoded"):
        decoded = request.state._mm_decoded
    else:
        raise ValueError("No decoded body available. Add MMMiddleware to your app.")

    if isinstance(decoded, dict):
        return target_model(**decoded)
    return target_model(**decoded)


def bind_query(
    request: Request,
    target_model: Type[T],
) -> T:
    """Bind URL query parameters to a model.

    Similar to ginmm.ShouldBindQuery() in mm-gin.

    Args:
        request: FastAPI request
        target_model: Model class to bind to

    Returns:
        Instance of target_model with query parameters

    Example:
        @app.get("/users")
        async def list_users(request: Request):
            params = bind_query(request, ListUsersRequest)
            return mm_respond({"page": params.page})
    """
    query_params = dict(request.query_params)
    
    if hasattr(target_model, "__annotations__"):
        hints = target_model.__annotations__
    else:
        hints = {}
    
    for field_name, field_type in hints.items():
        if field_name in query_params:
            value = query_params[field_name]
            
            # Convert to appropriate type
            if field_type is int:
                converted_params[field_name] = int(value)
            elif field_type is bool:
                converted_params[field_name] = value.lower() == "true"
            elif field_type is float:
                converted_params[field_name] = float(value)
            else:
                converted_params[field_name] = value
    
    return target_model(**converted_params)