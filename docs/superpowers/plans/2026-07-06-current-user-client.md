# Current User Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add `GET /api/current-user`, which uses the server-side session token to obtain and safely expose the current third-party user.

**Architecture:** The FastAPI route owns Cookie and HTTP response behavior. A reusable client validates remote HTTP and business responses, while a user-specific client maps the remote object into an explicit allowlist model. The access token crosses only the route-to-client boundary and is never included in the browser response or logs.

**Tech Stack:** Python 3.11, FastAPI, pydantic-settings, HTTPX, pytest

---

## File map

- Create `backend/app/clients/__init__.py`: declare the remote-client package.
- Create `backend/app/clients/base.py`: shared authenticated GET request and remote error types.
- Create `backend/app/clients/user.py`: current-user model and remote field allowlist mapping.
- Create `backend/app/api/current_user.py`: Cookie-protected BFF endpoint and error translation.
- Create `backend/tests/test_user_client.py`: remote request, response validation, and allowlist tests.
- Create `backend/tests/test_current_user.py`: route authentication, status mapping, and Cookie cleanup tests.
- Modify `backend/app/api/auth.py`: expose the shared session-token dependency and neutralize provider-specific comments/logs.
- Modify `backend/app/core/config.py`: add the user-info URL.
- Modify `backend/app/main.py`: register the current-user router.
- Modify `backend/tests/test_auth.py`: use provider-neutral fixtures and test names.
- Modify `backend/tests/test_config.py`: cover the user-info setting.
- Modify `.env.example` and `docker-compose.yml`: configure and pass the user-info URL.
- Modify `README.md`, `backend/README.md`, `docs/架构标准.md`, and OAuth design/plan records: document the BFF client boundary with provider-neutral terminology.

### Task 1: Add user-info configuration

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/tests/test_config.py`
- Modify: `.env.example`
- Modify: `docker-compose.yml`

- [x] **Step 1: Add the failing configuration assertions**

Add `OAUTH2_USERINFO_URL` to the environment test and assert both its empty default and environment override:

```python
assert settings.oauth2_userinfo_url == ""

monkeypatch.setenv(
    "OAUTH2_USERINFO_URL",
    "https://auth.example/oauth2/userinfo",
)
assert settings.oauth2_userinfo_url == "https://auth.example/oauth2/userinfo"
```

- [x] **Step 2: Run the configuration test and verify failure**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_config.py -q)
```

Expected: FAIL because `Settings.oauth2_userinfo_url` does not exist.

- [x] **Step 3: Add the typed setting and deployment wiring**

Add this field beside the other server-side OAuth2 endpoints:

```python
oauth2_userinfo_url: str = ""
```

Add this example:

```dotenv
OAUTH2_USERINFO_URL=http://127.0.0.1:5555/oauth2/userinfo
```

Pass it to the application container:

```yaml
OAUTH2_USERINFO_URL: "${OAUTH2_USERINFO_URL:-}"
```

- [x] **Step 4: Run the configuration test**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_config.py -q)
```

Expected: PASS.

### Task 2: Build the reusable remote client

**Files:**
- Create: `backend/app/clients/__init__.py`
- Create: `backend/app/clients/base.py`
- Create: `backend/app/clients/user.py`
- Create: `backend/tests/test_user_client.py`

- [x] **Step 1: Write failing client tests**

Use `httpx.MockTransport` to verify that `UserClient.get_current_user("private-token")` sends:

```python
assert request.method == "GET"
assert request.url == httpx.URL("https://auth.example/oauth2/userinfo")
assert request.headers["authorization"] == "Bearer private-token"
```

Return a successful `ResultBody` containing allowed fields plus `token`, `thirdToken`,
`refreshToken`, and an unknown field. Assert the result is exactly:

```python
CurrentUser(
    user_id=1,
    username="admin",
    real_name="管理员",
    dept_id=10,
    dept_name="平台部门",
    company_id=20,
    roles=["admin"],
    permissions=["system:read"],
    menu_permissions=["dashboard"],
    role_permissions=["ROLE_ADMIN"],
)
```

Add separate cases for HTTP 401/403, HTTP 500, transport failure, invalid JSON, business failure,
and a non-object `result`.

- [x] **Step 2: Run client tests and verify failure**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_user_client.py -q)
```

Expected: FAIL because `app.clients.user` does not exist.

- [x] **Step 3: Implement shared response validation**

Define these stable client exceptions:

```python
class RemoteClientError(Exception):
    """Base class for failures safe to translate at the local API boundary."""


class RemoteAuthenticationError(RemoteClientError):
    """The remote service rejected the current access token."""


class RemoteServiceError(RemoteClientError):
    """The remote service could not provide a valid business response."""
```

