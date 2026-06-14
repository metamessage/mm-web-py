"""Route decorators for MetaMessage in FastAPI."""

import dataclasses
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from metamessage import Tag, decode_to_value, encode_from_value

from .middleware import MMMiddleware
from mm_core.types import CONTENT_TYPE_METAMESSAGE

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


async def get_mm_body(request: Request) -> Dict[str, Any]:
    """Get and decode MetaMessage body from request.

    Follows mm-web-go pattern: always binary MetaMessage.

    Args:
        request: FastAPI request

    Returns:
        Decoded body as dict

    Raises:
        HTTPException: If decoding fails
    """
    if hasattr(request.state, "_mm_decoded"):
        return request.state._mm_decoded
    if hasattr(request.state, "mm_body"):
        return request.state.mm_body

    body = await request.body()

    if not body:
        return {}

    # Binary MetaMessage
    try:
        return decode_to_value(body)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to decode MetaMessage body: {e}",
        ) from e


def MMBody(model: Optional[Type[T]] = None) -> Callable:
    """Create a dependency that parses MetaMessage body into a model.

    Similar to mm-gin's Bind().

    Args:
        model: Optional model class to bind into

    Returns:
        FastAPI dependency function

    Example:
        from typing import Annotated

        @app.post("/users")
        async def create_user(user: Annotated[User, MMBody(User)]):
            return user
    """
    async def dependency(request: Request) -> Union[Dict[str, Any], T]:
        data = await get_mm_body(request)

        if model is not None:
            return model(**data)

        return data

    return Depends(dependency)


def MMQuery(model: Type[T]) -> Callable:
    """Create a dependency that binds URL query parameters into a model.

    Similar to mm-gin's ShouldBindQuery().

    Args:
        model: Model class to bind query parameters into

    Returns:
        FastAPI dependency function

    Example:
        from typing import Annotated

        @app.get("/users")
        async def list_users(params: Annotated[ListUsersRequest, MMQuery(ListUsersRequest)]):
            return {"page": params.page}
    """
    async def dependency(request: Request) -> T:
        # Get bound query from middleware
        query = getattr(request.state, "mm_query", {})

        return model(**query)

    return Depends(dependency)


class MMDependency:
    """Dependency class for MetaMessage data.

    This class provides a convenient way to inject MetaMessage
    decoded data into route handlers.

    Example:
        from fastapi_mm import MMDependency

        @app.post("/users")
        async def create_user(user: MMDependency[User]):
            return user.data
    """

    def __init__(self, data: Any):
        """Initialize dependency.

        Args:
            data: Decoded data
        """
        self._data = data

    @property
    def data(self) -> Any:
        """Get the decoded data."""
        return self._data

    @classmethod
    def create_dependency(cls, model: Optional[Type[T]] = None) -> Callable:
        """Create a FastAPI dependency.

        Args:
            model: Optional Pydantic model to validate into

        Returns:
            FastAPI dependency function
        """
        async def dependency(request: Request) -> "MMDependency":
            # Check if body was already decoded
            if hasattr(request.state, "_mm_decoded"):
                data = request.state._mm_decoded
            elif hasattr(request.state, "mm_body"):
                data = request.state.mm_body
            else:
                body = await request.body()

                if not body:
                    data = {}
                else:
                    data = decode_to_value(body)

            # Validate into model if specified
            if model is not None and isinstance(data, dict):
                data = model(**data)

            return cls(data, format)

        return Depends(dependency)


def create_mm_dependency(model: Type[T]) -> Callable[[], T]:
    """Create a typed dependency for MetaMessage body.

    This is a convenience function that creates a dependency
    which returns the validated model instance directly.

    Args:
        model: Model type

    Returns:
        FastAPI dependency function

    Example:
        UserDep = create_mm_dependency(User)

        @app.post("/users")
        async def create_user(user: UserDep):
            return user
    """
    async def dependency(request: Request) -> T:
        body = await request.body()

        if not body:
            return model()

        data = decode_to_value(body)
        return model(**data)

    return Depends(dependency)


# Type alias for convenience
MMDep = MMDependency


