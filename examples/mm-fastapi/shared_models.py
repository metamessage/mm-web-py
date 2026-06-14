"""Shared models for fastapi-mm examples.

These models are shared between server and client examples,
so request/response structures are defined once and reused.
"""

from __future__ import annotations

from typing import List, Optional

from metamessage import mm


# ============ CRUD Models ============


@mm(desc="User model")
class User:
    """User model."""
    id: int = mm(desc="User ID")
    name: str = mm(desc="User name")
    email: str = mm(desc="User email")
    age: int = mm(desc="User age")
    is_active: bool = mm(desc="User is active")


@mm(desc="Create user request")
class CreateUserRequest:
    """Create user request."""
    name: str = mm(desc="User name")
    email: str = mm(desc="User email")
    age: int = mm(desc="User age")


@mm(desc="Update user request - all fields optional")
class UpdateUserRequest:
    """Update user request - all fields optional."""
    name: Optional[str] = mm(desc="User name")
    email: Optional[str] = mm(desc="User email")
    age: Optional[int] = mm(desc="User age")
    is_active: Optional[bool] = mm(desc="User is active")


@mm(desc="User list request parameters")
class ListUsersRequest:
    """GET request parameters for listing users."""
    page: Optional[int] = mm(desc="Page number", min=1)
    page_size: Optional[int] = mm(desc="Items per page", min=1)
    name: Optional[str] = mm(desc="Filter by name",max=100)

@mm(desc="Get user request parameters")
class GetUserRequest:
    """GET request parameters for fetching a user."""
    include_inactive: Optional[bool] = mm(desc="Include inactive users")


@mm(desc="Delete user request parameters")
class DeleteUserRequest:
    """DELETE request parameters for deleting a user."""
    force: Optional[bool] = mm(desc="Force delete without confirmation")


@mm(desc="User list response")
class ListUsersResponse:
    """User list response."""
    total: int = mm(desc="Total number of users")
    users: List[User] = mm(desc="List of users")


@mm(desc="Generic API response")
class APIResponse:
    """Generic API response."""
    code: int = mm(desc="Response code")
    message: str = mm(desc="Response message")
    data: Optional[User] = mm(desc="Response data")


@mm(desc="Health check response")
class HealthResponse:
    """Health check response."""
    status: str = mm(desc="Health status")


@mm(desc="Error response")
class ErrorResponse:
    """Error response."""
    error: str = mm(desc="Error message")