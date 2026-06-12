"""Tests for mm_django - MetaMessage Django extension."""

import os
from dataclasses import dataclass
from typing import Optional

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_settings")

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        ROOT_URLCONF="tests.test_mm_django",
        MIDDLEWARE=[
            "mm_django.middleware.MMMiddleware",
        ],
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ],
    )
django.setup()

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from metamessage import decode_to_value, encode_from_value, mm

from mm_core.types import CONTENT_TYPE_METAMESSAGE
from mm_django import MMMiddleware, mm_respond, mm_view


# Test model
@mm(desc="Test user model")
@dataclass
class TestUser:
    """Test user model."""
    name: str
    age: int
    email: Optional[str] = None


# Test fixtures
@pytest.fixture
def rf() -> RequestFactory:
    """Create request factory."""
    return RequestFactory()


# Middleware tests
class TestMiddleware:
    """Tests for MMMiddleware."""

    def test_middleware_skip_routes(self, rf: RequestFactory):
        """Test skip routes pass through."""
        # Create a minimal request to a non-MM route via request factory
        request = rf.get("/admin/", HTTP_ACCEPT="text/html")

        response = HttpResponse("ok", content_type="text/html")

        def get_response(req):
            return response

        middleware = MMMiddleware(get_response)
        result = middleware(request)

        assert result.status_code == 200

    def test_bind_query_get(self, rf: RequestFactory):
        """Test GET with hex-encoded query param."""
        data = {"name": "Alice", "age": 30}
        raw = encode_from_value(data)

        request = rf.get(f"/users/?data={raw.hex()}")
        request.META["HTTP_ACCEPT"] = CONTENT_TYPE_METAMESSAGE

        # Process through middleware
        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        assert hasattr(request, "mm_query")
        assert request.mm_query["name"] == "Alice"
        assert request.mm_query["age"] == 30

    def test_decode_body_post(self, rf: RequestFactory):
        """Test POST with binary MetaMessage body."""
        data = {"name": "Bob", "age": 25}
        body = encode_from_value(data)

        request = rf.post(
            "/users/",
            data=body,
            content_type=CONTENT_TYPE_METAMESSAGE,
            HTTP_ACCEPT=CONTENT_TYPE_METAMESSAGE,
        )

        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        assert hasattr(request, "mm_body")
        assert request.mm_body["name"] == "Bob"
        assert request.mm_body["age"] == 25

    def test_no_data_query(self, rf: RequestFactory):
        """Test GET without data param."""
        request = rf.get("/users/")
        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        assert hasattr(request, "mm_query")
        assert request.mm_query == {}


# View decorator tests
class TestMMView:
    """Tests for mm_view decorator."""

    def test_get_hex_query(self, rf: RequestFactory):
        """Test GET with hex-encoded query param."""
        @mm_view()
        def list_users(request, req: TestUser):
            return TestUser(name=req.name, age=req.age)

        data = {"name": "Alice", "age": 30}
        raw = encode_from_value(data)

        request = rf.get(f"/users/?data={raw.hex()}")
        request.META["HTTP_ACCEPT"] = CONTENT_TYPE_METAMESSAGE

        # Process through middleware first
        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        response = list_users(request)

        assert response.status_code == 200
        assert response["Content-Type"] == CONTENT_TYPE_METAMESSAGE
        decoded = decode_to_value(response.content)
        assert decoded["name"] == "Alice"
        assert decoded["age"] == 30

    def test_post_binary_body(self, rf: RequestFactory):
        """Test POST with binary MetaMessage body."""
        @mm_view()
        def create_user(request, req: TestUser):
            return TestUser(name=req.name, age=req.age)

        data = {"name": "Bob", "age": 25}
        body = encode_from_value(data)

        request = rf.post(
            "/users/",
            data=body,
            content_type=CONTENT_TYPE_METAMESSAGE,
            HTTP_ACCEPT=CONTENT_TYPE_METAMESSAGE,
        )

        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        response = create_user(request)

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["name"] == "Bob"
        assert decoded["age"] == 25

    def test_path_param(self, rf: RequestFactory):
        """Test path parameter with GET request."""
        @mm_view()
        def get_user(request, user_id: int, req: TestUser):
            return {"id": user_id, "name": req.name, "age": req.age}

        data = {"name": "Charlie", "age": 35}
        raw = encode_from_value(data)

        request = rf.get(f"/users/42/?data={raw.hex()}")
        request.META["HTTP_ACCEPT"] = CONTENT_TYPE_METAMESSAGE

        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        # Pass user_id as URL kwarg
        response = get_user(request, user_id=42)

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["id"] == 42
        assert decoded["name"] == "Charlie"
        assert decoded["age"] == 35

    def test_put_binary_body(self, rf: RequestFactory):
        """Test PUT with binary MetaMessage body."""
        @mm_view()
        def update_user(request, user_id: int, req: TestUser):
            return {"id": user_id, "name": req.name, "age": req.age}

        data = {"name": "Updated", "age": 99}
        body = encode_from_value(data)

        request = rf.put(
            "/users/1/",
            data=body,
            content_type=CONTENT_TYPE_METAMESSAGE,
            HTTP_ACCEPT=CONTENT_TYPE_METAMESSAGE,
        )

        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        response = update_user(request, user_id=1)

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["id"] == 1
        assert decoded["name"] == "Updated"
        assert decoded["age"] == 99

    def test_delete_hex_query(self, rf: RequestFactory):
        """Test DELETE with hex-encoded query param."""
        @mm_view()
        def delete_user(request, user_id: int, req: TestUser):
            return {"id": user_id, "deleted": True}

        data = {"name": "ToDelete", "age": 50}
        raw = encode_from_value(data)

        request = rf.delete(f"/users/7/?data={raw.hex()}")
        request.META["HTTP_ACCEPT"] = CONTENT_TYPE_METAMESSAGE

        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        response = delete_user(request, user_id=7)

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["id"] == 7
        assert decoded["deleted"] is True

    def test_mm_view_http_response_passthrough(self, rf: RequestFactory):
        """Test that HttpResponse return values pass through unchanged."""
        @mm_view()
        def my_view(request):
            return HttpResponse("custom", content_type="text/plain")

        request = rf.get("/test/")
        response = my_view(request)

        assert response.status_code == 200
        assert response.content == b"custom"

    def test_no_mm_headers_passthrough(self, rf: RequestFactory):
        """Test that without MM headers, request passes through."""
        @mm_view()
        def hello(request):
            return {"msg": "hello"}

        request = rf.get("/hello/")
        mm_middleware = MMMiddleware(lambda req: HttpResponse("ok"))
        mm_middleware._process_request(request)

        response = hello(request)

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["msg"] == "hello"


# Response utility tests
class TestUtils:
    """Tests for utility functions."""

    def test_mm_respond(self):
        """Test mm_respond returns MetaMessage-encoded response."""
        data = {"message": "ok"}
        response = mm_respond(data)

        assert response["Content-Type"] == CONTENT_TYPE_METAMESSAGE
        decoded = decode_to_value(response.content)
        assert decoded["message"] == "ok"

    def test_mm_error(self):
        """Test mm_error returns error response."""
        from mm_django import mm_error

        response = mm_error("not found", 404)

        assert response.status_code == 404
        decoded = decode_to_value(response.content)
        assert decoded["error"] == "not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])