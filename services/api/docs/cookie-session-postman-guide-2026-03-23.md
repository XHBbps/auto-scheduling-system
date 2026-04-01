# 正式用户认证 Postman 联调指南（2026-03-23）

## 1. 当前认证口径

当前后端正式认证统一使用：

- `POST /api/auth/login`
- `GET /api/auth/session`
- `POST /api/auth/logout`

登录成功后，服务端会通过 `Set-Cookie` 下发会话 Cookie；后续访问受保护接口时继续携带该 Cookie 即可。

## 2. 登录请求

- Method：`POST`
- URL：`{{baseUrl}}/api/auth/login`
- Header：`Content-Type: application/json`
- Body：

```json
{
  "username": "admin",
  "password": "your-password"
}
```

## 3. 查询当前会话

- Method：`GET`
- URL：`{{baseUrl}}/api/auth/session`

## 4. 访问受保护接口

示例：
- `GET {{baseUrl}}/api/admin/users`
- `GET {{baseUrl}}/api/data/sales-plan?page_no=1&page_size=10`

前提：
- Postman 需要自动带上登录后保存的 Cookie
- 当前用户必须具备 `admin` 角色

## 5. 退出登录

- Method：`POST`
- URL：`{{baseUrl}}/api/auth/logout`

## 6. 常见误区

- 不需要额外传自定义认证请求头，按 Cookie 会话链路调用即可。
- 登录入口统一使用 `/api/auth/login`，随后通过 Cookie 访问受保护接口。
- 登录后如果还是 401，先检查 Cookie 是否真的保存成功。

