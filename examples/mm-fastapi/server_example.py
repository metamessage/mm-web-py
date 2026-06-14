"""Complete CRUD server example for fastapi-mm.

Based on mm-gin examples/main.go architecture.
Run: python server_example.py
Then test with: python client_example.py

Design patterns from mm-web-go:
- POST/PUT requests use MetaMessage body encoding
- GET requests use URL query parameters encoding
"""

from typing import List, Optional, Union

from fastapi import FastAPI

from mm_fastapi import MMRouter

from shared_models import (
    APIResponse,
    CreateUserRequest,
    DeleteUserRequest,
    ErrorResponse,
    GetUserRequest,
    HealthResponse,
    ListUsersRequest,
    ListUsersResponse,
    UpdateUserRequest,
    User,
)


# ============ In-Memory Storage ============

users_db: List[User] = [
    User(id=1, name="Alice", email="alice@example.com", age=25, is_active=True),
    User(id=2, name="Bob", email="bob@example.com", age=30, is_active=True),
    User(id=3, name="Charlie", email="charlie@example.com", age=35, is_active=False),
]


def find_user_index(user_id: int) -> Optional[int]:
    for i, u in enumerate(users_db):
        if u.id == user_id:
            return i
    return None


# ============ Create FastAPI App ============

app = FastAPI(
    title="MetaMessage CRUD API",
    description="Complete CRUD API example using MetaMessage protocol",
    version="1.0.0",
)

# ============ API Routes with MMRouter ============

router = MMRouter(app)


@router.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.get("/api/v1/users")
async def list_users(req: ListUsersRequest) -> ListUsersResponse:
    """List users with optional filtering and pagination.
    
    Similar to mm-web-go: req is automatically bound from URL query.
    Request object is available as 'r' for accessing raw request data.
    """

    print(f'req {req}')
    filtered_users = users_db
    page = req.page or 1
    page_size = req.page_size or 10
    name = req.name
    
    if name:
        filtered_users = [u for u in filtered_users if name.lower() in u.name.lower()]
    
    total = len(filtered_users)
    
    if page and page_size:
        start = (page - 1) * page_size
        end = start + page_size
        filtered_users = filtered_users[start:end]
    
    return ListUsersResponse(total=total, users=filtered_users)


@router.get("/api/v1/user/{user_id}")
async def get_user(user_id: int, req: GetUserRequest) -> Union[APIResponse, ErrorResponse]:
    """Get a single user by ID.
    
    Similar to mm-web-go: req is automatically bound from URL query.
    Request object is available as 'r' for accessing raw request data.
    """
    include_inactive = req.include_inactive if req.include_inactive is not None else True
    
    idx = find_user_index(user_id)
    if idx is None:
        return ErrorResponse(error="user not found")

    user = users_db[idx]
    
    if not user.is_active and not include_inactive:
        return ErrorResponse(error="user is inactive")

    return APIResponse(code=0, message="success", data=user)


@router.post("/api/v1/user/create")
async def create_user(req: CreateUserRequest) -> APIResponse:
    """Create a new user."""
    print(f'CreateUserRequest {req}')
    new_id = max((u.id for u in users_db), default=0) + 1
    new_user = User(
        id=new_id,
        name=req.name,
        email=req.email,
        age=req.age,
        is_active=True,
    )
    users_db.append(new_user)

    return APIResponse(code=0, message="user created", data=new_user)


@router.put("/api/v1/user/update/{user_id}")
async def update_user(user_id: int, req: UpdateUserRequest) -> Union[APIResponse, ErrorResponse]:
    """Update a user. Only updates provided fields.
    
    Similar to mm-web-go: req is automatically bound from request body.
    Request object is available as 'r' for accessing raw request data.
    """
    idx = find_user_index(user_id)
    if idx is None:
        return ErrorResponse(error="user not found")

    existing = users_db[idx]

    if req.name is not None:
        existing.name = req.name
    if req.email is not None:
        existing.email = req.email
    if req.age is not None:
        existing.age = req.age
    if req.is_active is not None:
        existing.is_active = req.is_active

    users_db[idx] = existing

    return APIResponse(code=0, message="user updated", data=existing)


@router.patch("/api/v1/user/patch/{user_id}")
async def patch_user(user_id: int, req: UpdateUserRequest) -> Union[APIResponse, ErrorResponse]:
    """Partial update a user (PATCH). Only updates specified fields.
    
    Similar to mm-web-go: req is automatically bound from request body.
    Request object is available as 'r' for accessing raw request data.
    """
    idx = find_user_index(user_id)
    if idx is None:
        return ErrorResponse(error="user not found")

    existing = users_db[idx]
    updated_fields = []

    if req.name is not None:
        existing.name = req.name
        updated_fields.append("name")
    if req.email is not None:
        existing.email = req.email
        updated_fields.append("email")
    if req.age is not None:
        existing.age = req.age
        updated_fields.append("age")
    if req.is_active is not None:
        existing.is_active = req.is_active
        updated_fields.append("is_active")

    users_db[idx] = existing

    return APIResponse(code=0, message=f"updated fields: {', '.join(updated_fields)}", data=existing)


@router.delete("/api/v1/user/delete/{user_id}")
async def delete_user(user_id: int, req: DeleteUserRequest) -> Union[APIResponse, ErrorResponse]:
    """Delete a user.
    
    Similar to mm-web-go: req is automatically bound from URL query.
    Request object is available as 'r' for accessing raw request data.
    """
    idx = find_user_index(user_id)
    if idx is None:
        return ErrorResponse(error="user not found")

    force = req.force if req.force is not None else False

    user = users_db[idx]
    
    if not force and not user.is_active:
        return ErrorResponse(error="user is inactive, use force=true to delete")

    users_db.pop(idx)

    return APIResponse(code=0, message="user deleted", data=None)


# ============ Main ============

if __name__ == "__main__":
    import uvicorn

    print("=" * 100)
    print("  MetaMessage CRUD API Server")
    print("=" * 100)
    print()
    print("  Design Pattern:")
    print("    - POST/PUT/PATCH requests: MetaMessage body encoding")
    print("    - GET/DELETE requests: URL query parameters")
    print("    - Routes return model instances directly")
    print("    - Middleware handles automatic MetaMessage encoding")
    print()
    print("  Endpoints:")
    print("    GET    /health                                    - Health check")
    print("    GET    /api/v1/users?data=<hex>                   - List users with pagination/filter")
    print("    GET    /api/v1/user/{id}?data=<hex>               - Get user")
    print("    POST   /api/v1/user/create                        - Create user (MetaMessage body)")
    print("    PUT    /api/v1/user/update/{id}                   - Update user (MetaMessage body)")
    print("    PATCH  /api/v1/user/patch/{id}                    - Partial update (MetaMessage body)")
    print("    DELETE /api/v1/user/delete/{id}?data=<hex>        - Delete user")
    print()
    print("  Route Pattern:")
    print("    @mm_post('/user')")
    print("    async def create_user(r: Request, req: CreateUserRequest) -> APIResponse:")
    print("        return APIResponse(code=0, message='ok', data=req)")
    print()
    print("  Test manually:")
    print("    curl http://localhost:8000/health")
    print("    curl -H 'Accept: application/metamessage' 'http://localhost:8000/api/v1/users?data=<hex>'")
    print("    curl -H 'Accept: application/metamessage' 'http://localhost:8000/api/v1/user/1?data=<hex>'")
    print()
    print("  Or use the client:")
    print("    python client_example.py")
    print()
    print("=" * 100)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)