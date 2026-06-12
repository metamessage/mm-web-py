"""Flask extension for MetaMessage protocol.

Provides:
- MMFlask: Flask extension with automatic MetaMessage encoding/decoding
- Route decorators (.get, .post, .put, .delete, .patch)
- Utilities (mm_respond, mm_error, etc.)

Example:
    from flask import Flask
    from flask_mm import MMFlask

    app = Flask(__name__)
    mm = MMFlask(app)

    @mm.get("/users")
    def list_users(req: User):
        return User(name=req.name, age=req.age)
"""

from .decorators import MMFlask
from .middleware import MMMiddleware
from .utils import bind_body, mm_body, mm_error, mm_options_handler, mm_respond

__all__ = [
    "MMFlask",
    "MMMiddleware",
    "mm_respond",
    "mm_error",
    "mm_options_handler",
    "mm_body",
    "bind_body",
]