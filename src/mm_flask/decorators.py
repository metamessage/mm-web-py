"""Flask route decorators for MetaMessage.

Provides:
- MMFlask: Flask extension that wraps a Flask app with MetaMessage support
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

import flask
from flask import Flask, Response, request
from metamessage import encode_from_value

from mm_core.types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def _get_mm_body() -> Dict[str, Any]:
    """Get decoded MetaMessage body from flask.g."""
    if hasattr(flask.g, "mm_body"):
        return flask.g.mm_body
    return {}


def _get_mm_query() -> Dict[str, Any]:
    """Get decoded MetaMessage query from flask.g."""
    if hasattr(flask.g, "mm_query"):
        return flask.g.mm_query
    return {}


class MMFlask:
    """Flask extension for MetaMessage protocol.

    Wraps a Flask app (or Blueprint) with MetaMessage route decorators
    that automatically:
    - Bind request parameters from query (GET/DELETE) or body (POST/PUT/PATCH)
    - Encode responses as binary MetaMessage

    Example:
        app = Flask(__name__)
        MMMiddleware(app)
        mm = MMFlask(app)

        @mm.get("/users")
        def list_users(req: User):
            return User(name=req.name, age=req.age)
    """

    def __init__(
        self,
        app: Union[Flask, flask.Blueprint],
        auto_options: bool = True,
    ):
        self.app = app
        self.auto_options = auto_options

    def _bind_params(self, param_type: type, method: str) -> Any:
        """Bind parameters from request body or query.

        Args:
            param_type: Parameter type
            method: HTTP method

        Returns:
            Bound parameter value
        """
        # Basic types are not bound (passed as-is from path params or defaults)
        basic_types = (int, str, bool, float, type(None))
        origin = getattr(param_type, '__origin__', None)
        if param_type in basic_types or origin is Union:
            return None  # Signal to skip binding

        # For POST/PUT/PATCH, bind from body
        if method in ('POST', 'PUT', 'PATCH'):
            data = _get_mm_body()
            return self._create_instance(param_type, data)

        # For GET/DELETE, bind from query
        if method in ('GET', 'DELETE'):
            query = _get_mm_query()
            return self._create_instance(param_type, query)

        return None

    def _create_instance(self, param_type: type, data: dict) -> Any:
        """Create an instance of param_type from data dict."""
        if not data:
            return None
        try:
            return param_type(**data)
        except (TypeError, Exception):
            # If the type can't be constructed with kwargs, return data as-is
            return data

    def _wrap_handler(self, func: F) -> F:
        """Wrap a handler function with MetaMessage encoding.

        Returns:
            Wrapped function that accepts no args and returns a Response.
        """
        sig = inspect.signature(func)

        def wrapper(*args: Any, **kwargs: Any) -> Response:
            bound_kwargs: Dict[str, Any] = {}

            for name, param in sig.parameters.items():
                t = param.annotation
                if t is inspect.Parameter.empty:
                    continue

                # Path params come from Flask's URL routing
                if name in kwargs:
                    bound_kwargs[name] = kwargs[name]
                    continue

                # Bind from query or body
                v = self._bind_params(t, request.method)
                if v is not None:
                    bound_kwargs[name] = v

            # Call the original handler with *args too (for endpoint-based usage)
            result = func(*args, **bound_kwargs)

            if isinstance(result, Response):
                return result

            try:
                content = encode_from_value(result)
                return Response(
                    response=content,
                    status=200,
                    content_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                return Response(
                    response=str(e),
                    status=500,
                    content_type="text/plain",
                )

        return wrapper  # type: ignore

    def _decorator(self, method: str, path: str) -> Callable[[F], F]:
        """Create a route decorator for the given HTTP method."""
        def decorator(func: F) -> F:
            wrapped = self._wrap_handler(func)
            route_method = getattr(self.app, method.lower())
            route_method(path)(wrapped)
            return wrapped
        return decorator

    def get(self, path: str) -> Callable[[F], F]:
        """GET route decorator."""
        return self._decorator("get", path)

    def post(self, path: str) -> Callable[[F], F]:
        """POST route decorator."""
        return self._decorator("post", path)

    def put(self, path: str) -> Callable[[F], F]:
        """PUT route decorator."""
        return self._decorator("put", path)

    def patch(self, path: str) -> Callable[[F], F]:
        """PATCH route decorator."""
        return self._decorator("patch", path)

    def delete(self, path: str) -> Callable[[F], F]:
        """DELETE route decorator."""
        return self._decorator("delete", path)