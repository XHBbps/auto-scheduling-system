# 正式用户认证 Curl 联调示例（2026-03-23）

本文档记录当前正式登录链路的 curl 用法。
当前统一使用：

- `POST /api/auth/login`
- `GET /api/auth/session`
- `POST /api/auth/logout`

> 说明：受保护接口依赖浏览器 / curl 保存的会话 Cookie，统一按 `/api/auth/*` + `user_session` 链路联调。

## 1. 登录并保存 Cookie

```bash
curl -i -c auth.cookie -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

## 2. 查询当前会话

```bash
curl -b auth.cookie http://127.0.0.1:8000/api/auth/session
```

## 3. 调用受保护接口

```bash
curl -b auth.cookie "http://127.0.0.1:8000/api/admin/users"
```

```bash
curl -b auth.cookie "http://127.0.0.1:8000/api/data/sales-plan?page_no=1&page_size=10"
```

## 4. 退出登录

```bash
curl -b auth.cookie -c auth.cookie -X POST http://127.0.0.1:8000/api/auth/logout
```

## 5. 常见问题

- 登录成功后访问接口仍返回 401：优先检查 Cookie 是否保存成功、后续请求是否真的带上 Cookie。
- 返回 403：说明当前登录用户已认证，但没有 `admin` 角色。
- 仍然出现认证失败：优先检查是否已先完成 `/api/auth/login`，以及当前请求是否正确带上会话 Cookie。

