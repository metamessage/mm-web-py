"""Comprehensive test for the MM client-server integration."""
import sys
from mm_core import MMClient, MMClientError
from metamessage import value_to_jsonc
from shared_models import (
    APIResponse,
    CreateUserRequest,
    ListUsersResponse,
    UpdateUserRequest,
    DeleteUserRequest,
)


def run_all_tests(base_url: str = "http://localhost:8000"):
    client = MMClient(base_url, debug=True)

    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name} {detail}")
            failed += 1

    print("\n" + "=" * 60)
    print("  MetaMessage Client Integration Tests")
    print("=" * 60)

    # 1. Health check
    print("\n--- [GET] /health ---")
    status = client.health()
    check("health ok", status == "ok", f"got {status}")

    # 2. List users
    print("\n--- [GET] /api/v1/users ---")
    resp = client.get("/api/v1/users", target_type=ListUsersResponse)
    check("status 200", resp.status_code == 200)
    if isinstance(resp.data, ListUsersResponse):
        check("has total", resp.data.total >= 0)
        check("has users", len(resp.data.users) > 0)
        check("user has name", resp.data.users[0].name is not None)
    else:
        check("correct type", False, f"got {type(resp.data).__name__}")

    # 3. Get single user
    print("\n--- [GET] /api/v1/user/1 ---")
    resp = client.get("/api/v1/user/1", target_type=APIResponse)
    check("status 200", resp.status_code == 200)
    if isinstance(resp.data, APIResponse):
        check("message success", resp.data.message == "success")
        check("has user data", resp.data.data is not None)
        if resp.data.data:
            check("user id=1", resp.data.data.id == 1)
    else:
        check("correct type", False, f"got {type(resp.data).__name__}")

    # 4. Create user
    print("\n--- [POST] /api/v1/user/create ---")
    create_req = CreateUserRequest(name="David", email="david@example.com", age=28)
    resp = client.post("/api/v1/user/create", body=create_req, target_type=APIResponse)
    check("status 200/201", resp.status_code in (200, 201))
    if isinstance(resp.data, APIResponse):
        check("message user created", resp.data.message == "user created")
        check("new user has id", resp.data.data is not None)
    else:
        check("correct type", False, f"got {type(resp.data).__name__}")

    # 5. Update user
    print("\n--- [PUT] /api/v1/user/update/1 ---")
    update_req = UpdateUserRequest(name="Alice Updated")
    resp = client.put("/api/v1/user/update/1", body=update_req, target_type=APIResponse)
    check("status 200", resp.status_code == 200)
    if isinstance(resp.data, APIResponse):
        check("message user updated", resp.data.message == "user updated")
        if resp.data.data:
            check("name updated", resp.data.data.name == "Alice Updated")
    else:
        check("correct type", False, f"got {type(resp.data).__name__}")

    # 6. Delete user (with force)
    print("\n--- [DELETE] /api/v1/user/delete/3 ---")
    resp = client.delete("/api/v1/user/delete/3")
    check("status 200/error", resp.status_code == 200)
    if isinstance(resp.data, dict):
        if "error" in resp.data:
            check("delete with force", True)
            del_req = DeleteUserRequest(force=True)
            resp2 = client.delete("/api/v1/user/delete/3", body=del_req, target_type=APIResponse)
            check("force delete status", resp2.status_code == 200)
            if isinstance(resp2.data, APIResponse):
                check("force delete message", resp2.data.message == "user deleted")
            else:
                check("correct type", False, f"got {type(resp2.data).__name__}")
        else:
            check("delete result", True)
    else:
        check("correct type", False, f"got {type(resp.data).__name__}")

    client.close()

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)