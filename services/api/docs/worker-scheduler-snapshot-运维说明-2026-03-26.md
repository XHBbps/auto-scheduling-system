# worker / scheduler / snapshot 运维说明（2026-03-26）

> 适用范围：`auto-scheduling-system/services/api`
> 目标：让后端同学接手任务系统时，能快速理解启动方式、观察指标与故障处理流程。
> 依据代码：
> - `E:\Vibe Coding\SOUL\docker-compose.yml`
> - `services/api/docker/backend-entrypoint.sh`
> - `services/api/docker/worker-entrypoint.sh`
> - `services/api/docker/scheduler-entrypoint.sh`
> - `services/api/scripts/run_sync_worker.py`
> - `services/api/scripts/run_sync_scheduler.py`
> - `services/api/app/main.py`
> - `services/api/app/sync_scheduler.py`
> - `services/api/app/services/background_task_worker_service.py`
> - `services/api/app/services/schedule_snapshot_refresh_service.py`
> - `services/api/app/routers/admin_sync_router.py`
> - `services/api/app/routers/admin_schedule_router.py`

---

## 1. 服务分工

当前任务系统已经拆成 4 个常驻服务：

1. `db`
   - PostgreSQL 16
   - 任务、同步日志、快照、业务数据都落在这里

2. `backend`
   - FastAPI API 服务
   - 提供 `/health`、手动同步、排产、导出、观测接口
   - 默认启动时执行：
     - `wait_for_db`
     - `alembic upgrade head`
     - `prewarm_snapshots`
     - `uvicorn app.main:app`

3. `worker`
   - 负责消费 `background_task` 表中的后台任务
   - 真实执行销售计划同步、BOM 同步、生产订单同步、研究所同步、零件周期基准重建、snapshot reconcile、BOM 补数消费

4. `scheduler`
   - 负责按 APScheduler 定时规则入队
   - 不直接执行同步，只负责创建后台任务
   - 启停状态落在 `sync_scheduler_state` 表

---

## 2. Docker 启动方式

项目根目录在 `E:\Vibe Coding\SOUL`，Compose 文件在：

- `E:\Vibe Coding\SOUL\docker-compose.yml`

### 2.1 全量启动

```powershell
docker compose up -d db backend worker scheduler frontend
```

### 2.2 仅后端任务系统启动

```powershell
docker compose up -d db backend worker scheduler
```

### 2.3 查看服务状态

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

当前容器名来自 Compose：

- `auto_scheduling_db`
- `auto_scheduling_api`
- `auto_scheduling_worker`
- `auto_scheduling_scheduler`
- `auto_scheduling_frontend`

---

## 3. 本地脚本启动方式

工作目录：

- `E:\Vibe Coding\SOUL\auto-scheduling-system\services\api`

### 3.1 启 API

