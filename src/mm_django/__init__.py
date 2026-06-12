"""Django extension for MetaMessage protocol.

Provides:
- MMMiddleware: Django middleware for MetaMessage request/response handling
- mm_view: View decorator for automatic parameter binding and response encoding
- Utilities (mm_respond, mm_error, mm_body, bind_body)

Example:
    # settings.py
    MIDDLEWARE = [
        ...
        'mm_django.middleware.MMMiddleware',
    ]

    # views.py
    from mm_django import mm_view

    @mm_view()
    def create_user(request, req: CreateUserRequest):
        return CreateUserResponse(id=1, name=req.name, age=req.age)
"""

from .decorators import mm_view
from .middleware import MMMiddleware
from .utils import bind_body, mm_body, mm_error, mm_respond

__all__ = [
    "MMMiddleware",
    "mm_view",
    "mm_respond",
    "mm_error",
    "mm_body",
    "bind_body",
]