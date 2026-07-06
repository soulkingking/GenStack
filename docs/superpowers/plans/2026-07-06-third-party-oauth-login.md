# Third-Party OAuth Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JBM OAuth2 authorization-code login to GenStack while keeping the client secret and access token outside frontend JavaScript.

**Architecture:** React uses an `AuthGate` to check the current HttpOnly-cookie session, exchange callback parameters through FastAPI, and redirect unauthenticated users to a backend login endpoint. FastAPI owns OAuth2 configuration, state validation, the JBM token request, response validation, and session-cookie creation.

**Tech Stack:** FastAPI, pydantic-settings, httpx, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library

---

## File map

- Create `backend/app/api/auth.py`: OAuth2 login, token exchange, and session endpoints.
- Create `backend/tests/test_auth.py`: backend authentication contract tests with mocked JBM transport.
- Modify `backend/app/core/config.py`: typed OAuth2 and cookie settings.
- Modify `backend/app/main.py`: register the authentication router.
- Modify `backend/requirements.txt`: make `httpx` a runtime dependency.
- Modify `docker-compose.yml`: pass OAuth2 settings from the root `.env` into the backend container.
- Create `frontend/src/api/auth.ts`: stable frontend authentication API boundary.
- Create `frontend/src/app/auth-gate.tsx`: authentication state machine and redirect-loop guard.
- Create `frontend/src/app/auth-gate.test.tsx`: frontend flow tests.
- Modify `frontend/src/app/app.tsx`: protect application routes with `AuthGate`.
- Modify `.env.example`, `README.md`, `backend/README.md`, `frontend/README.md`, and
  `docs/架构标准.md`: document configuration and runtime behavior.

### Task 1: Backend OAuth2 configuration

**Files:**
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_config.py`

- [x] **Step 1: Add failing configuration tests**

Add tests that construct `Settings` without reading `.env` and assert trimmed URL/client values,
the default scope, five-minute state lifetime, conservative session lifetime, and insecure local
cookie default:

```python
def test_oauth2_settings_have_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.oauth2_scope == ""
    assert settings.oauth2_state_ttl_seconds == 300
    assert settings.oauth2_default_session_ttl_seconds == 3600
    assert settings.auth_cookie_secure is False


def test_oauth2_configuration_is_complete_only_when_required_values_exist() -> None:
    incomplete = Settings(_env_file=None)
    complete = Settings(
        _env_file=None,
        oauth2_authorize_url="https://auth.example/oauth2/authorize",
        oauth2_token_url="https://auth.example/oauth2/token",
        oauth2_client_id="client",
        oauth2_client_secret="secret",
        oauth2_redirect_uri="https://app.example/",
    )

    assert incomplete.oauth2_configured is False
    assert complete.oauth2_configured is True
```

- [x] **Step 2: Run the configuration tests and verify failure**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_config.py -q)
```

Expected: FAIL because the OAuth2 settings and `oauth2_configured` property do not exist.

- [x] **Step 3: Add typed settings**

Add these fields and property to `Settings`:

```python
oauth2_authorize_url: str = ""
oauth2_token_url: str = ""
oauth2_client_id: str = ""
oauth2_client_secret: SecretStr = SecretStr("")
oauth2_redirect_uri: str = ""
oauth2_scope: str = ""
oauth2_state_ttl_seconds: int = Field(default=300, gt=0)
oauth2_default_session_ttl_seconds: int = Field(default=3600, gt=0)
auth_cookie_secure: bool = False

@property
def oauth2_configured(self) -> bool:
    """返回第三方登录所需配置是否完整，不暴露具体缺失的密钥值。"""

    return all(
        value.strip()
        for value in (
            self.oauth2_authorize_url,
            self.oauth2_token_url,
            self.oauth2_client_id,
            self.oauth2_client_secret.get_secret_value(),
            self.oauth2_redirect_uri,
        )
    )
```

- [x] **Step 4: Run the configuration tests**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_config.py -q)
```

Expected: PASS.

### Task 2: FastAPI OAuth2 endpoints

**Files:**
- Create: `backend/app/api/auth.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [x] **Step 1: Write failing login and session tests**

Create an isolated FastAPI test app that injects `Settings` and an `httpx.MockTransport`. Cover:

