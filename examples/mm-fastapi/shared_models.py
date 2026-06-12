"""Shared models for fastapi-mm examples.

These models are shared between server and client examples,
so request/response structures are defined once and reused.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from metamessage import mm


# ============ CRUD Models ============


@mm(desc="User model")
@dataclass
class User:
    """User model."""
    id: int = mm(desc="User ID")
    name: str = mm(desc="User name")
    email: str = mm(desc="User email")
    age: int = mm(desc="User age")
    is_active: bool = mm(desc="User is active")


@mm(desc="Create user request")
@dataclass
class CreateUserRequest:
    """Create user request."""
    name: str = mm(desc="User name")
    email: str = mm(desc="User email")
    age: int = mm(desc="User age")


@mm(desc="Update user request - all fields optional")
@dataclass
class UpdateUserRequest:
    """Update user request - all fields optional."""
    name: Optional[str] = mm(desc="User name", nullable=True)
    email: Optional[str] = mm(desc="User email", nullable=True)
    age: Optional[int] = mm(desc="User age", nullable=True)
    is_active: Optional[bool] = mm(desc="User is active", nullable=True)


@mm(desc="User list request parameters")
@dataclass
class ListUsersRequest:
    """GET request parameters for listing users."""
    page: int = mm(desc="Page number", nullable=True)
    page_size: int = mm(desc="Items per page", nullable=True)
    name: str = mm(desc="Filter by name", nullable=True)

    def validate(self) -> Optional[str]:
        """Validate request parameters."""
        if self.page is not None and self.page < 1:
            return "Page must be >= 1"
        if self.page_size is not None and self.page_size < 1:
            return "Page size must be >= 1"
        if self.page_size is not None and self.page_size > 100:
            return "Page size must be <= 100"
        return None


@mm(desc="Get user request parameters")
@dataclass
class GetUserRequest:
    """GET request parameters for fetching a user."""
    include_inactive: bool = mm(desc="Include inactive users", nullable=True)


@mm(desc="Delete user request parameters")
@dataclass
class DeleteUserRequest:
    """DELETE request parameters for deleting a user."""
    force: bool = mm(desc="Force delete without confirmation", nullable=True)


@mm(desc="User list response")
@dataclass
class ListUsersResponse:
    """User list response."""
    total: int = mm(desc="Total number of users")
    users: List[User] = mm(desc="List of users")


@mm(desc="Generic API response")
@dataclass
class APIResponse:
    """Generic API response."""
    code: int = mm(desc="Response code")
    message: str = mm(desc="Response message")
    data: Optional[User] = mm(desc="Response data", nullable=True)


@mm(desc="Health check response")
@dataclass
class HealthResponse:
    """Health check response."""
    status: str = mm(desc="Health status")


@mm(desc="Error response")
@dataclass
class ErrorResponse:
    """Error response."""
    error: str = mm(desc="Error message")