Implement `RemoteClient.get_result()` with `httpx.AsyncClient.get`, an explicit
`httpx.Timeout(10.0, connect=5.0)`, `Authorization: Bearer <token>`, 401/403 classification,
non-success classification, JSON parsing, and the exact business contract:

```python
body.get("code") == 200
body.get("success") is True
isinstance(body.get("result"), dict)
```

Logs may contain only the exception class or HTTP status.

- [x] **Step 4: Implement current-user allowlist mapping**

Define `CurrentUser` with these fields:

```python
user_id: int | None = None
username: str | None = None
real_name: str | None = None
dept_id: int | None = None
dept_name: str | None = None
company_id: int | None = None
roles: list[str] = Field(default_factory=list)
permissions: list[str] = Field(default_factory=list)
menu_permissions: list[str] = Field(default_factory=list)
role_permissions: list[str] = Field(default_factory=list)
```

`UserClient` maps only `userId`, `username`, `realName`, `deptId`, `deptName`, `companyId`,
`roles`, `permissions`, `menuPermission`, and `rolePermission`. It does not copy the remote
dictionary or expose unknown fields.

- [x] **Step 5: Run client tests**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_user_client.py -q)
```

Expected: PASS.

### Task 3: Add the current-user API

**Files:**
- Modify: `backend/app/api/auth.py`
- Create: `backend/app/api/current_user.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_current_user.py`

- [x] **Step 1: Write failing route tests**

Build an isolated FastAPI app and override the user-client dependency. Cover:

```python
assert missing_cookie.status_code == 401
assert missing_cookie.json() == {"detail": "未登录"}

assert success.status_code == 200
assert success.json()["username"] == "admin"
assert "token" not in success.text.lower()
```

Also assert:

- an empty Cookie does not call the remote client;
- missing `OAUTH2_USERINFO_URL` returns 503 without a remote call;
- `RemoteAuthenticationError` returns 401 and expires `genstack_session`;
- `RemoteServiceError` returns 502 without exposing exception content.

- [x] **Step 2: Run route tests and verify failure**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_current_user.py -q)
```

Expected: FAIL because `app.api.current_user` does not exist.

- [x] **Step 3: Add the shared session dependency**

Add this public dependency to `auth.py`:

```python
def require_session_token(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> str:
    """Return the non-empty server-side session token or reject the request."""

    if not session_token or not session_token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return session_token.strip()
```

- [x] **Step 4: Implement and register the route**

Create an HTTP client dependency and a `UserClient` dependency. Implement:

```python
@router.get("/current-user", response_model=CurrentUser)
async def get_current_user(
    response: Response,
    access_token: str = Depends(require_session_token),
    settings: Settings = Depends(get_current_user_settings),
    user_client: UserClient = Depends(get_user_client),
) -> CurrentUser:
    ...
```

Reject an empty user-info URL with 503. Translate `RemoteAuthenticationError` into 401 after
deleting `genstack_session` with the same path, secure, HttpOnly, and SameSite settings used at
creation. Translate other `RemoteClientError` values into a stable 502 response.

Register `current_user.router` under `/api` in `app/main.py`.

- [x] **Step 5: Run route and regression tests**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_current_user.py tests/test_auth.py tests/test_api.py -q)
```

Expected: PASS.

### Task 4: Update terminology and operational documentation

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/tests/test_auth.py`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `docs/架构标准.md`
- Modify: `docs/superpowers/specs/2026-07-06-third-party-oauth-login-design.md`
- Modify: `docs/superpowers/plans/2026-07-06-third-party-oauth-login.md`

- [x] **Step 1: Replace provider-specific terminology**

Use “第三方认证服务” or “远程服务” in code comments, logger messages, tests, and maintained
documentation. Rename provider-specific test functions and fixtures so:

```bash
git grep -n -i $'\x4a\x42\x4d'
```

returns no matches.

- [x] **Step 2: Document the endpoint and client boundary**

Add `GET /api/current-user` to the public API list. Document that FastAPI reads the HttpOnly
Cookie, passes the access token to `clients`, returns only allowlisted fields, clears the Cookie
when the remote service rejects it, and maps remote availability or contract failures to 502.

- [x] **Step 3: Run all validation**

Run:

```bash
(cd backend && .venv/bin/pytest -q)
corepack pnpm --dir frontend check
docker compose config --quiet
git diff --check
```

Expected: all commands pass.

- [x] **Step 4: Audit comments and docs**

Inspect the final diff and confirm that comments explain Bearer authentication, response
allowlisting, Cookie cleanup, and stable error translation without narrating trivial syntax.