```python
def test_login_redirects_with_state_and_fixed_oauth_parameters() -> None:
    response = asyncio.run(_request("GET", "/api/auth/login"))

    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["genstack-client"]
    assert query["redirect_uri"] == ["http://127.0.0.1:5173/"]
    assert query["scope"] == ["all"]
    assert query["state"] == [response.cookies["oauth_state"]]


def test_session_only_reports_cookie_presence() -> None:
    response = asyncio.run(
        _request("GET", "/api/auth/session", cookies={"genstack_session": "private-token"})
    )

    assert response.json() == {"authenticated": True}
    assert "private-token" not in response.text
```

- [x] **Step 2: Write failing token-exchange tests**

Cover missing/mismatched state, successful JBM response, HTTP failure, JBM `success: false`, and
missing `access_token`. In the success handler, assert the outbound form contains:

```python
assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
assert parse_qs(request.content.decode()) == {
    "grant_type": ["authorization_code"],
    "code": ["one-time-code"],
    "client_id": ["genstack-client"],
    "client_secret": ["server-secret"],
    "redirect_uri": ["http://127.0.0.1:5173/"],
}
```

Assert the API response is only `{"authenticated": True}`, the session Cookie is HttpOnly,
SameSite=Lax, and `oauth_state` is cleared.

- [x] **Step 3: Run auth tests and verify failure**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_auth.py -q)
```

Expected: FAIL because `app.api.auth` and its dependency hooks do not exist.

- [x] **Step 4: Implement the authentication router**

Implement:

```python
router = APIRouter(prefix="/auth", tags=["authentication"])
STATE_COOKIE_NAME = "oauth_state"
SESSION_COOKIE_NAME = "genstack_session"


class TokenExchangeRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class SessionStatus(BaseModel):
    authenticated: bool
```

Provide dependency functions for `Settings` and an `httpx.AsyncClient` so tests can inject a
mock transport. `GET /login` must reject incomplete configuration with 503, generate state via
`secrets.token_urlsafe(32)`, set a five-minute HttpOnly state Cookie, and return
`RedirectResponse(status_code=302)`.

`POST /token` must compare state using `secrets.compare_digest`, submit the form to JBM with an
explicit timeout, validate the `ResultBody`, clamp invalid/non-positive `expires_in` to the
configured default, set `genstack_session`, and clear `oauth_state`. Error responses must never
echo the upstream body because it may contain sensitive authentication data.

`GET /session` returns only whether `genstack_session` is a non-empty string.

- [x] **Step 5: Register the router and runtime dependency**

In `backend/app/main.py`:

```python
from app.api import auth, health

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
```

Move `httpx>=0.28.0,<1` into `backend/requirements.txt`; keep only `pytest` in
`backend/requirements-dev.txt` because `-r requirements.txt` already installs runtime packages.

- [x] **Step 6: Run backend auth and regression tests**

Run:

```bash
(cd backend && .venv/bin/pytest tests/test_auth.py tests/test_api.py tests/test_config.py -q)
```

Expected: PASS.

### Task 3: Frontend authentication API

**Files:**
- Create: `frontend/src/api/auth.ts`
- Test: `frontend/src/api/auth.test.ts`

- [x] **Step 1: Write failing API tests**

Mock `fetch` and cover session status, token exchange request shape, and stable errors:

```typescript
expect(fetch).toHaveBeenCalledWith("/api/auth/token", {
  method: "POST",
  credentials: "same-origin",
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  body: JSON.stringify({ code: "code", state: "state" }),
});
```

- [x] **Step 2: Run the API tests and verify failure**

Run:

```bash
corepack pnpm --dir frontend test -- src/api/auth.test.ts
```

Expected: FAIL because `src/api/auth.ts` does not exist.

- [x] **Step 3: Implement the authentication API**

Export:

```typescript
export interface SessionStatus {
  authenticated: boolean;
}