```powershell
python -m scripts.wait_for_db
alembic upgrade head
python -m scripts.prewarm_snapshots
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.2 启 worker

```powershell
python -m scripts.run_sync_worker
```

### 3.3 启 scheduler

```powershell
python -m scripts.run_sync_scheduler
```

---

## 4. 启动链路与入口脚本

### 4.1 backend

入口脚本：`services/api/docker/backend-entrypoint.sh`

顺序：

1. `python -m scripts.wait_for_db`
2. `alembic upgrade head`
3. `python -m scripts.prewarm_snapshots`
4. `uvicorn app.main:app`

说明：

- `SNAPSHOT_PREWARM_ON_STARTUP=true` 时，启动会尝试 seed snapshot
- `/health` 只表示 API 进程存活，不代表 worker/scheduler 也正常

### 4.2 worker

入口脚本：`services/api/docker/worker-entrypoint.sh`

顺序：

1. `wait_for_db`
2. `alembic upgrade head`
3. `python -m scripts.run_sync_worker`

worker 日志主入口：

- `Background task worker started`
- `Recovered stale background task`
- `Background task execution started`
- `Background task execution succeeded`
- `Background task execution failed`

### 4.3 scheduler

入口脚本：`services/api/docker/scheduler-entrypoint.sh`

顺序：

1. `wait_for_db`
2. `alembic upgrade head`
3. `python -m scripts.run_sync_scheduler`

scheduler 日志主入口：

- `Sync scheduler started`
- `Sync scheduler control state changed`
- `Scheduled task enqueued`
- `Scheduled task skipped because an active task already exists`
- `Sync scheduler stopped`

---

## 5. 关键环境变量

以 `services/api/.env.example` 与 `app/config.py` 为准，当前运维最相关的变量有：

### 5.1 数据库 / 启动

- `DATABASE_URL`
- `WAIT_FOR_DB_ON_STARTUP`
- `WAIT_FOR_DB_TIMEOUT_SECONDS`
- `WAIT_FOR_DB_POLL_INTERVAL_SECONDS`
- `DATABASE_AUTO_CREATE_ALL`

说明：

- 生产/联调默认应以 Alembic 为准，不建议依赖 `DATABASE_AUTO_CREATE_ALL=true`

### 5.2 snapshot

- `SNAPSHOT_PREWARM_ON_STARTUP`
- `SNAPSHOT_REFRESH_BATCH_SIZE`
- `SNAPSHOT_OBSERVABILITY_WARN_REFRESH_AGE_MINUTES`
- `SNAPSHOT_REFRESH_WINDOW_DAYS`

### 5.3 worker / queue

- `SYNC_TASK_DEFAULT_MAX_ATTEMPTS`
- `SYNC_TASK_RETRY_BACKOFF_SECONDS`
- `SYNC_TASK_WORKER_POLL_INTERVAL_SECONDS`
- `SYNC_TASK_WORKER_BATCH_SIZE`
- `SYNC_TASK_CLAIM_TIMEOUT_SECONDS`
- `SYNC_JOB_HEARTBEAT_INTERVAL_SECONDS`
- `SYNC_JOB_TIMEOUT_SECONDS`

### 5.4 scheduler

- `SYNC_SCHEDULER_ENABLED`
- `SYNC_SCHEDULER_TIMEZONE`
- `SYNC_SCHEDULER_CONTROL_POLL_SECONDS`
- `SYNC_SCHEDULER_STALE_SECONDS`
- `SALES_PLAN_SYNC_HOUR / MINUTE`
- `BOM_SYNC_HOUR / MINUTE`
- `PRODUCTION_ORDER_SYNC_HOUR / MINUTE`
- `RESEARCH_SYNC_HOUR / MINUTE`
- `SCHEDULE_SNAPSHOT_RECONCILE_HOUR / MINUTE`
- `BOM_BACKFILL_QUEUE_CONSUME_ENABLED`
- `BOM_BACKFILL_QUEUE_CONSUME_MINUTES`

---

## 6. 关键任务与去重键

### 6.1 scheduler 定时任务

来自 `app/sync_scheduler.py`：

- `sales_plan_sync`
- `bom_sync`
- `production_order_sync`
- `research_sync`
- `schedule_snapshot_reconcile`
- `bom_backfill_queue_consume`

### 6.2 关键 dedupe_key

- `sync_job:sales_plan:guandata`
- `sync_job:bom:sap`
- `sync_job:production_order:feishu`
- `sync_job:research:feishu`
- `scheduler:schedule_snapshot_reconcile`
- `scheduler:bom_backfill_queue_consume`
- `baseline_rebuild:part_cycle`

说明：

- scheduler / manual API 都会复用相同 dedupe_key
- 同类活动任务未结束前，重复入队会被跳过

---

## 7. 关键表与看数顺序

### 7.1 `background_task`

作用：

- 后台任务真实队列表

重点字段：

- `task_type`
- `status`：`pending / running / succeeded / failed`
- `source`
- `reason`
- `dedupe_key`
- `sync_job_log_id`
- `attempt_count / max_attempts`
- `available_at`
- `claimed_at / started_at / finished_at`
- `worker_id`
- `last_error`

适用场景：

- 查任务是否真的入队
- 查 worker 是否认领
- 查是否因为 stale recovery 被回收
- 查失败原因与 failure_kind/stage

### 7.2 `sync_job_log`

作用：

- 同步日志真源

重点字段：

- `job_type`
- `source_system`
- `status`：常见有 `queued / running / completed / completed_with_errors / failed`
- `heartbeat_at`
- `recovered_at`
- `recovery_note`
- `message`
- `success_count / fail_count`

适用场景：

- 查手动同步/定时同步是否在跑
- 查最近失败与结构化进度
- 查 BOM 补数、生产订单、研究所、销售计划等执行结果

### 7.3 `sync_scheduler_state`

作用：

- scheduler 单例状态表

重点字段：

- `enabled`
- `last_state`
- `instance_id`
- `heartbeat_at`
- `updated_by`

适用场景：

- 查 scheduler 是否启用
- 查当前实例是否存活
- 查心跳是否 stale

### 7.4 `order_schedule_snapshot`

作用：

- 排产快照真源

重点字段：

- `order_line_id`
- `schedule_status`
- `warning_level`
- `last_refresh_source`
- `refreshed_at`
- `plant`

适用场景：

- 查 snapshot 是否覆盖订单
- 查 refresh 是否老化
- 查 rebuild / refresh 后是否真正落库

---

## 8. 关键观察接口

### 8.1 API 存活

- `GET /health`

用途：

- 仅确认 backend API 进程可访问

### 8.2 scheduler 状态

- `GET /api/admin/sync/schedule`
- `POST /api/admin/sync/schedule`

用途：

- 看 `enabled / state / timezone / jobs.next_run_time`
- 临时停用或恢复 scheduler

### 8.3 同步观测摘要

- `GET /api/admin/sync/observability`

用途：

- 看运行中任务数
- 看 BOM 补数队列积压
- 看最近同步任务结果

### 8.4 同步日志

- `GET /api/admin/sync-logs`
- `GET /api/admin/sync-logs/{log_id}`

用途：

- 看单任务执行明细
- 看结构化 progress
- 看失败 message / recovery_note / heartbeat

### 8.5 snapshot 观测

- `GET /api/admin/schedule/snapshots/observability`

用途：

- 看 snapshot 总量、覆盖率、刷新老化
- 看 runtime observations

### 8.6 snapshot 手动重建

- `POST /api/admin/schedule/snapshots/rebuild`

用途：

- 规则调整后手工触发 refresh / rebuild

---

## 9. 快照观测口径

来自 `ScheduleSnapshotRefreshService.get_observability_summary()`：

### 9.1 health

- `healthy`
- `warning`
- `critical`

### 9.2 常见告警

- `snapshot_empty`
- `snapshot_coverage_gap`
- `snapshot_refresh_age_high`

### 9.3 runtime_observations

会记录最近运行的：

- `ensure_seeded`
- `refresh_future_window`
- `rebuild_all_open_snapshots`

每条包含：

- `operation`
- `source`
- `reason`
- `started_at / finished_at`
- `duration_ms`
- `success`
- `summary`
- `error`

说明：

- 这是内存级最近观测窗口，不是永久历史表
- 进程重启后会重新累计

---

## 10. 常见排查顺序

### 10.1 手动同步点了没反应

先看：

1. `GET /api/admin/sync-logs`
2. `background_task` 是否生成新记录
3. `dedupe_key` 是否被活动任务占用
4. `worker` 日志是否有 `Background task execution started`

重点判断：

- 有 `sync_job_log` 但没有 `background_task`：入队链路异常
- 有 `background_task(pending)` 长时间不动：worker 没启动或认领异常
- 返回 `noop/running`：通常是去重生效，不一定是故障

### 10.2 scheduler 没有按时触发

先看：

1. `GET /api/admin/sync/schedule`
2. `sync_scheduler_state`
3. `scheduler` 日志

重点判断：

- `enabled=false`：被人为关闭
- `state=stopped` 且 `heartbeat_at` 旧：scheduler 进程不在
- `state=paused`：scheduler 在，但被停用
- 有 `Scheduled task skipped...`：通常是已有活动任务，非 scheduler 崩溃

### 10.3 worker 任务卡住

先看：

1. `background_task.status`
2. `claimed_at / started_at / worker_id`
3. `sync_job_log.heartbeat_at`
4. `worker` 日志

重点判断：

- `running` 且长时间无 heartbeat：看是否超过 `SYNC_TASK_CLAIM_TIMEOUT_SECONDS`
- stale 后 worker 会尝试自动回收
- 回收后会在 `last_error` / `message` 中留下 `action=requeue` 或 `action=fail`

### 10.4 snapshot 看起来没刷新

先看：

1. `GET /api/admin/schedule/snapshots/observability`
2. `order_schedule_snapshot.refreshed_at`
3. `last_refresh_source`
4. backend 日志中的 `Snapshot observation ...`

重点判断：

- 先确认是“没 refresh”还是“refresh 后结果本身没变化”
- 若 `coverage_ratio < 1`，先排查 known order 与 snapshot seed/rebuild

### 10.5 BOM 补数队列积压

先看：

1. `GET /api/admin/sync/observability`
2. `GET /api/admin/sync/bom-backfill-queue`
3. `sync_job_log` 中 BOM 相关日志

重点判断：

- `retry_wait` 持续升高：多为外部接口或空结果重试
- `failed` 上升：看 `failure_kind` 和 `last_error`

---

## 11. 常见日志关键词

### 11.1 启动类

- `Database is ready.`
- `Snapshot prewarm finished and persisted successfully.`
- `Snapshot prewarm skipped because snapshot data already exists.`
- `Background task worker started`
- `Sync scheduler started`

### 11.2 任务执行类

- `Background task enqueued`
- `Background task enqueue deduped`
- `Background task execution started`
- `Background task execution succeeded`
- `Background task execution failed`
- `Recovered stale background task`

### 11.3 调度类

- `Sync scheduler control state changed`
- `Scheduled task enqueued`
- `Scheduled task skipped because an active task already exists`

### 11.4 snapshot 类

- `Snapshot observation operation=...`
- `Initial snapshot fast seed finished`

---

## 12. 推荐故障处理 SOP

### 场景 A：服务整体重启后任务系统异常

1. 先确认 `db / backend / worker / scheduler` 四个容器都在
2. 看 `worker` 和 `scheduler` 是否都输出 started 日志
3. 访问 `/health`
4. 访问 `/api/admin/sync/schedule`
5. 访问 `/api/admin/sync/observability`
6. 若仍异常，再查三张表：
   - `background_task`
   - `sync_job_log`
   - `sync_scheduler_state`

### 场景 B：任务重复触发但没有新日志

1. 先查是否被 `dedupe_key` 去重
2. 再查是否已有 `queued/running` 的 `sync_job_log`
3. 如果确实需要重跑，应先确认旧任务是否已卡死，再决定人工恢复或重触发

### 场景 C：需要临时停 scheduler 排查

1. `POST /api/admin/sync/schedule` 传 `enabled=false`
2. 确认 `GET /api/admin/sync/schedule` 返回 `paused`
3. 排查完成后再恢复 `enabled=true`

### 场景 D：snapshot 明显陈旧

1. 先看 snapshot observability 的 `refresh_age_minutes`
2. 确认是否有 scheduler / worker 异常
3. 必要时手工调用 `/api/admin/schedule/snapshots/rebuild`

---

## 13. 当前限制与注意事项

1. `/health` 只能证明 API 活着，不能替代 worker/scheduler 观测
2. `runtime_observations` 是进程内最近窗口，不是永久审计历史
3. scheduler 是否真的“在工作”，以 `sync_scheduler_state.heartbeat_at` 与 `/api/admin/sync/schedule` 为准
4. 同步是否真的“在执行”，以 `background_task` + `sync_job_log` 联合判断，不只看前端提示
5. backend 启动默认会跑 Alembic；若数据库权限或迁移异常，服务可能起不来

---

## 14. 接手时最少要会的 5 个动作

1. 会用 `docker compose up -d db backend worker scheduler`
2. 会看 `docker logs` 中 worker / scheduler 的 started、failed、deduped、recovered 关键词
3. 会查 `/api/admin/sync/schedule`
4. 会查 `/api/admin/sync/observability` 与 `/api/admin/sync-logs`
5. 会在 `background_task / sync_job_log / sync_scheduler_state / order_schedule_snapshot` 四张表里定位问题
