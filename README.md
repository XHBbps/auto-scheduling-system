# 自动排产系统（Auto Scheduling System）

[![CI](https://github.com/XHBbps/auto-scheduling-system/actions/workflows/ci.yml/badge.svg)](https://github.com/XHBbps/auto-scheduling-system/actions/workflows/ci.yml)

面向制造企业的生产排产管理平台，通过对接 SAP BOM、观远 BI 销售计划、飞书生产订单等外部数据源，自动计算整机与零件排产结果，并提供可视化看板、异常预警和数据导出能力。

---

## 技术栈

### 后端

| 分类 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.115+ |
| 运行时 | Python 3.11，Uvicorn（ASGI） |
| ORM | SQLAlchemy 2.0（async） |
| 数据库驱动 | asyncpg |
| 数据校验 | Pydantic v2，pydantic-settings |
| 数据库迁移 | Alembic |
| 定时调度 | APScheduler 3.x |
| HTTP 客户端 | httpx |
| 接口限流 | slowapi |
| 导出 | openpyxl |

### 前端

| 分类 | 技术 |
|------|------|
| 框架 | Vue 3.5 |
| 语言 | TypeScript 5.9 |
| 构建工具 | Vite 8 |
| UI 组件库 | Element Plus 2.x |
| 图表 | ECharts 6 |
| 路由 | Vue Router 5 |
| HTTP 客户端 | Axios |
| CSS 工具 | Tailwind CSS 3 |
| 测试 | Vitest + @vue/test-utils |

### 基础设施

| 分类 | 技术 |
|------|------|
| 数据库 | PostgreSQL 16（Alpine） |
| 容器化 | Docker + Docker Compose |
| 前端容器 | Nginx |

---

## 系统架构

系统由五个 Docker 服务组成，通过 `docker-compose.yml` 统一编排：

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│  frontend   │────>│              backend（API）               │
│  Nginx:5173 │     │        FastAPI / Uvicorn :8000            │
└─────────────┘     └────────────────────┬─────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
             ┌──────▼──────┐    ┌────────▼────────┐   ┌────────▼──────┐
             │     db      │    │     worker      │   │   scheduler   │
             │ PostgreSQL  │    │  同步任务执行器  │   │  定时同步调度  │
             │    :5432    │    └─────────────────┘   └───────────────┘
             └─────────────┘
```

| 服务 | 说明 |
|------|------|
| `db` | PostgreSQL 16 数据库，持久化所有业务数据 |
| `backend` | FastAPI 应用，提供 REST API，启动时自动执行数据库健康检查和身份初始化 |
| `worker` | 异步同步任务执行器，消费同步队列（`run_sync_worker`） |
| `scheduler` | 定时任务调度器，按配置时间触发各数据源同步（`run_sync_scheduler`） |
| `frontend` | Vue 应用，由 Nginx 静态托管，反向代理至 backend |

---

## 功能模块

### 排产查询与看板

- **排产总览（Dashboard）**：整机排产、零件排产 KPI、交付风险订单、趋势图表
- **整机排产列表**：按合同号、客户、机型、排产状态、预警等级等多维筛选，支持排序和分页
- **零件排产列表**：按订单、部装、关键零件等筛选，展示排产结果
- **排产详情**：单订单的整机排产、零件排产和关联异常记录
- **排产数据导出**：整机和零件排产结果导出为 Excel（`.xlsx`），支持行数上限保护

### 异常管理

- **异常问题列表**：展示排产过程中检出的数据异常（缺图纸、缺交货期等）
- **管理员异常处理**：标记处理状态、批量操作

### 数据同步控制台

- **手动同步触发**：销售计划、BOM、生产订单、研究所数据的手动触发与状态查询
- **BOM 补数队列**：查看 BOM 自动补数进度，对失败记录执行重试
- **自动调度控制**：启停定时同步调度器，查看下次执行时间
- **同步观测摘要**：运行中任务、最近失败、超时和回收状态
- **同步日志列表**：历史同步任务的详细日志

### 基准参数配置（管理员）

- **整机周期基准**：配置各机型整机生产周期
- **零件周期基准**：配置零部件排产提前期基准
- **装配时长配置**：配置部装环节的标准装配时长
- **排产日历**：配置工厂工作日历，管理节假日和休息日

### 数据源查看

- **销售计划表**：查看从观远 BI 同步的销售计划数据
- **BOM 数据**：查看从 SAP 同步的 BOM 树结构及层级关系
- **生产订单历史**：查看从飞书同步的生产订单历史记录
- **整机周期历史**：查看历史整机加工周期数据

### 用户与权限管理

- **用户管理**：创建、编辑用户，重置密码
- **角色管理**：定义角色与权限映射关系
- **权限列表**：查看系统内置权限项

---

## 快速开始

### 环境要求

| 工具 | 最低版本 |
|------|----------|
| Docker | 24.x |
| Docker Compose | v2.x（Compose V2，内置于 Docker Desktop） |
| Node.js | 20.x（仅本地开发前端时需要） |
| Python | 3.11（仅本地开发后端时需要） |

### Docker 一键启动

**第一步：准备环境变量文件**

```bash
cp services/api/.env.example services/api/.env
```

编辑 `services/api/.env`，填写以下必填项：

```
POSTGRES_PASSWORD=your_strong_password
BOOTSTRAP_ADMIN_PASSWORD=your_admin_password
```

其余外部系统凭据（观远 BI、SAP、飞书）按实际情况填写，若暂不对接可留空。

**第二步：构建并启动所有服务**

```bash
docker compose up -d --build
```

**第三步：执行数据库迁移**

```bash
docker compose exec backend alembic upgrade head
```

**第四步：访问系统**

| 地址 | 说明 |
|------|------|
| `http://localhost:5173` | 前端页面 |
| `http://localhost:8000/docs` | Swagger API 文档（仅非生产环境可见） |
| `http://localhost:8000/redoc` | Redoc API 文档（仅非生产环境可见） |
| `http://localhost:8000/health` | 服务健康检查 |

初始管理员账号为 `admin`，密码为 `BOOTSTRAP_ADMIN_PASSWORD` 中设置的值。

**停止服务**

```bash
docker compose down
```

如需同时清除数据库卷：

```bash
docker compose down -v
```

### 本地开发启动

**后端**

```bash
cd services/api

# 安装依赖（建议使用 virtualenv 或 uv）
pip install -e ".[dev]"

# 复制并配置环境变量
cp .env.example .env
# 编辑 .env，确保 DATABASE_URL 指向本地 PostgreSQL 实例

# 执行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**

```bash
cd apps/web

# 安装依赖
npm install

# 启动开发服务器（默认代理至 http://localhost:8000）
npm run dev
```

前端默认监听 `http://localhost:5173`，开发时 Vite 会将 `/api` 请求代理至后端。

---

## 环境变量说明

配置模板位于 `services/api/.env.example`，复制为 `services/api/.env` 后按需填写。

### 数据库

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串（asyncpg 协议） | `postgresql+asyncpg://postgres:pwd@127.0.0.1:5432/auto_scheduling` |
| `POSTGRES_PASSWORD` | Docker Compose 中数据库密码（必须设置） | `your_strong_password` |

### 应用

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_ENV` | 运行环境（`development` / `production`） | `development` |
| `BOOTSTRAP_ADMIN_PASSWORD` | 初始管理员密码，首次启动时写入数据库 | — |
| `BOOTSTRAP_ADMIN_USERNAME` | 初始管理员用户名 | `admin` |

### 外部数据源

| 变量 | 说明 |
|------|------|
| `GUANDATA_BASE_URL` | 观远 BI 服务地址（销售计划同步） |
| `GUANDATA_DOMAIN` | 观远 BI 域名 |
| `GUANDATA_LOGIN_ID` | 观远 BI 登录账号 |
| `GUANDATA_PASSWORD` | 观远 BI 登录密码 |
| `GUANDATA_DS_ID` | 观远 BI 数据集 ID |
| `SAP_BOM_BASE_URL` | SAP BOM 接口地址 |
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `FEISHU_PRODUCTION_APP_TOKEN` | 飞书生产订单多维表格 App Token |
| `FEISHU_PRODUCTION_TABLE_ID` | 飞书生产订单多维表格 Table ID |
| `FEISHU_RESEARCH_APP_TOKEN` | 飞书研究所数据多维表格 App Token |
| `FEISHU_RESEARCH_TABLE_ID` | 飞书研究所数据多维表格 Table ID |

### 排产与同步参数

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SCHEDULE_TRIGGER_ADVANCE_DAYS` | 排产触发提前天数 | `28` |
| `SYNC_SCHEDULER_ENABLED` | 是否启用定时自动同步 | `false` |
| `SYNC_SCHEDULER_TIMEZONE` | 定时任务时区 | `Asia/Shanghai` |
| `SALES_PLAN_SYNC_HOUR` / `SALES_PLAN_SYNC_MINUTE` | 销售计划定时同步时刻 | `6:00` |
| `BOM_SYNC_HOUR` / `BOM_SYNC_MINUTE` | BOM 定时同步时刻 | `6:30` |
| `PRODUCTION_ORDER_SYNC_HOUR` / `PRODUCTION_ORDER_SYNC_MINUTE` | 生产订单定时同步时刻 | `7:00` |
| `RESEARCH_SYNC_HOUR` / `RESEARCH_SYNC_MINUTE` | 研究所数据定时同步时刻 | `7:30` |

---

## 项目结构

```
auto-scheduling-system/
├── docker-compose.yml              # 服务编排配置
├── apps/
│   └── web/                        # 前端 Vue 应用
│       ├── src/
│       │   ├── views/              # 页面组件
│       │   ├── components/         # 可复用组件（按页面分组）
│       │   ├── layouts/            # 布局组件
│       │   ├── router/             # 路由配置与权限守卫
│       │   ├── utils/              # 工具函数（认证、缓存等）
│       │   └── types/              # TypeScript 类型定义
│       ├── package.json
│       └── vite.config.ts
└── services/
    └── api/                        # 后端 FastAPI 应用
        ├── app/
        │   ├── main.py             # 应用入口，路由注册，生命周期
        │   ├── config.py           # 配置类（pydantic-settings）
        │   ├── database.py         # 数据库引擎与连接池
        │   ├── models/             # SQLAlchemy ORM 模型
        │   ├── repository/         # 数据访问层
        │   ├── schemas/            # Pydantic 请求/响应 Schema
        │   ├── routers/            # API 路由（FastAPI Router）
        │   ├── services/           # 业务服务层
        │   ├── sync/               # 数据同步任务实现
        │   ├── scheduler/          # 排产引擎
        │   ├── baseline/           # 基准参数计算服务
        │   ├── integration/        # 外部系统客户端（飞书/观远/SAP）
        │   └── common/             # 公共工具（异常、枚举、日历计算等）
        ├── alembic/                # 数据库迁移脚本
        │   └── versions/           # 迁移版本文件
        ├── scripts/                # 运维脚本（初始化、等待数据库等）
        ├── docker/                 # 容器启动脚本
        ├── tests/                  # 单元测试与集成测试
        ├── pyproject.toml          # Python 项目配置与依赖
        ├── .env.example            # 环境变量模板
        └── alembic.ini             # Alembic 配置
```

---

## API 文档

后端服务在非生产环境（`APP_ENV` 不为 `production`）下自动开放交互式 API 文档：

| 地址 | 类型 | 说明 |
|------|------|------|
| `http://localhost:8000/docs` | Swagger UI | 支持在线调试，显示请求耗时，默认展开接口列表 |
| `http://localhost:8000/redoc` | Redoc | 适合阅读的静态文档格式 |

API 按标签分组，主要包含：

| 标签 | 说明 |
|------|------|
| 用户认证 | 登录、登出、获取当前会话 |
| 排产查询 | 整机列表、零件列表、排产详情、总览数据 |
| 排产管理 | 触发排产、快照刷新（管理员） |
| 手动同步 | 触发各数据源同步、BOM 补数队列管理 |
| 整机周期基准 | 基准参数的增删改查 |
| 零件周期基准 | 零件排产提前期基准管理 |
| 装配时长配置 | 部装标准时长管理 |
| 排产日历 | 工厂工作日历管理 |
| 异常问题管理 | 异常记录查询与状态管理 |
| 同步日志 | 历史同步任务日志查询 |
| 用户管理 | 用户、角色、权限的增删改查 |
| 数据源查看 | 销售计划、BOM、生产订单、周期历史 |
| 排产导出 | 整机/零件排产 Excel 导出 |

---

## 开发指南

### 数据库迁移

使用 Alembic 管理数据库 Schema 变更。

```bash
# 进入后端目录
cd services/api

# 应用所有待执行迁移
alembic upgrade head

# 生成新的迁移脚本（变更 models/ 后执行）
alembic revision --autogenerate -m "描述变更内容"

# 查看当前迁移版本
alembic current

# 回退一个版本
alembic downgrade -1
```

迁移文件命名规范：`YYYYMMDD_NNNN_描述.py`，例如 `20260320_0001_baseline_schema.py`。

> 注意：在开发环境中可以将 `DATABASE_AUTO_CREATE_ALL=true` 快速建表，但正式环境应始终通过 Alembic 迁移管理 Schema。

### 运行测试

```bash
cd services/api

# 运行全部测试
pytest

# 运行并输出覆盖率报告
pytest --cov=app --cov-report=term-missing
```

### 前端代码检查与构建

```bash
cd apps/web

# 代码规范检查（ESLint，零警告策略）
npm run lint

# TypeScript 类型检查 + 生产构建
npm run build

# 分析产物 chunk 大小
npm run build:observe
```

### 代码规范

- **后端**：遵循 PEP 8，所有时间字段统一使用 UTC naive datetime（通过 `app.common.datetime_utils.utc_now()` 获取）
- **前端**：ESLint + TypeScript 严格模式，零警告策略（`--max-warnings 0`）
- **API 响应**：统一使用 `ApiResponse[T]` 包装，业务异常通过 `BizException` 抛出，状态码固定返回 200，通过 `code` 字段区分业务状态
- **权限控制**：所有后端接口通过 `require_permission("permission.key")` 守卫，前端路由通过 `requiredPermissions` / `requiredAnyPermissions` meta 字段控制访问
