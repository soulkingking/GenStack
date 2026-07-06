# 第三方 OAuth2 登录设计

## 目标

GenStack 作为 OAuth2 客户端接入 JBM 认证服务。用户访问系统时：

1. 已有有效登录 Cookie 则直接进入系统。
2. 未登录且回调 URL 包含 `code` 时，由 GenStack 后端用授权码兑换 Token。
3. 兑换成功后建立本站登录会话并进入系统。
4. 未携带 `code`，或首次兑换失败时，重定向到 JBM 授权页面。
5. 同一浏览器标签页连续兑换失败时展示错误，防止错误配置造成无限重定向。

本次只建立登录入口和会话判断，不实现用户同步、权限模型、Token 刷新、主动登出或业务接口代理。

## 已确认的 JBM 契约

授权入口为 `/oauth2/authorize`，使用授权码模式时包含：

- `response_type=code`
- `client_id`
- `redirect_uri`
- `scope`
- `state`

Token 入口为 `/oauth2/token`。虽然 Swagger 模型没有展示 `client_secret`，JBM 底层实现会强制读取并校验以下参数：

- `grant_type=authorization_code`
- `code`
- `client_id`
- `client_secret`
- `redirect_uri`

JBM 控制器同时接受 GET 和 POST。GenStack 使用
`POST application/x-www-form-urlencoded`，避免 `client_secret` 出现在 URL、浏览器历史或常规访问日志中。

成功响应是 JBM `ResultBody`：

```json
{
  "code": 200,
  "success": true,
  "result": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "refresh_expires_in": 2592000,
    "client_id": "...",
    "scope": "...",
    "openid": "..."
  }
}
```

GenStack 仅在 HTTP 请求成功、`code === 200`、`success === true` 且
`result.access_token` 为非空字符串时接受响应。授权码只能兑换一次，兑换时的
`redirect_uri` 必须与申请授权码时完全一致。

## 方案选择

采用“前端 Auth Gate + FastAPI 兑换 Token + HttpOnly Cookie”：

- React 负责识别回调参数和控制页面状态。
- FastAPI 保存 OAuth2 客户端密钥、校验 `state` 并调用 JBM Token 接口。
- 浏览器只持有 HttpOnly Cookie，前端 JavaScript 不接触 Access Token。
- 后续业务请求需要访问 JBM 时，由 FastAPI 从 Cookie 读取 Token 并作为 BFF 转发；本次不实现业务代理。

未采用以下方案：

- 后端直接接收 OAuth2 回调：实现更简单，但不符合前端判断 `code` 的既定流程。
- 前端直接兑换或把 Token 保存到 `localStorage`：会暴露客户端密钥或扩大 XSS 后的 Token 泄露面。
- 内存会话表：当前模板没有数据库或 Redis，多进程和重启时无法保持一致。

## 配置

配置由 `backend/app/core/config.py` 统一读取：

| 环境变量 | 作用 |
| --- | --- |
| `OAUTH2_AUTHORIZE_URL` | JBM 完整授权地址 |
| `OAUTH2_TOKEN_URL` | JBM 完整 Token 地址 |
| `OAUTH2_CLIENT_ID` | GenStack 在 JBM 注册的客户端 ID |
| `OAUTH2_CLIENT_SECRET` | 仅后端可读取的客户端密钥 |
| `OAUTH2_REDIRECT_URI` | JBM 注册的固定前端回调地址 |
| `OAUTH2_SCOPE` | 授权范围，允许为空 |
| `AUTH_COOKIE_SECURE` | 生产 HTTPS 环境设为 `true` |

`redirect_uri` 使用显式配置，不能根据请求的 Host 动态拼接，避免 Host Header
影响 OAuth2 回调目标。密钥不得进入前端环境变量、前端构建产物、日志或 API 响应。

## 后端边界

新增独立认证路由，不把认证流程写入 `app/main.py`：

### `GET /api/auth/session`

检查登录 Cookie 是否存在，返回：

```json
{ "authenticated": true }
```

该接口不返回 Token、过期时间或客户端密钥。浏览器 Cookie 到期后返回
`authenticated: false`。

### `GET /api/auth/login`

1. 使用密码学安全随机数生成 `state`。
2. 写入短期 `oauth_state` HttpOnly Cookie，有效期 5 分钟。
3. 以固定配置构建 JBM `/oauth2/authorize` URL。
4. 返回 302 重定向。

授权参数使用标准 URL 编码，`response_type` 固定为 `code`。

