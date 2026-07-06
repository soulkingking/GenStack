# 当前用户客户端设计

## 目标

在现有 OAuth2 登录基础上增加 `GET /api/current-user`。FastAPI 从 HttpOnly Cookie
读取 Access Token，通过 `clients` 目录中的公共 HTTP 客户端请求第三方用户信息接口，
并向前端返回经过白名单过滤的当前用户数据。

本次保持现有轻量架构，不引入独立认证代理、Redis、Token 刷新、数据库用户同步或权限
持久化。

## 目录

```text
backend/app/
├── api/
│   ├── auth.py
│   └── current_user.py
├── clients/
│   ├── __init__.py
│   ├── base.py
│   └── user.py
├── core/
│   └── config.py
└── main.py
```

- `api/auth.py`：继续管理 OAuth2 登录和 Cookie，并提供读取有效 Session Token 的依赖。
- `api/current_user.py`：声明当前用户 HTTP 接口，不处理远程协议细节。
- `clients/base.py`：统一处理 Authorization、超时、HTTP 状态和业务响应外壳。
- `clients/user.py`：调用用户信息接口，并将远程字段映射为本站用户模型。

客户端不读取 FastAPI Request 或 Cookie。HTTP 边界先取得 Token，再将 Token 显式传给
客户端，避免远程客户端依赖 Web 框架。

## 请求流程

```text
GET /api/current-user
→ 从 genstack_session HttpOnly Cookie 读取 Access Token
→ UserClient.get_current_user(access_token)
→ Authorization: Bearer <access_token>
→ 第三方用户信息接口
→ 校验 HTTP 状态及业务响应
→ 白名单映射
→ 返回本站 CurrentUser
```

Cookie 缺失或为空时返回 401，不调用第三方服务。

## 配置

新增后端配置：

```dotenv
OAUTH2_USERINFO_URL=http://127.0.0.1:5555/oauth2/userinfo
```

该地址必须与其他 OAuth2 地址一样只存在于后端运行配置，并通过 Docker Compose 传入
后端容器。

## 公共响应

接口只返回当前页面和后续权限判断需要的字段：

```json
{
  "user_id": 1,
  "username": "admin",
  "real_name": "管理员",
  "dept_id": 10,
  "dept_name": "平台部门",
  "company_id": 20,
  "roles": ["admin"],
  "permissions": ["system:read"],
  "menu_permissions": ["dashboard"],
  "role_permissions": ["ROLE_ADMIN"]
}
```

字段允许为空，集合缺失时返回空数组。明确禁止向前端返回：

- Access Token、Refresh Token 或其他 Token 字段
- 登录账号、客户端密钥
- 登录 IP、设备信息
- 第三方响应中未列入白名单的扩展字段

## 客户端契约

`clients/base.py` 提供共享异步请求能力：

- Token 由调用方显式传入。
- 请求头固定使用 `Authorization: Bearer <token>`。
- 设置明确的连接/读取超时。
- 要求 HTTP 响应成功。
- 要求业务响应 `code === 200`、`success === true` 且 `result` 为对象。
- 日志不得包含 Token、Authorization Header 或完整远程响应。

`clients/user.py` 只负责用户信息地址和字段白名单映射。后续增加其他远程能力时，可新增
`clients/order.py`、`clients/file.py` 等，共用 `clients/base.py`。

## 错误处理

- Session Cookie 缺失：返回 401。
- 第三方服务返回 401/403：清除本站登录 Cookie 并返回 401，前端重新进入登录流程。
- 第三方服务超时、连接失败或 5xx：返回 502。
- 业务响应失败、JSON 非法或用户对象缺失：返回 502。
- 对外错误消息保持稳定，不透传第三方响应中的敏感信息。

## 测试

后端测试覆盖：

- 缺少 Cookie 时不调用客户端并返回 401。
- 客户端使用 `Bearer` Header 且不泄露 Token。
- 成功响应只返回白名单字段。
- Token 字段和未知字段被过滤。
- 远程 401/403 清除 Cookie。
- 网络失败、业务失败、非法 JSON 和缺少用户对象返回 502。

回归检查继续运行完整后端测试、前端检查和 `git diff --check`。

## 文档和注释

同步更新 `.env.example`、Docker Compose、README 和架构文档。认证与客户端文档统一使用
“第三方认证服务”或“远程服务”，不使用具体系统名称。

注释仅解释 Bearer 前缀、响应白名单、Cookie 清理和错误转换等无法从代码命名直接推断的
约束。
