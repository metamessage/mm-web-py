"""Basic example demonstrating fastapi-mm usage."""

from typing import Optional

from fastapi import FastAPI
from metamessage import mm

from mm_fastapi import MMRouter


# Define models using @mm decorator
@mm(desc="User model")
class User:
    """User model."""
    name: str = mm(desc="User name")
    age: int = mm(desc="User age")
    email: Optional[str] = mm(desc="User email", nullable=True)


@mm(desc="User response")
class UserResponse:
    """User response model."""
    id: int = mm(desc="User ID")
    name: str = mm(desc="User name")
    age: int = mm(desc="User age")
    email: Optional[str] = mm(desc="User email", nullable=True)


@mm(desc="Generic API response")
class APIResponse:
    """Generic API response."""
    code: int = mm(desc="Response code")
    message: str = mm(desc="Response message")
    data: Optional[UserResponse] = mm(desc="Response data", nullable=True)


@mm(desc="Health check response")
class HealthResponse:
    """Health check response."""
    status: str = mm(desc="Health status")


# Create FastAPI app
app = FastAPI(
    title="MetaMessage API Example",
    description="Example API using MetaMessage protocol",
    version="1.0.0",
)

# Create MMRouter with app auto-registration
router = MMRouter(app)


@router.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@router.post("/users")
async def create_user(user: User) -> APIResponse:
    """Create a new user.

    Accepts MetaMessage binary format.
    req is automatically bound from request body.
    """
    return APIResponse(
        code=0,
        message="created",
        data=UserResponse(
            id=1,
            name=user.name,
            age=user.age,
            email=user.email,
        ),
    )


@router.get("/items/{item_id}")
async def get_item(item_id: int) -> dict:
    """Get an item by ID.

    Response format is determined by Accept header.
    """
    return {
        "id": item_id,
        "name": "Example Item",
        "price": 99.99,
    }


if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI server with MetaMessage support...")
    print("\nTest with curl:")
    print("\n# Health check:")
    print("curl http://localhost:8000/health")
    print("\n# Create user (MetaMessage binary):")
    print('curl -X POST -H "Content-Type: application/metamessage" \\')
    print('     --data-binary @user.mm http://localhost:8000/users')
    print("\n# Get item:")
    print("curl http://localhost:8000/items/1")

    uvicorn.run(app, host="0.0.0.0", port=8000)