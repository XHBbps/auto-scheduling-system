# 全系统时区统一实施计划

> 生成日期：2026-04-01 | 对应评审项：P1-6

---

## 背景

系统中存在 5 种时间写法并存：`datetime.now()`（本地时间）、`utc_now()`（UTC naive）、`func.now()`（数据库侧）、`time.time()`（Unix 时间戳）、`datetime.now(ZoneInfo(...))`（CST aware）。

当部署到 UTC 服务器时，心跳判断、任务超时、监控指标等逻辑会偏差 8 小时。

## 统一方案

**全库统一为 UTC Naive**（改动最小，不改数据库列类型）

> 约定：所有 Python datetime 存入 DB 时为 UTC naive（`tzinfo=None`，值为 UTC 时间）

---

## 改动总量

- **需修改文件**：20 个（不含 tests）
- **需修改调用点**：54 处
- **新建文件**：1 个（`datetime_utils.py`）
- **删除/合并函数**：3 个重复工具函数
- **测试同步更新**：约 5 个测试文件

---

## 执行步骤

### Step 1：新建统一时间工具模块

**新建** `services/api/app/common/datetime_utils.py`

```python
from datetime import datetime, timezone


def utc_now() -> datetime:
    """返回当前 UTC 时间（naive，无 tzinfo）。全系统唯一的时间获取入口。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    """任意 datetime 转为 UTC naive。naive 输入视为已是 UTC。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
```

**验证**：`python -c "from app.common.datetime_utils import utc_now; print(utc_now())"`

---

### Step 2：模型层 default 替换（7 处，5 个文件）

| 文件 | 行号 | 改动 |
|------|------|------|
| `app/models/background_task.py` | 29 | `default=datetime.now` → `default=utc_now` |
| `app/models/bom_backfill_queue.py` | 24 | `default=datetime.now` → `default=utc_now` |
| `app/models/sync_job_log.py` | 26 | `default=datetime.now` → `default=utc_now` |
| `app/models/sync_scheduler_state.py` | 21-22 | `default=datetime.now` → `default=utc_now`，`onupdate=datetime.now` → `onupdate=utc_now` |
| `app/models/user_session.py` | 15,17 | `default=datetime.now` → `default=utc_now` |

每个文件头部添加：`from app.common.datetime_utils import utc_now`

**验证**：全部 5 个文件 `ast.parse` 通过

---

### Step 3：Repository 层替换（7 处，3 个文件）

| 文件 | 行号 | 改动 |
|------|------|------|
| `app/repository/background_task_repo.py` | 34 | `datetime.now()` → `utc_now()` |
| `app/repository/bom_backfill_queue_repo.py` | 49,118,136,183 | `datetime.now()` → `utc_now()` |
| `app/repository/sync_scheduler_state_repo.py` | 26,27 | `datetime.now()` → `utc_now()` |

**额外清理**：`app/repository/user_session_repo.py` 行 21,51 的 `datetime.now(timezone.utc).replace(tzinfo=None)` → `utc_now()`

**验证**：语法检查 + 确认 import 正确

---

### Step 4：Services 层替换（21 处，7 个文件）

| 文件 | 行号 | 改动数 |
|------|------|--------|
| `app/services/background_task_worker_service.py` | 116,138,145,149,238,268,294,310 | 8 处 |
| `app/services/background_task_dispatch_service.py` | 50,73 | 2 处 |
| `app/services/schedule_snapshot_refresh_helpers.py` | 167,207 | 2 处 |
| `app/services/schedule_snapshot_refresh_observability.py` | 27,100 | 2 处 |
| `app/services/schedule_snapshot_refresh_refresher.py` | 97,157 | 2 处 |
| `app/services/schedule_snapshot_refresh_service.py` | 96,136,260,342 | 4 处 |
| `app/services/sync_job_observability_service.py` | 150 | 1 处 |

**验证**：语法检查 + 重点验证观测计算（行 27、150）

---

### Step 5：Sync 层替换（10 处，3 个文件）

