"""Basic example for flask_mm."""

from dataclasses import dataclass
from flask import Flask
from metamessage import mm
from mm_flask import MMFlask, MMMiddleware


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


app = Flask(__name__)
MMMiddleware(app)
mm = MMFlask(app)


@mm.post("/users")
def create_user(req: CreateUserRequest) -> CreateUserResponse:
    """Create a new user."""
    # User data is automatically bound from MetaMessage binary body
    return CreateUserResponse(id=1, name=req.name, age=req.age)


@mm.get("/users/<int:user_id>")
def get_user(user_id: int, req: CreateUserRequest) -> dict:
    """Get user with hex-encoded query params."""
    return {
        "id": user_id,
        "name": req.name,
        "age": req.age,
    }


@mm.delete("/users/<int:user_id>")
def delete_user(user_id: int) -> dict:
    """Delete a user."""
    return {
        "id": user_id,
        "deleted": True,
    }


if __name__ == "__main__":
    app.run(debug=True)
