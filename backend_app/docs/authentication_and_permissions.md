# Integrated Authentication & Permissions in Sonic Brief

## Overview
Sonic Brief uses integrated authentication and a granular permission system to secure all backend APIs. Authentication is based on JWT tokens, and permissions are enforced at both the route and business logic levels using FastAPI dependencies and utility functions.

---

## Authentication Flow

1. **User Login**
   - Users authenticate via `/api/auth/login` (or SSO endpoints).
   - On success, a JWT access token is issued, containing the user's email as the `sub` claim.

2. **JWT Token Usage**
   - The frontend includes the JWT in the `Authorization: Bearer <token>` header for all API requests.
   - The backend extracts and validates the token for each request.

3. **User Extraction**
   - The `get_current_user` dependency (in `auth.py`) decodes the JWT, fetches the user from Cosmos DB, and attaches the user object to the request context.

---

## FastAPI Security Integration

- Uses `OAuth2PasswordBearer` for token extraction.
- JWT secret and algorithm are loaded from environment/config.
- Invalid or expired tokens result in a 401 error.

**Example:**
```python
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    # Decode JWT, fetch user from DB, raise 401 if invalid
    ...
```

---

## Permission Enforcement

- **Route-level**: Use dependencies like `require_admin`, `require_editor`, or custom checks to restrict access.
- **Business logic**: Use `permission_service.has_permission_level()` and `get_user_capabilities()` for fine-grained checks.

**Example:**
```python
@router.get("/admin/endpoint", dependencies=[Depends(require_admin)])
async def admin_endpoint():
    ...
```

---

## Permission Caching

- User permissions are cached in-memory (see `permission_cache.py`) for performance.
- Cache is used before querying the database.

---

## Extending Authentication

- To add new authentication providers (e.g., SSO), implement a new login endpoint that issues a compatible JWT.
- To add new permission levels, update `PermissionLevel` and related utilities.

---

## Best Practices

- Always use `Depends(get_current_user)` or a stricter dependency in all protected endpoints.
- Never trust user input for permissions—always fetch from the DB or cache.
- Document required permissions for each endpoint.

---

## References
- [`app/routers/auth.py`](../app/routers/auth.py)
- [`app/services/permissions.py`](../app/services/permissions.py)
- [`app/middleware/permission_middleware.py`](../app/middleware/permission_middleware.py)
- [`app/utils/permission_cache.py`](../app/utils/permission_cache.py)

_Last updated: June 2025_
