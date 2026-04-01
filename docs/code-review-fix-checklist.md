# 代码评审修复清单

> 生成日期：2026-04-01 | 评审范围：全栈（后端 Python + 前端 Vue/TS + 基础设施）

---

## P0 — 必须立即修复

- [x] **P0-1** 清理 .env 中硬编码凭据，添加 .env.example 模板
  - 创建 `services/api/.env.example` 模板，所有敏感字段留空
  - 验证：.env.example 不含任何真实凭据 ✅
- [x] **P0-2** 登录接口添加暴力破解防护（频率限制）
  - 添加 `slowapi` 依赖，`auth_router.py` 登录接口加 `@limiter.limit("5/minute")`
  - `main.py` 注册 `RateLimitExceeded` 异常处理器
  - 验证：Python 语法检查通过 ✅
- [x] **P0-3** 密码字段添加最小长度和复杂度校验
  - `UserCreateRequest.password` 和 `UserPasswordResetRequest.new_password` 加 `min_length=8, max_length=128`
  - 验证：短密码被 Pydantic 拒绝，合规密码通过 ✅
- [x] **P0-4** docker-compose.yml 数据库密码改为环境变量引用
  - `POSTGRES_PASSWORD` 改为 `${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}`
  - 所有 `DATABASE_URL` 改为环境变量插值
  - 验证：YAML 解析正确 ✅

## P1 — 应该修复

### 安全类
- [x] **P1-1** 异常 `str(exc)` 不再直接返回前端，替换为固定提示语
  - `admin_schedule_router.py` 和 `admin_sync_router.py` 中 6 处 `str(exc)` 替换为固定中文提示
  - 同时添加 `exc_info=True` 保留完整日志
  - 验证：语法检查通过 ✅
- [x] **P1-2** Session Cookie `Secure` 默认值改为 `True`
  - `config.py:15` `user_session_cookie_secure` 默认值从 `False` → `True`
  - 验证：`settings.user_session_cookie_secure == True` ✅
- [x] **P1-3** 移除未使用的 `admin_api_token` 配置
  - 从 `config.py` 中删除 `admin_api_token` 字段
  - 验证：`hasattr(settings, 'admin_api_token') == False` ✅
- [x] **P1-4** `delete_sync_log` 权限从 `sync.log.view` 改为 `sync.manage`
  - `admin_sync_log_router.py` DELETE 接口 Depends 改为 `require_permission("sync.manage")`
  - 验证：语法检查通过 ✅
- [x] **P1-5** 生产环境关闭 OpenAPI 文档暴露（`/docs`, `/redoc`）
  - `main.py` 根据 `app_env` 条件设置 `docs_url=None` 和 `redoc_url=None`
  - 验证：语法检查通过 ✅

### 后端核心
- [x] **P1-6** 统一全系统时区：全库 UTC Naive 统一改造
  - 新建 `app/common/datetime_utils.py`（`utc_now()` + `to_utc_naive()`）
  - 替换 54 处 `datetime.now()` 为 `utc_now()`，覆盖 20 个文件
  - 清理重复工具函数（`auth.py` 的 `utc_now` 改为 re-export，移除 `ensure_naive_utc` 冗余调用）
  - 修复 Guandata 时间解析（附加 CST 时区再取 timestamp）
  - 验证：全部文件语法通过，app/ 和 scripts/ 中无残留 `datetime.now()` ✅
- [x] **P1-7** 数据库连接池配置（pool_size, max_overflow, pool_pre_ping, pool_recycle）
  - `database.py` 配置 `pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=3600`
  - 验证：`engine.pool.size()==10, max_overflow==20, pre_ping==True, recycle==3600` ✅
- [x] **P1-8** `subtract_workdays` 中 `int()` 截断改为 `math.ceil()`，添加最大迭代保护
  - `calendar_utils.py` 支持 float 输入，`math.ceil()` 向上取整，`MAX_WORKDAY_ITERATIONS=1000` 保护
  - 验证：`subtract_workdays(2026-04-01, 0.3, {})` 正确返回前 1 个工作日 ✅
- [x] **P1-9** BOM 层级计算 `id()` 键替换为稳定行索引
  - `bom_sync_service.py` 用 `_row_idx` 整数索引替代 `id()` 做字典键
  - 验证：语法检查通过 ✅
- [x] **P1-10** `_record_precheck_issue` 中 `pending_delivery` 路由修正
  - 新增独立的 `_record_pending_delivery_issue` 方法，与 `_record_pending_drawing_issue` 分离
  - 验证：语法检查通过，`build_pending_delivery_issue_payload` 已正确导入 ✅
- [x] **P1-11** 导出接口添加行数上限保护（默认 50000，最大 100000）
  - `schedule_export_router.py` 两个导出接口增加 `max_rows` Query 参数
  - 服务层已有 `settings.export_excel_max_rows=5000` 硬上限
  - 验证：语法检查通过 ✅