class MMRoute:
    """Route decorator class for MetaMessage endpoints.
    
    This class provides route decorators that automatically handle
    MetaMessage encoding and decoding.
    
    Example:
        from fastapi_mm import mm_route
        
        @mm_route.post("/users")
        async def create_user(user: User):
            return user
        
        @mm_route.get("/users/{user_id}")
        async def get_user(user_id: int):
            return {"id": user_id, "name": "Alice"}
    """
    
    def __init__(
        self,
        router: Optional[APIRouter] = None,
        prefix: str = "",
        tags: Optional[List[str]] = None,
    ):
        """Initialize MM route decorator.
        
        Args:
            router: FastAPI router to use (creates new one if None)
            prefix: URL prefix for all routes
            tags: Tags for all routes
        """
        self.router = router or APIRouter(prefix=prefix, tags=tags)
    
    def _create_route_handler(
        self,
        method: str,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 200,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """Create a route handler decorator.
        
        Args:
            method: HTTP method
            path: URL path
            response_model: Response model
            status_code: HTTP status code
            **kwargs: Additional route options
            
        Returns:
            Route decorator function
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Response:
                # Call the original handler
                result = await func(request, *args, **kwargs)
                
                # If result is already a Response, return as-is
                if isinstance(result, Response):
                    return result
                
                # Encode result as binary MetaMessage
                try:
                    content = encode_from_value(result)
                    return Response(
                        content=content,
                        status_code=status_code,
                        media_type=CONTENT_TYPE_METAMESSAGE,
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to encode response: {e}",
                    ) from e
            
            # Register route
            route_method = getattr(self.router, method.lower())
            route_method(
                path,
                response_model=response_model,
                status_code=status_code,
                **kwargs,
            )(wrapper)
            
            return wrapper  # type: ignore
        
        return decorator
    
    def get(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 200,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """GET route decorator.
        
        Args:
            path: URL path
            response_model: Response model
            status_code: HTTP status code
            **kwargs: Additional route options
            
        Returns:
            Route decorator
        """
        return self._create_route_handler(
            "get", path, response_model, status_code, **kwargs
        )
    
    def post(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 201,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """POST route decorator.
        
        Args:
            path: URL path
            response_model: Response model
            status_code: HTTP status code
            **kwargs: Additional route options
            
        Returns:
            Route decorator
        """
        return self._create_route_handler(
            "post", path, response_model, status_code, **kwargs
        )
    
    def put(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 200,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """PUT route decorator."""
        return self._create_route_handler(
            "put", path, response_model, status_code, **kwargs
        )
    
    def patch(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 200,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """PATCH route decorator."""
        return self._create_route_handler(
            "patch", path, response_model, status_code, **kwargs
        )
    
    def delete(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 204,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """DELETE route decorator."""
        return self._create_route_handler(
            "delete", path, response_model, status_code, **kwargs
        )
    
    def head(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 200,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """HEAD route decorator."""
        return self._create_route_handler(
            "head", path, response_model, status_code, **kwargs
        )
    
    def options(
        self,
        path: str,
        response_model: Optional[Type] = None,
        status_code: int = 200,
        **kwargs: Any,
    ) -> Callable[[F], F]:
        """OPTIONS route decorator."""
        return self._create_route_handler(
            "options", path, response_model, status_code, **kwargs
        )


# Default instance for convenience
mm_route = MMRoute()


def mm_api(
    path: str,
    method: str = "GET",
    response_model: Optional[Type] = None,
    status_code: int = 200,
    **kwargs: Any,
) -> Callable[[F], F]:
    """Generic API decorator for MetaMessage endpoints.
    
    This is a simpler decorator for creating MM endpoints
    without using the MMRoute class.
    
    Args:
        path: URL path
        method: HTTP method
        response_model: Response model
        status_code: HTTP status code
        **kwargs: Additional route options
        
    Returns:
        Route decorator
        
    Example:
        @mm_api("/users", method="POST")
        async def create_user(user: User):
            return user
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Response:
            result = await func(request, *args, **kwargs)
            
            if isinstance(result, Response):
                return result
            
            try:
                content = encode_from_value(result)
                return Response(
                    content=content,
                    status_code=status_code,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to encode response: {e}",
                ) from e
        
        return wrapper  # type: ignore
    
    return decorator


def _is_mm_model(cls: type) -> bool:
    """Check if a class is an MM model (has @mm decorator)."""
    return hasattr(cls, '_mm_schema') or (hasattr(cls, '__annotations__') and hasattr(cls, '_mm_fields'))


def _clean_mm_defaults(instance: Any) -> Any:
    """Replace metamessage field descriptor defaults with None.
    
    When a @dataclass model uses `name: str = mm(desc="...")`, the field 
    default IS an mm() instance. When no data is provided (empty query/body),
    constructing the model gives mm objects as values. This helper replaces 
    those with None so handlers can work with proper types.
    """
    if not dataclasses.is_dataclass(instance):
        return instance
    for field_def in dataclasses.fields(instance):
        val = getattr(instance, field_def.name)
        # mm is itself a dataclass, so check the class name
        if type(val).__name__ == "mm":
            setattr(instance, field_def.name, None)
    return instance


def _make_empty_instance(model: type) -> Any:
    """Create a model instance without calling __init__, setting all fields to None.
    
    Handles models that can't be instantiated without arguments (e.g., mm descriptor
    fields without proper defaults). Falls back to the model itself if unavailable.
    """
    try:
        inst = object.__new__(model)
        for name in getattr(model, '__annotations__', {}):
            if not name.startswith('_'):
                setattr(inst, name, None)
        return inst
    except Exception:
        return model()


async def _bind_params(
    request: Request,
    param_type: type,
    method: str,
) -> Any:
    """Bind parameters from request body or query.
    
    Args:
        request: FastAPI request
        param_type: Parameter type
        method: HTTP method
        
    Returns:
        Bound parameter value
    """
    # Special case: if parameter type is Request, return the request itself
    if param_type is Request:
        return request
    
    # Path parameters are handled by FastAPI automatically
    basic_types = (int, str, bool, float)
    if param_type in basic_types or (hasattr(param_type, '__origin__') and param_type.__origin__ in (Union, Optional)):
        # Let FastAPI handle basic types via its normal dependency injection
        return None  # Signal to use FastAPI's default handling
    
    # For POST/PUT/PATCH, bind from body
    if method in ('POST', 'PUT', 'PATCH'):
        data = await get_mm_body(request)

        if _is_mm_model(param_type):
            try:
                return _clean_mm_defaults(param_type(**data))
            except (TypeError, ValueError):
                return _make_empty_instance(param_type)
        elif hasattr(param_type, '__init__'):
            try:
                return _clean_mm_defaults(param_type(**data))
            except (TypeError, ValueError):
                return _make_empty_instance(param_type)
        else:
            return data

    # For GET/DELETE, bind from query
    if method in ('GET', 'DELETE'):
        query = getattr(request.state, 'mm_query', {})

        if _is_mm_model(param_type):
            try:
                return _clean_mm_defaults(param_type(**query))
            except (TypeError, ValueError):
                return _make_empty_instance(param_type)
        elif hasattr(param_type, '__init__'):
            try:
                return _clean_mm_defaults(param_type(**query))
            except (TypeError, ValueError):
                return _make_empty_instance(param_type)
        else:
            return query
    
    return None


def mm_get(
    path: str,
    response_model: Optional[Type] = None,
    status_code: int = 200,
    **kwargs: Any,
) -> Callable[[F], F]:
    """GET route decorator with automatic parameter binding.
    
    Similar to mm-web-go's pattern - parameters are automatically bound
    from URL query.
    
    Automatically registers an OPTIONS endpoint for schema discovery.
    
    Args:
        path: URL path
        response_model: Response model
        status_code: HTTP status code
        **kwargs: Additional route options
        
    Returns:
        Route decorator
        
    Example:
        @mm_get("/users")
        async def list_users(params: ListUsersRequest):
            return {"users": [], "total": 0}
    """
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        async def wrapper(request: Request) -> Response:
            bound_args = {}
            
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                
                # Skip if no annotation or it's Request
                if param_type is inspect.Parameter.empty or param_type is Request:
                    if param_type is Request:
                        bound_args[param_name] = request
                    continue
                
                # Handle path parameters
                if param_name in request.path_params:
                    bound_args[param_name] = request.path_params[param_name]
                    continue
                
                # Bind from query
                value = await _bind_params(request, param_name, param_type, 'GET')
                if value is not None:
                    bound_args[param_name] = value
            
            # Call the original function
            result = await func(**bound_args)
            
            if isinstance(result, Response):
                return result
            
            try:
                content = encode_from_value(result)
                return Response(
                    content=content,
                    status_code=status_code,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to encode response: {e}",
                ) from e
        
        return wrapper  # type: ignore
    
    return decorator


def mm_post(
    path: str,
    response_model: Optional[Type] = None,
    status_code: int = 201,
    **kwargs: Any,
) -> Callable[[F], F]:
    """POST route decorator with automatic parameter binding.
    
    Similar to mm-web-go's pattern - parameters are automatically bound
    from request body.
    
    Args:
        path: URL path
        response_model: Response model
        status_code: HTTP status code
        **kwargs: Additional route options
        
    Returns:
        Route decorator
        
    Example:
        @mm_post("/users")
        async def create_user(user: CreateUserRequest):
            return {"id": 1, "name": user.name}
    """
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        async def wrapper(request: Request) -> Response:
            bound_args = {}
            
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                
                # Skip if no annotation
                if param_type is inspect.Parameter.empty:
                    continue
                
                # Handle path parameters
                if param_name in request.path_params:
                    bound_args[param_name] = request.path_params[param_name]
                    continue
                
                # Bind from body
                value = await _bind_params(request, param_name, param_type, 'POST')
                if value is not None:
                    bound_args[param_name] = value
            
            # Call the original function
            result = await func(**bound_args)
            
            if isinstance(result, Response):
                return result
            
            try:
                content = encode_from_value(result)
                return Response(
                    content=content,
                    status_code=status_code,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to encode response: {e}",
                ) from e
        
        return wrapper  # type: ignore
    
    return decorator


def mm_put(
    path: str,
    response_model: Optional[Type] = None,
    status_code: int = 200,
    **kwargs: Any,
) -> Callable[[F], F]:
    """PUT route decorator with automatic parameter binding."""
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        async def wrapper(request: Request) -> Response:
            bound_args = {}
            
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                
                if param_type is inspect.Parameter.empty:
                    continue
                
                if param_name in request.path_params:
                    bound_args[param_name] = request.path_params[param_name]
                    continue
                
                value = await _bind_params(request, param_name, param_type, 'PUT')
                if value is not None:
                    bound_args[param_name] = value
            
            result = await func(**bound_args)
            
            if isinstance(result, Response):
                return result
            
            try:
                content = encode_from_value(result)
                return Response(
                    content=content,
                    status_code=status_code,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to encode response: {e}",
                ) from e
        
        return wrapper  # type: ignore
    
    return decorator


def mm_patch(
    path: str,
    response_model: Optional[Type] = None,
    status_code: int = 200,
    **kwargs: Any,
) -> Callable[[F], F]:
    """PATCH route decorator with automatic parameter binding."""
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        async def wrapper(request: Request) -> Response:
            bound_args = {}
            
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                
                if param_type is inspect.Parameter.empty:
                    continue
                
                if param_name in request.path_params:
                    bound_args[param_name] = request.path_params[param_name]
                    continue
                
                value = await _bind_params(request, param_name, param_type, 'PATCH')
                if value is not None:
                    bound_args[param_name] = value
            
            result = await func(**bound_args)
            
            if isinstance(result, Response):
                return result
            
            try:
                content = encode_from_value(result)
                return Response(
                    content=content,
                    status_code=status_code,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to encode response: {e}",
                ) from e
        
        return wrapper  # type: ignore
    
    return decorator


def mm_delete(
    path: str,
    response_model: Optional[Type] = None,
    status_code: int = 200,
    **kwargs: Any,
) -> Callable[[F], F]:
    """DELETE route decorator with automatic parameter binding."""
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        async def wrapper(request: Request) -> Response:
            bound_args = {}
            
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                
                if param_type is inspect.Parameter.empty:
                    continue
                
                if param_name in request.path_params:
                    bound_args[param_name] = request.path_params[param_name]
                    continue
                
                value = await _bind_params(request, param_name, param_type, 'DELETE')
                if value is not None:
                    bound_args[param_name] = value
            
            result = await func(**bound_args)
            
            if isinstance(result, Response):
                return result
            
            try:
                content = encode_from_value(result)
                return Response(
                    content=content,
                    status_code=status_code,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to encode response: {e}",
                ) from e
        
        return wrapper  # type: ignore
    
    return decorator


class MMRouter(APIRouter):
    """Extended APIRouter with MetaMessage support and automatic OPTIONS.
    
    Similar to mm-web-go: automatically registers with app on creation
    and registers OPTIONS endpoints for schema discovery.
    
    Example:
        router = MMRouter(app)
        
        @router.post("/users")
        async def create_user(user: User):
            return user
    """
    
    def __init__(
        self,
        app: Optional[FastAPI] = None,
        auto_options: bool = True,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.auto_options = auto_options
        self._app = app
        if app is not None:
            app.add_middleware(MMMiddleware)

    def _get_request_model(self, endpoint: Callable) -> Optional[Type]:
        sig = inspect.signature(endpoint)
        for _, param in sig.parameters.items():
            t = param.annotation
            if t is inspect.Parameter.empty or t is Request or t in (int, str, bool, float):
                continue
            if hasattr(t, '__origin__') and t.__origin__ in (Union, Optional):
                continue
            return t
        return None

    def _create_options_handler(self, model: Type) -> Callable:
        async def handler(request: Request) -> Response:
            try:
                # Try normal instantiation first
                try:
                    inst = model() if hasattr(model, '__init__') else model
                except TypeError:
                    # Model can't be instantiated without args (e.g., mm-descriptor fields
                    # without proper defaults). Build schema dict from annotations.
                    inst = {}
                    for name in getattr(model, '__annotations__', {}):
                        if name.startswith('_'):
                            continue
                        default = getattr(model, name, None)
                        inst[name] = default
                # Pass model instance directly to encode_from_value so it can
                # use type annotations to infer ValueType for None values.
                return Response(
                    content=encode_from_value(inst, tag=Tag(example=True)),
                    status_code=200,
                    media_type=CONTENT_TYPE_METAMESSAGE,
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
        return handler

    def _wrap_handler(self, func: F, status_code: Optional[int] = None) -> F:
        if status_code is None:
            status_code = 200
        sig = inspect.signature(func)
        async def wrapper(request: Request) -> Response:
            kwargs = {}
            for name, param in sig.parameters.items():
                t = param.annotation
                if t is inspect.Parameter.empty:
                    continue
                if t is Request:
                    kwargs[name] = request
                elif name in request.path_params:
                    value = request.path_params[name]
                    if t is not str:
                        try:
                            value = t(value)
                        except (ValueError, TypeError):
                            pass
                    kwargs[name] = value
                else:
                    v = await _bind_params(request, t, request.method)
                    if v is not None:
                        kwargs[name] = v
            result = await func(**kwargs)
            if isinstance(result, Response):
                return result
            try:
                content = encode_from_value(result)
                return Response(content=content, status_code=status_code, media_type=CONTENT_TYPE_METAMESSAGE)
            except Exception as e:
                # Return error as status 200 with MetaMessage encoding
                try:
                    content = encode_from_value({"error": str(e)})
                except Exception:
                    content = b"error:" + str(e).encode()
                return Response(content=content, status_code=200, media_type=CONTENT_TYPE_METAMESSAGE)
        return wrapper  # type: ignore

    def add_api_route(self, path: str, endpoint: Callable, *, status_code: Optional[int] = None, methods: Optional[List[str]] = None, **kwargs: Any) -> None:
        # Default to 200 for all methods
        if status_code is None:
            status_code = 200
        wrapped = self._wrap_handler(endpoint, status_code)
        app = self._app
        if app is not None:
            app.router.add_api_route(path, wrapped, status_code=status_code, methods=methods, **kwargs)
        else:
            super().add_api_route(path, wrapped, status_code=status_code, methods=methods, **kwargs)
        if self.auto_options:
            model = self._get_request_model(endpoint)
            if model:
                options_handler = self._create_options_handler(model)
                if app is not None:
                    app.router.add_api_route(path, options_handler, methods=["OPTIONS"])
                else:
                    super().add_api_route(path, options_handler, methods=["OPTIONS"])
