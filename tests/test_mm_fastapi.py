"""Tests for fastapi-mm - MetaMessage protocol only."""

from dataclasses import dataclass
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from metamessage import decode_to_value, encode_from_value, mm

from mm_core.types import CONTENT_TYPE_METAMESSAGE
from mm_fastapi import (
    MMBody,
    MMMiddleware,
    MMRouter,
)
from mm_fastapi.utils import mm_respond


# Test models
@mm(desc="Test user model")
@dataclass
class TestUser:
    """Test user model."""
    name: str
    age: int
    email: Optional[str] = None


# Test fixtures
@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI()
    app.add_middleware(MMMiddleware)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# Middleware tests
class TestMiddleware:
    """Tests for MMMiddleware."""

    def test_skip_openapi_routes(self, app: FastAPI, client: TestClient) -> None:
        """Test that OpenAPI routes are skipped."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200


# Decorator tests
class TestDecorators:
    """Tests for route decorators."""
    
    def test_get_hex_query(self, app: FastAPI) -> None:
        """Test GET request with hex-encoded query param."""
        router = MMRouter(app)

        @router.get("/users")
        async def list_users(req: TestUser) -> TestUser:
            return TestUser(name=req.name, age=req.age)

        client = TestClient(app)
        data = {"name": "Alice", "age": 30}
        raw = encode_from_value(data)
        response = client.get(f"/users?data={raw.hex()}")

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["name"] == "Alice"
        assert decoded["age"] == 30

    def test_post_binary_body(self, app: FastAPI) -> None:
        """Test POST request with binary MetaMessage body."""
        router = MMRouter(app)

        @router.post("/users")
        async def create_user(req: TestUser) -> TestUser:
            return TestUser(name=req.name, age=req.age)

        client = TestClient(app)
        data = {"name": "Bob", "age": 25}
        body = encode_from_value(data)
        response = client.post(
            "/users",
            content=body,
            headers={"Content-Type": CONTENT_TYPE_METAMESSAGE, "Accept": CONTENT_TYPE_METAMESSAGE},
        )

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["name"] == "Bob"
        assert decoded["age"] == 25

    def test_path_param_with_query(self, app: FastAPI) -> None:
        """Test path parameter + hex query for GET."""
        router = MMRouter(app)

        @router.get("/users/{user_id}")
        async def get_user(user_id: int, req: TestUser) -> dict:
            return {"id": user_id, "name": req.name, "age": req.age}

        client = TestClient(app)
        data = {"name": "Charlie", "age": 35}
        raw = encode_from_value(data)
        response = client.get(f"/users/42?data={raw.hex()}")

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["id"] == 42
        assert decoded["name"] == "Charlie"
        assert decoded["age"] == 35

    def test_put_binary_body(self, app: FastAPI) -> None:
        """Test PUT request with binary MetaMessage body."""
        router = MMRouter(app)

        @router.put("/users/{user_id}")
        async def update_user(user_id: int, req: TestUser) -> dict:
            return {"id": user_id, "name": req.name, "age": req.age}

        client = TestClient(app)
        data = {"name": "Updated", "age": 99}
        body = encode_from_value(data)
        response = client.put(
            f"/users/1",
            content=body,
            headers={"Content-Type": CONTENT_TYPE_METAMESSAGE, "Accept": CONTENT_TYPE_METAMESSAGE},
        )

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["id"] == 1
        assert decoded["name"] == "Updated"
        assert decoded["age"] == 99

    def test_delete_hex_query(self, app: FastAPI) -> None:
        """Test DELETE request with hex-encoded query param."""
        router = MMRouter(app)

        @router.delete("/users/{user_id}")
        async def delete_user(user_id: int, req: TestUser) -> dict:
            return {"id": user_id, "deleted": True}

        client = TestClient(app)
        data = {"name": "ToDelete", "age": 50}
        raw = encode_from_value(data)
        response = client.delete(f"/users/7?data={raw.hex()}")

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["id"] == 7
        assert decoded["deleted"] is True


# Dependency tests
class TestDependencies:
    """Tests for dependency injection with MetaMessage."""

    def test_mm_body_dependency(self, app: FastAPI) -> None:
        """Test MMBody dependency with binary body."""
        router = MMRouter(app)

        @router.post("/users")
        async def create_user(user: TestUser = MMBody(TestUser)) -> dict:
            return {"id": 1, "name": user.name, "age": user.age}

        client = TestClient(app)
        data = {"name": "Bob", "age": 25}
        body = encode_from_value(data)
        response = client.post(
            "/users",
            content=body,
            headers={"Content-Type": CONTENT_TYPE_METAMESSAGE, "Accept": CONTENT_TYPE_METAMESSAGE},
        )

        assert response.status_code == 200
        decoded = decode_to_value(response.content)
        assert decoded["name"] == "Bob"
        assert decoded["age"] == 25


# Response test
class TestUtils:
    """Tests for utility functions."""

    def test_mm_respond_binary(self) -> None:
        """Test mm_respond returns MetaMessage-encoded response."""
        data = {"message": "ok"}
        response = mm_respond(data)

        assert response.media_type == CONTENT_TYPE_METAMESSAGE
        decoded = decode_to_value(response.body)
        assert decoded["message"] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])