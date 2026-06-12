"""Basic example for mm_django.

Demonstrates using MMMiddleware and @mm_view decorator.

Run: python basic_example.py
Test: curl http://localhost:8000/users/?data=<hex>
"""

from dataclasses import dataclass

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from metamessage import mm

from mm_django import MMMiddleware, mm_view

# Configure Django minimally
settings.configure(
    DEBUG=True,
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[
        "mm_django.middleware.MMMiddleware",
    ],
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
    ],
)
import django
django.setup()


@mm(desc="User create request")
@dataclass
class CreateUserRequest:
    name: str
    age: int
    email: str


@mm(desc="User create response")
@dataclass
class CreateUserResponse:
    id: int
    name: str
    age: int


@mm_view()
def create_user(request: HttpRequest, req: CreateUserRequest) -> HttpResponse:
    """Create a new user."""
    return CreateUserResponse(id=1, name=req.name, age=req.age)


@mm_view()
def get_user(request: HttpRequest, user_id: int, req: CreateUserRequest) -> HttpResponse:
    """Get user with hex-encoded query params."""
    return {
        "id": user_id,
        "name": req.name,
        "age": req.age,
    }


@mm_view()
def delete_user(request: HttpRequest, user_id: int) -> HttpResponse:
    """Delete a user."""
    return {
        "id": user_id,
        "deleted": True,
    }


# URL patterns
from django.urls import path

urlpatterns = [
    path("users/", create_user, name="create_user"),
    path("users/<int:user_id>/", get_user, name="get_user"),
    path("users/<int:user_id>/delete/", delete_user, name="delete_user"),
]


# WSGI application
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    import sys

    print("Starting Django server with MetaMessage support...")
    print()
    print("Endpoints:")
    print("  POST   /users/               - Create user (MetaMessage body)")
    print("  GET    /users/<id>/?data=... - Get user")
    print("  DELETE /users/<id>/delete/   - Delete user")
    print()
    sys.argv = [sys.argv[0], "runserver", "0.0.0.0:8000"]
    execute_from_command_line(sys.argv)