export function getSession(): Promise<SessionStatus>;
export function exchangeAuthorizationCode(code: string, state: string): Promise<SessionStatus>;
export const LOGIN_URL = "/api/auth/login";
```

Use a private JSON request helper that sends `credentials: "same-origin"`, rejects non-2xx
responses, and verifies the response contains a boolean `authenticated` field.

- [x] **Step 4: Run the frontend API tests**

Run:

```bash
corepack pnpm --dir frontend test -- src/api/auth.test.ts
```

Expected: PASS.

### Task 4: React Auth Gate

**Files:**
- Create: `frontend/src/app/auth-gate.tsx`
- Create: `frontend/src/app/auth-gate.test.tsx`
- Modify: `frontend/src/app/app.tsx`

- [x] **Step 1: Write failing Auth Gate tests**

Mock `getSession` and `exchangeAuthorizationCode`. Cover:

```typescript
it("renders protected content for an existing session", async () => {});
it("redirects an unauthenticated request without a code", async () => {});
it("exchanges a callback code, cleans the URL, and renders content", async () => {});
it("restarts authorization after the first exchange failure", async () => {});
it("shows an error instead of looping after a repeated failure", async () => {});
```

Inject navigation functions through optional props in tests so jsdom does not need to perform a
real document navigation:

```typescript
interface AuthGateProps {
  children: ReactNode;
  redirect?: (url: string) => void;
  replaceUrl?: (url: string) => void;
}
```

- [x] **Step 2: Run the Auth Gate tests and verify failure**

Run:

```bash
corepack pnpm --dir frontend test -- src/app/auth-gate.test.tsx
```

Expected: FAIL because `AuthGate` does not exist.

- [x] **Step 3: Implement the Auth Gate state machine**

Use a single `useEffect` with a cancellation flag. Check session first, then parse `code`, `state`,
and `error` from `window.location.search`. On success, remove OAuth2 parameters with
`history.replaceState`; preserve unrelated query parameters and the hash.

Use `sessionStorage` key `genstack_oauth_retry`:

- first callback failure: set the key and redirect to `LOGIN_URL`;
- repeated failure: render an alert and a “重新登录” button;
- successful session or exchange: remove the key.

Loading states render `role="status"`; the error uses `role="alert"`. Do not render children until
authentication succeeds.

- [x] **Step 4: Protect the application**

Wrap `BrowserRouter` in `frontend/src/app/app.tsx`:

```tsx
<AuthGate>
  <BrowserRouter>
    <Routes>
      <Route path="*" element={<HomePage />} />
    </Routes>
  </BrowserRouter>
</AuthGate>
```

- [x] **Step 5: Run frontend authentication and page tests**

Run:

```bash
corepack pnpm --dir frontend test -- \
  src/api/auth.test.ts src/app/auth-gate.test.tsx src/pages/home-page.test.tsx
```

Expected: PASS.

### Task 5: Configuration and documentation

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Modify: `docs/架构标准.md`

- [x] **Step 1: Add environment placeholders**

Add non-secret examples:

```dotenv
# OAuth2 第三方登录
OAUTH2_AUTHORIZE_URL=http://127.0.0.1:5555/oauth2/authorize
OAUTH2_TOKEN_URL=http://127.0.0.1:5555/oauth2/token
OAUTH2_CLIENT_ID=replace-with-client-id
OAUTH2_CLIENT_SECRET=replace-with-client-secret
OAUTH2_REDIRECT_URI=http://127.0.0.1:5173/
OAUTH2_SCOPE=all
AUTH_COOKIE_SECURE=false
```

Pass the same variables through `docker-compose.yml` using `${NAME:-}` interpolation so Compose
deployments can use the root `.env` without enabling unrelated settings from that file.

- [x] **Step 2: Update architecture and runbooks**

Document the three local endpoints, the JBM OAuth2 flow, exact redirect URI registration,
production HTTPS/Secure Cookie requirement, client-secret boundary, and the absence of refresh,
logout, user synchronization, and authorization in this increment. Remove every statement that
claims login is not implemented.

- [x] **Step 3: Audit comments and documentation**

Inspect the full diff. Keep comments explaining JBM's hidden `client_secret` requirement, fixed
redirect URI, state validation, cookie lifetime, and redirect-loop prevention. Remove comments
that still describe authentication as a placeholder.

### Task 6: Full verification

**Files:**
- Verify all changed files.

- [x] **Step 1: Run backend tests**

Run:

```bash
(cd backend && .venv/bin/pytest -q)
```

Expected: all tests pass.

- [x] **Step 2: Run frontend checks**

Run:

```bash
corepack pnpm --dir frontend check
```

Expected: lint, typecheck, tests, and production build pass.

- [x] **Step 3: Run repository hygiene checks**

Run:

```bash
git diff --check
rg -n "登录接口尚未实现|当前不包含登录|认证账号.*预留" \
  README.md backend frontend docs .env.example
```

Expected: `git diff --check` passes and the stale-document search returns no matches.

- [x] **Step 4: Review the final diff**

Confirm no real secret, access token, authorization code, unrelated generated file, or stale
comment is present. Confirm the only browser-visible authentication response is the boolean
session status.

- [x] **Step 5: Commit the implementation**

```bash
git add .env.example README.md backend frontend docs/架构标准.md \
  docs/superpowers/plans/2026-07-06-third-party-oauth-login.md
git commit -m "feat: add third-party OAuth login"
```