### `POST /api/auth/token`

请求 JSON：

```json
{ "code": "...", "state": "..." }
```

处理顺序：

1. 校验 `code` 和 `state` 非空。
2. 使用常量时间比较请求 `state` 与 `oauth_state` Cookie。
3. 使用固定配置向 JBM Token 地址发送表单请求。
4. 校验 HTTP 状态和 JBM 业务响应。
5. 将 `access_token` 写入 `genstack_session` HttpOnly Cookie。
6. Cookie 的 `Max-Age` 使用合法的正数 `expires_in`；上游未提供合法值时使用保守默认值。
7. 清除一次性的 `oauth_state` Cookie。
8. 仅返回 `{ "authenticated": true }`。

登录 Cookie 使用 `HttpOnly`、`SameSite=Lax`、`Path=/`；生产环境由
`AUTH_COOKIE_SECURE=true` 启用 `Secure`。Token 兑换设置明确的网络超时。

Token Cookie 当前承担最小会话能力。未来引入数据库或 Redis 时，可把它替换为随机
Session ID 和服务端 Token 存储，而不改变前端接口。

## 前端边界

新增 Auth Gate 包裹系统页面，状态包括：

- `checking`：检查已有会话。
- `exchanging`：使用回调 `code/state` 建立会话。
- `redirecting`：准备跳转授权服务。
- `authenticated`：允许渲染系统页面。
- `error`：连续失败后展示可重试错误。

启动流程：

1. 请求 `/api/auth/session`。
2. 已登录则渲染现有首页。
3. 未登录时读取当前 URL 的 `code`、`state` 和 `error`。
4. 存在 OAuth2 错误参数时按兑换失败处理。
5. 存在 `code` 时调用 `/api/auth/token`。
6. 兑换成功后用 `history.replaceState` 清除回调查询参数，再进入首页。
7. 没有 `code` 时跳转 `/api/auth/login`。

首次兑换失败时，在 `sessionStorage` 记录一次重试并跳转 `/api/auth/login`。同一标签页
再次失败时停止自动跳转并展示错误与“重新登录”按钮。成功后清除重试标记。

加载和重定向阶段只展示简洁状态，不短暂渲染受保护页面，避免未认证内容闪现。

## 错误处理与安全约束

- 不记录授权码、Access Token、Refresh Token 或客户端密钥。
- `state` 缺失或不匹配返回 400，不请求 JBM。
- 配置缺失返回可诊断的 503，但响应不包含密钥。
- JBM 网络失败、非成功 HTTP 状态、业务失败或缺少 Token 均视为兑换失败。
- 后端返回面向前端的稳定错误消息；详细异常仅记录不含敏感值的类型和上下文。
- 前端自动重试最多一次，避免授权服务或客户端配置异常时形成重定向循环。
- 不把 JBM 返回的 Refresh Token 写入浏览器；Token 刷新不在本次范围内。

## 测试

后端测试覆盖：

- 登录入口生成完整授权 URL 和短期 `state` Cookie。
- 缺少或错误 `state` 时拒绝兑换。
- Token 请求包含固定 `client_id`、后端 `client_secret`、授权码模式及一致的回调地址。
- JBM HTTP 失败、业务失败、缺少 `access_token` 时不建立会话。
- 成功兑换时登录 Cookie 的安全属性和有效期正确。
- Session 接口只暴露布尔认证状态。

前端测试覆盖：

- 已登录时直接进入首页。
- 未登录且无 `code` 时跳转登录入口。
- 有 `code/state` 时兑换、清理 URL 并进入首页。
- 首次兑换失败重新授权。
- 连续失败时显示错误且不再自动跳转。

回归检查保留现有 health/meta 测试，并运行：

```bash
(cd backend && .venv/bin/pytest -q)
corepack pnpm --dir frontend check
git diff --check
```

## 文档与注释

实现时同步更新：

- `.env.example`：补充 OAuth2 配置，密钥使用占位值。
- `README.md`：增加第三方登录配置和运行说明，移除“当前不包含登录”的描述。
- `docs/架构标准.md`：记录认证边界、Cookie 会话和 FastAPI BFF 职责。
- `backend/README.md`、`frontend/README.md`：补充各自认证职责。

代码注释只解释无法从类型和命名直接推断的约束，包括 JBM 隐式要求
`client_secret`、固定 `redirect_uri`、一次性授权码、Cookie 属性及重定向循环保护。
