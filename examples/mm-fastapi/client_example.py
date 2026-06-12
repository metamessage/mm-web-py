"""Standalone client example for fastapi-mm.

Demonstrates using MMClient SDK to interact with the MetaMessage CRUD API.
Uses shared models from shared_models.py - same structures as the server.

Prerequisites:
    1. Start the server:  python server_example.py
    2. Run the client:     python client_example.py
"""

import sys

from mm_core import MMClient

from shared_models import (
    APIResponse,
    CreateUserRequest,
    ListUsersResponse,
    UpdateUserRequest,
)


# ============ Main ============


def run_tests(base_url: str = "http://localhost:8000"):
    client = MMClient(base_url)

    print("\n" + "=" * 60)
    print("  MetaMessage Client Test")
    print("=" * 60)

    # Health check
    print("\n  [GET] /health")
    status = client.health()
    print(f"  Status: {status}")

    # List users (GET - query params encoded)
    print("\n  [GET] /api/v1/users")
    resp = client.get("/api/v1/users", target_type=ListUsersResponse)
    if resp.status_code == 200 and isinstance(resp.data, ListUsersResponse):
        print(f"  Total: {resp.data.total}")
        for u in resp.data.users:
            print(f"    - ID: {u.id}, Name: {u.name}, "
                  f"Email: {u.email}, Age: {u.age}")
    else:
        print(f"  Error: status={resp.status_code}")

    # Get single user (GET - query params encoded)
    print("\n  [GET] /api/v1/user/1")
    resp = client.get("/api/v1/user/1", target_type=APIResponse)
    if resp.status_code == 200 and isinstance(resp.data, APIResponse):
        print(f"  Message: {resp.data.message}")
        user = resp.data.data
        if user:
            print(f"  User: ID={user.id}, Name={user.name}, "
                  f"Email={user.email}, Age={user.age}")
    else:
        print(f"  Error: status={resp.status_code}")

    # Create user (POST - body encoded)
    print("\n  [POST] /api/v1/user/create")
    create_req = CreateUserRequest(name="David", email="david@example.com", age=28)
    resp = client.post("/api/v1/user/create", body=create_req, target_type=APIResponse)
    if resp.status_code == 201 and isinstance(resp.data, APIResponse):
        print(f"  Message: {resp.data.message}")
        new_user = resp.data.data
        if new_user:
            print(f"  New User: ID={new_user.id}, Name={new_user.name}, "
                  f"Email={new_user.email}, Age={new_user.age}")
    else:
        print(f"  Error: status={resp.status_code}, data={resp.data}")

    # Update user (PUT - body encoded)
    print("\n  [PUT] /api/v1/user/update/1")
    update_req = UpdateUserRequest(name="Alice Updated")
    resp = client.put("/api/v1/user/update/1", body=update_req, target_type=APIResponse)
    if resp.status_code == 200 and isinstance(resp.data, APIResponse):
        print(f"  Message: {resp.data.message}")
        updated = resp.data.data
        if updated:
            print(f"  Updated: ID={updated.id}, Name={updated.name}")
    else:
        print(f"  Error: status={resp.status_code}")

    # Delete user (DELETE - query params encoded)
    print("\n  [DELETE] /api/v1/user/delete/3")
    resp = client.delete("/api/v1/user/delete/3", target_type=APIResponse)
    if isinstance(resp.data, APIResponse):
        print(f"  Message: {resp.data.message}")
    else:
        print(resp.data)

    client.close()

    print("\n" + "=" * 60)
    print("  All tests completed!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    run_tests(base_url)