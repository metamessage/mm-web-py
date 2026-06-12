"""Tests for mm_flask - MetaMessage Flask extension."""

from dataclasses import dataclass
from typing import Optional

import pytest
from flask import Flask
from metamessage import decode_to_value, encode_from_value, mm

from mm_core.types import CONTENT_TYPE_METAMESSAGE
from mm_flask import MMFlask, MMMiddleware, mm_respond


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
def app() -> Flask:
    """Create test Flask app."""
    app = Flask(__name__)
    MMMiddleware(app)
    return app


@pytest.fixture
def client(app: Flask):
    """Create test client."""
    return app.test_client()


# Middleware tests
class TestMiddleware:
    """Tests for MMMiddleware."""

    def test_skip_openapi_routes(self, client) -> None:
        """Test that skip routes pass through."""
        response = client.get("/openapi.json")
        assert response.status_code == 404  # Flask has no OpenAPI by default


# Decorator tests
class TestMMFlask:
    """Tests for MMFlask decorators."""

    def test_get_hex_query(self, app: Flask) -> None:
        """Test GET request with hex-encoded query param."""
        mm = MMFlask(app)

        @mm.get("/users")
        def list_users(req: TestUser) -> TestUser:
            return TestUser(name=req.name, age=req.age)

        client = app.test_client()
        data = {"name": "Alice", "age": 30}
        raw = encode_from_value(data)
        response = client.get(f"/users?data={raw.hex()}")

        assert response.status_code == 200
        decoded = decode_to_value(response.data)
        assert decoded["name"] == "Alice"
        assert decoded["age"] == 30

    def test_post_binary_body(self, app: Flask) -> None:
        """Test POST request with binary MetaMessage body."""
        mm = MMFlask(app)

        @mm.post("/users")
        def create_user(req: TestUser) -> TestUser:
            return TestUser(name=req.name, age=req.age)

        client = app.test_client()
        data = {"name": "Bob", "age": 25}
        body = encode_from_value(data)
        response = client.post(
            "/users",
            data=body,
            content_type=CONTENT_TYPE_METAMESSAGE,
            headers={"Accept": CONTENT_TYPE_METAMESSAGE},
        )

        assert response.status_code == 200
        decoded = decode_to_value(response.data)
        assert decoded["name"] == "Bob"
        assert decoded["age"] == 25

    def test_path_param(self, app: Flask) -> None:
        """Test path parameter with GET request."""
        mm = MMFlask(app)

        @mm.get("/users/<int:user_id>")
        def get_user(user_id: int, req: TestUser) -> dict:
            return {"id": user_id, "name": req.name, "age": req.age}

        client = app.test_client()
        data = {"name": "Charlie", "age": 35}
        raw = encode_from_value(data)
        response = client.get(f"/users/42?data={raw.hex()}")

        assert response.status_code == 200
        decoded = decode_to_value(response.data)
        assert decoded["id"] == 42
        assert decoded["name"] == "Charlie"
        assert decoded["age"] == 35

    def test_put_binary_body(self, app: Flask) -> None:
        """Test PUT request with binary MetaMessage body."""
        mm = MMFlask(app)

        @mm.put("/users/<int:user_id>")
        def update_user(user_id: int, req: TestUser) -> dict:
            return {"id": user_id, "name": req.name, "age": req.age}

        client = app.test_client()
        data = {"name": "Updated", "age": 99}
        body = encode_from_value(data)
        response = client.put(
            "/users/1",
            data=body,
            content_type=CONTENT_TYPE_METAMESSAGE,
            headers={"Accept": CONTENT_TYPE_METAMESSAGE},
        )

        assert response.status_code == 200
        decoded = decode_to_value(response.data)
        assert decoded["id"] == 1
        assert decoded["name"] == "Updated"
        assert decoded["age"] == 99

    def test_delete_hex_query(self, app: Flask) -> None:
        """Test DELETE request with hex-encoded query param."""
        mm = MMFlask(app)

        @mm.delete("/users/<int:user_id>")
        def delete_user(user_id: int, req: TestUser) -> dict:
            return {"id": user_id, "deleted": True}

        client = app.test_client()
        data = {"name": "ToDelete", "age": 50}
        raw = encode_from_value(data)
        response = client.delete(f"/users/7?data={raw.hex()}")

        assert response.status_code == 200
        decoded = decode_to_value(response.data)
        assert decoded["id"] == 7
        assert decoded["deleted"] is True

    def test_mm_respond(self) -> None:
        """Test mm_respond returns MetaMessage-encoded response."""
        data = {"message": "ok"}
        response = mm_respond(data)

        assert response.content_type == CONTENT_TYPE_METAMESSAGE
        decoded = decode_to_value(response.data)
        assert decoded["message"] == "ok"

    def test_no_mm_headers_passthrough(self, app: Flask) -> None:
        """Test that without MM headers, request passes through as is."""
        mm = MMFlask(app)

        @mm.get("/hello")
        def hello() -> dict:
            return {"msg": "hello"}

        client = app.test_client()
        response = client.get("/hello")

        assert response.status_code == 200
        # Without mm headers, the response is encoded but content type might not be set
        decoded = decode_to_value(response.data)
        assert decoded["msg"] == "hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])