| 文件 | 行号 | 改动数 |
|------|------|--------|
| `app/sync/sync_support_utils.py` | 47,68,79,93,106 | 5 处 |
| `app/sync/bom_sync_service.py` | 145,240,255 | 3 处 |
| `app/sync/bom_backfill_queue_service.py` | 330,459 | 2 处 |

**验证**：语法检查

---

### Step 6：Scheduler + Router 层替换（8 处，5 个文件）

| 文件 | 行号 | 改动数 |
|------|------|--------|
| `app/sync_scheduler.py` | 185,194,226 | 3 处 |
| `app/scheduler/machine_schedule_service.py` | 86 | 1 处 |
| `app/routers/admin_issue_router.py` | 36,59 | 2 处 |
| `app/routers/admin_schedule_router.py` | 74 | 1 处 |
| `app/routers/admin_part_cycle_router.py` | 164 | 1 处 |

**验证**：语法检查 + 重点验证心跳判断（sync_scheduler.py:226）

---

### Step 7：导出文件名（4 处，1 个文件）

| 文件 | 行号 | 改动 |
|------|------|------|
| `app/services/schedule_export_service.py` | 167,179,213,225 | `datetime.now()` → `utc_now()` |

**说明**：文件名时间戳改为 UTC 时间。若需要保持北京时间文件名，可用 `utc_now() + timedelta(hours=8)`，但建议统一 UTC。

**验证**：语法检查

---

### Step 8：清理重复工具函数

1. **删除** `app/services/user_auth_service.py` 中的 `ensure_naive_utc()` → 改为引用 `to_utc_naive()`
2. **删除** `app/common/auth.py` 中的 `utc_now()` → 改为从 `datetime_utils` 导入并 re-export
3. **更新** 所有引用 `from app.common.auth import utc_now` 的位置（约 2 处）

**验证**：全局搜索确认无残留引用

---

### Step 9：修复 Guandata 时间解析

`app/integration/guandata_client.py` 第 61 行：

```python
# Before: datetime.strptime(value, fmt).timestamp() * 1000
# After:
from zoneinfo import ZoneInfo
dt = datetime.strptime(value, fmt).replace(tzinfo=ZoneInfo("Asia/Shanghai"))
return dt.timestamp() * 1000
```

**说明**：Guandata 返回的时间字符串是 CST 时区，需要显式声明后再取 Unix 时间戳。

**验证**：单元测试验证解析结果

---

### Step 10：Scripts 修复（2 处）

`scripts/validate_postgres_runtime.py` 行 80,100：`datetime.now()` → `utc_now()`

**验证**：语法检查

---

### Step 11：测试文件同步更新

以下测试文件中的 `datetime.now()` 需同步改为 `utc_now()`：

- `tests/test_api/test_admin_sync_api.py`（约 5 处）
- `tests/test_sync/test_auto_bom_backfill_service.py`（约 2 处）
- `tests/test_sync/test_sync_helpers.py`（约 1 处）
- `tests/test_scheduler/test_sync_scheduler_service.py`（约 1 处）
- `tests/test_services/test_background_task_worker_service.py`（约 10 处）

**验证**：`pytest --tb=short` 全部通过

---

## 风险控制

| 风险 | 缓解措施 |
|------|---------|
| 业务日期字段（交货期等）被误改为 UTC | 这些字段无 `datetime.now()` 调用，由外部数据同步写入，不在改动范围 |
| `sales_plan_filters.py` 使用 CST 时间窗口 | 该文件的 `datetime.now(ZoneInfo(...))` 是有意为之（业务查询窗口），不在本次改动范围，但需加注释说明 |
| 历史数据时区不一致 | 现有数据若一直部署在 CST 服务器上，则 `datetime.now()` 写入的值实际是 CST naive，切换后新数据为 UTC naive。建议在迁移前统一处理，或加文档说明切换时间点 |

---

## 执行顺序和并行策略

```
Step 1（新建工具模块）
   ↓
Step 2-7（可并行：按层级分 agent 执行替换）
   ↓
Step 8（清理重复函数）
   ↓
Step 9（修复 Guandata）
   ↓
Step 10-11（Scripts + Tests）
   ↓
全量验证
```

Step 2-7 可以用 6 个并行 agent 同时执行，预计总耗时 5-10 分钟。