- [x] **P1-12** `GuandataClient` Token 过期时间单位统一
  - `_parse_expire_at` 对数值输入自动判断秒/毫秒（< 1e12 则乘 1000）
  - `authenticate` 改用 `time.time() * 1000` 对齐毫秒
  - 验证：三种输入格式（int秒、int毫秒、str）均正确返回毫秒级时间戳 ✅

### 前端
- [x] **P1-13** `confirmDialog` 消除 `dangerouslyUseHTMLString`，改用安全渲染
  - 使用 Vue `h()` 函数构建 VNode，完全消除 HTML 字符串拼接和 XSS 风险
  - 移除 `escapeHtml` 和 `dangerouslyUseHTMLString: true`
  - 验证：TypeScript 编译通过 ✅
- [x] **P1-14** `ensurePromise` 权限参数一致性检查
  - 并发调用等待 `ensurePromise` 完成后重新从 `getAuthSessionState()` 检查权限
  - 不再复用首次调用的权限检查结果
  - 验证：TypeScript 编译通过 ✅
- [x] **P1-15** `useUserManagementPage` 添加 catch 错误处理
  - `loadUsers`、`loadRoles`、`loadPermissions` 添加 catch 分支 + `ElMessage.error`
  - 验证：TypeScript 编译通过 ✅

## P2 — 建议改进

- [x] **P2-1** `TimestampMixin` 改用 `server_default=func.now()`
  - `models/base.py` `created_at` 和 `updated_at` 改为 `server_default`
  - 验证：语法检查通过 ✅
- [x] **P2-2** 修复 `sync_scheduler.py` 和 `admin_schemas.py` 中的中文乱码
  - 替换 `??...` 乱码为正确中文描述
  - 验证：语法检查通过 ✅
- [x] **P2-3** `FeishuClient/GuandataClient` Token 刷新添加 `asyncio.Lock`
  - 两个客户端均添加 `_token_lock = asyncio.Lock()` + 双重检查锁定模式
  - 验证：语法检查通过 ✅
- [x] **P2-4** `ensure_identity_seeded` 移至应用启动阶段，从登录 handler 中移除
  - `main.py lifespan` 中执行一次 seed
  - 从 `auth_router.py` 和 `admin_user_router.py` 中移除所有 7 处调用
  - 验证：语法检查通过 ✅
- [x] **P2-5** 各接口 `page_size` 上限统一化
  - `PageParams` 基类添加 `ge=1, le=100` 约束
  - 零件排产列表 `le=500` → `le=200`（一订单多零件场景）
  - BOM 补数队列 `page_size: int = 20` → `Query(20, ge=1, le=100)`
  - 验证：`PageParams(page_size=999)` 被 Pydantic 拒绝 ✅
- [x] **P2-6** BOM 子节点接口 `limit` 设置默认值，禁止无上限查询
  - `data_source_bom_router.py` `limit` 从 `Optional[int] = Query(None)` 改为 `int = Query(100)`
  - 验证：语法检查通过 ✅
- [x] **P2-7** Dockerfile 基础镜像从 devcontainers 改为 python:3.11-slim
  - `FROM python:3.11-slim-bookworm` 替换 `FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`
  - 验证：文件内容正确 ✅
- [x] **P2-8** Nginx 添加 `proxy_read_timeout` 配置
  - `/api/` location 添加 `proxy_read_timeout 300; proxy_send_timeout 300;`
  - 验证：配置语法正确 ✅
- [x] **P2-9** 前端类型重复定义清理（`RoleInfo` 等）
  - `authSession.ts` 中删除 `RoleInfo`/`AuthenticatedUser` 重复定义
  - 改为从 `types/apiModels.ts` 导入并 re-export
  - 验证：TypeScript 编译通过 ✅
- [x] **P2-10** `requestCache.ts` 添加最大条目限制
  - `MAX_CACHE_ENTRIES = 50`，超限时删除最旧条目
  - 验证：TypeScript 编译通过 ✅
- [x] **P2-11** `useSyncConsolePage` 轮询定时器并发竞争修复
  - 引入 `pollGeneration` 计数器，每次 `clearPollTimer` 递增 generation
  - `pollJobStatus` 在 await 返回后检查 generation 是否已变，若变则放弃本链路
  - 确保同一 key 同时只有一条活跃轮询链路
  - 验证：TypeScript 编译通过 ✅
- [x] **P2-12** 密码 `strip()` 行为统一（创建/重置/登录一致）
  - `admin_user_router.py` 创建和重置密码不再 strip，与登录行为保持一致
  - Pydantic `min_length=8` 已在 schema 层保障非空
  - 验证：语法检查通过 ✅
- [x] **P2-13** `MainLayout.vue` 的 `catch (error: any)` 改为 `error: unknown`
  - 使用 `error instanceof Error ? error.message : '请稍后重试'`
  - 验证：TypeScript 编译通过 ✅

---

## 修复统计

| 优先级 | 总计 | 已修复 | 待修复 |
|--------|------|--------|--------|
| P0     | 4    | 4      | 0      |
| P1     | 15   | 15     | 0      |
| P2     | 13   | 13     | 0      |
| **合计** | **32** | **32** | **0** |

### 全部修复完成 ✅
