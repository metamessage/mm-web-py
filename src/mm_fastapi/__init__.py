"""FastAPI plugin for MetaMessage protocol.

This package provides seamless integration between FastAPI and MetaMessage,
supporting binary MetaMessage format.

Example:
    from fastapi import FastAPI
    from fastapi_mm import MMMiddleware, mm_route

    app = FastAPI()
    app.add_middleware(MMMiddleware)

    @app.post("/user/create")
    async def create_user(user: User):
        return user
"""

from mm_core.client import (
    AsyncMMClient,
    MMClient,
    MMClientError,
    MMResponse,
)
from .decorators import MMDependency, MMDep, MMBody, MMQuery, MMRouter, create_mm_dependency, get_mm_body
from .middleware import MMRequestMiddleware, MMMiddleware
from mm_core.types import (
    CONTENT_TYPE_METAMESSAGE,
    MMDecoderError,
    MMEncoderError,
    MMRequest,
    MMResponse as MMResponseType,
)
from .utils import (
    bind_body,
    mm_body,
    mm_error,
    mm_options_handler,
    mm_respond,
)

__version__ = "0.1.0"
__all__ = [
    # Core types
    "MMRequest",
    "MMResponseType",
    "MMEncoderError",
    "MMDecoderError",
    # Middleware
    "MMMiddleware",
    "MMRequestMiddleware",
    # Dependencies
    "MMBody",
    "MMQuery",
    "MMDependency",
    "MMDep",
    "get_mm_body",
    "create_mm_dependency",
    # Decorators
    "MMRouter",
    # Client SDK
    "MMClient",
    "AsyncMMClient",
    "MMResponse",
    "MMClientError",
    # Utilities
    "mm_respond",
    "mm_error",
    "mm_options_handler",
    "mm_body",
    "bind_body",
]