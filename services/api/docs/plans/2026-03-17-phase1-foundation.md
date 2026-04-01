# Phase 1: Foundation Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the project scaffold, database models, common utilities, and repository layer — everything downstream layers (integration, sync, baseline, scheduler, API) depend on.

**Architecture:** Python FastAPI monolith with layered architecture. SQLAlchemy ORM for PostgreSQL. Repository pattern wraps all SQL. Common utilities provide workday calendar math, Chinese text parsing, and standardized exceptions/responses.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Pydantic v2, pytest, pytest-asyncio

**Spec documents:**
- `自动排产项目资料包/00_AI项目导读.md`
- `自动排产项目资料包/02_SQL/01_核心表结构.sql`
- `自动排产项目资料包/02_SQL/02_排产结果表.sql`
- `自动排产项目资料包/03_设计/01_后端设计.md`

**This is Plan 1 of 4:**
1. **Foundation** (this plan): scaffold, models, repos, common utils
2. **Integration + Sync**: external API clients, data sync services
3. **Baseline + Scheduler**: cycle baselines, scheduling engine
4. **API Layer**: REST endpoints, export, admin

---

## File Structure

```
auto-scheduling-system/services/api/
├── pyproject.toml
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entry
│   ├── config.py                        # Pydantic Settings
│   ├── database.py                      # async engine + session factory
│   ├── common/
│   │   ├── __init__.py
│   │   ├── enums.py                     # ScheduleStatus, WarningLevel, OrderType, etc.
│   │   ├── exceptions.py               # BizException, error codes
│   │   ├── response.py                 # unified ApiResponse model
│   │   ├── calendar_utils.py           # workday add/subtract using DB calendar
│   │   └── text_parse_utils.py         # extract Chinese prefix for assembly names
│   ├── models/
│   │   ├── __init__.py                  # re-exports all models
│   │   ├── base.py                      # DeclarativeBase + mixins
│   │   ├── sales_plan.py               # SalesPlanOrderLineSrc
│   │   ├── bom_relation.py             # BomRelationSrc
│   │   ├── production_order.py         # ProductionOrderHistorySrc
│   │   ├── machine_cycle_history.py    # MachineCycleHistorySrc
│   │   ├── machine_cycle_baseline.py   # MachineCycleBaseline
│   │   ├── part_cycle_baseline.py      # PartCycleBaseline
│   │   ├── assembly_time.py            # AssemblyTimeBaseline
│   │   ├── work_calendar.py            # WorkCalendar
│   │   ├── sync_job_log.py             # SyncJobLog
│   │   ├── data_issue.py               # DataIssueRecord
│   │   ├── machine_schedule_result.py  # MachineScheduleResult
│   │   └── part_schedule_result.py     # PartScheduleResult
│   └── repository/
│       ├── __init__.py
│       ├── base.py                      # BaseRepository with CRUD helpers
│       ├── sales_plan_repo.py
│       ├── bom_relation_repo.py
│       ├── production_order_repo.py
│       ├── machine_cycle_history_repo.py
│       ├── machine_cycle_baseline_repo.py
│       ├── part_cycle_baseline_repo.py
│       ├── assembly_time_repo.py
│       ├── work_calendar_repo.py
│       ├── sync_job_log_repo.py
│       ├── data_issue_repo.py
│       ├── machine_schedule_result_repo.py
│       └── part_schedule_result_repo.py
├── tests/
│   ├── conftest.py                      # test DB setup, fixtures
│   ├── test_common/
│   │   ├── test_enums.py
│   │   ├── test_exceptions.py
│   │   ├── test_calendar_utils.py
│   │   └── test_text_parse_utils.py
│   └── test_repository/
│       ├── test_work_calendar_repo.py
│       ├── test_sales_plan_repo.py
│       ├── test_machine_schedule_result_repo.py
│       └── test_data_issue_repo.py
└── scripts/
    └── init_work_calendar.py            # Initialize 2026-2027 calendar
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `auto-scheduling-system/services/api/pyproject.toml`
- Create: `auto-scheduling-system/services/api/.env.example`
- Create: `auto-scheduling-system/services/api/app/__init__.py`
- Create: `auto-scheduling-system/services/api/app/config.py`
- Create: `auto-scheduling-system/services/api/app/database.py`
- Create: `auto-scheduling-system/services/api/app/main.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "auto-scheduling"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "openpyxl>=3.1.0",
    "alembic>=1.13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "aiosqlite>=0.20.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

- [ ] **Step 2: Create .env.example**

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/auto_scheduling
GUANDATA_BASE_URL=<GUANDATA_BASE_URL>
GUANDATA_DOMAIN=<GUANDATA_DOMAIN>
GUANDATA_LOGIN_ID=<GUANDATA_LOGIN_ID>
GUANDATA_PASSWORD=<GUANDATA_PASSWORD>
GUANDATA_DS_ID=<GUANDATA_DS_ID>
SAP_BOM_BASE_URL=<SAP_BOM_BASE_URL>
FEISHU_APP_ID=<FEISHU_APP_ID>
FEISHU_APP_SECRET=<FEISHU_APP_SECRET>
FEISHU_PRODUCTION_APP_TOKEN=<FEISHU_PRODUCTION_ORDER_APP_TOKEN>
FEISHU_PRODUCTION_TABLE_ID=<FEISHU_PRODUCTION_ORDER_TABLE_ID>
FEISHU_RESEARCH_APP_TOKEN=<FEISHU_RESEARCH_APP_TOKEN>
FEISHU_RESEARCH_TABLE_ID=<FEISHU_RESEARCH_TABLE_ID>
SCHEDULE_TRIGGER_ADVANCE_DAYS=28
```

- [ ] **Step 3: Create config.py**

```python
# auto-scheduling-system/services/api/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/auto_scheduling"

    # 观远
    guandata_base_url: str = ""
    guandata_domain: str = ""
    guandata_login_id: str = ""
    guandata_password: str = ""
    guandata_ds_id: str = ""

    # SAP
    sap_bom_base_url: str = ""

    # 飞书
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_production_app_token: str = ""
    feishu_production_table_id: str = ""
    feishu_research_app_token: str = ""
    feishu_research_table_id: str = ""

    # 排产参数
    schedule_trigger_advance_days: int = 28  # 排产触发提前量（自然日）
    sync_window_days: int = 15  # 观远同步窗口（天）

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 4: Create database.py**

```python
# auto-scheduling-system/services/api/app/database.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 5: Create main.py**

```python
# auto-scheduling-system/services/api/app/main.py
from fastapi import FastAPI

app = FastAPI(title="自动排产工具", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create app/__init__.py**

```python
# auto-scheduling-system/services/api/app/__init__.py
```

- [ ] **Step 7: Verify scaffold starts**

Run: `cd auto-scheduling-system/services/api && pip install -e ".[dev]" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
Then: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`
Kill the server after verification.

- [ ] **Step 8: Commit**

```bash
cd auto-scheduling-system/services/api
git add pyproject.toml .env.example app/__init__.py app/config.py app/database.py app/main.py
git commit -m "feat: project scaffold with FastAPI, config, database setup"
```

---

### Task 2: Common — Enums, Exceptions, Response

**Files:**
- Create: `auto-scheduling-system/services/api/app/common/__init__.py`
- Create: `auto-scheduling-system/services/api/app/common/enums.py`
- Create: `auto-scheduling-system/services/api/app/common/exceptions.py`
- Create: `auto-scheduling-system/services/api/app/common/response.py`
- Test: `auto-scheduling-system/services/api/tests/test_common/test_enums.py`
- Test: `auto-scheduling-system/services/api/tests/test_common/test_exceptions.py`

- [ ] **Step 1: Write enums tests**

```python
# tests/test_common/test_enums.py
from app.common.enums import ScheduleStatus, WarningLevel, OrderType, IssueStatus


def test_schedule_status_values():
    assert ScheduleStatus.PENDING_DRAWING == "pending_drawing"
    assert ScheduleStatus.PENDING_TRIGGER == "pending_trigger"
    assert ScheduleStatus.SCHEDULABLE == "schedulable"
    assert ScheduleStatus.SCHEDULED == "scheduled"


def test_warning_level_values():
    assert WarningLevel.NORMAL == "normal"
    assert WarningLevel.ABNORMAL == "abnormal"


def test_order_type_values():
    assert OrderType.REGULAR.value == "1"
    assert OrderType.OPTIONAL.value == "2"
    assert OrderType.CUSTOM.value == "3"


def test_issue_status_values():
    assert IssueStatus.OPEN == "open"
    assert IssueStatus.RESOLVED == "resolved"
    assert IssueStatus.IGNORED == "ignored"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_enums.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement enums**

```python
# app/common/__init__.py
```

```python
# app/common/enums.py
from enum import StrEnum


class ScheduleStatus(StrEnum):
    PENDING_DRAWING = "pending_drawing"
    PENDING_TRIGGER = "pending_trigger"
    SCHEDULABLE = "schedulable"
    SCHEDULED = "scheduled"


class WarningLevel(StrEnum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"


class OrderType(StrEnum):
    REGULAR = "1"
    OPTIONAL = "2"
    CUSTOM = "3"


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_enums.py -v`
Expected: PASS

- [ ] **Step 5: Write exceptions tests**

```python
# tests/test_common/test_exceptions.py
from app.common.exceptions import BizException, ErrorCode


def test_error_codes():
    assert ErrorCode.PARAM_ERROR == 4001
    assert ErrorCode.NOT_FOUND == 4002
    assert ErrorCode.BIZ_VALIDATION_FAILED == 4003
    assert ErrorCode.EXTERNAL_API_FAILED == 5001
    assert ErrorCode.DB_ERROR == 5002
    assert ErrorCode.SCHEDULE_CALC_FAILED == 5003
    assert ErrorCode.EXPORT_FAILED == 5004


def test_biz_exception():
    ex = BizException(ErrorCode.NOT_FOUND, "记录不存在")
    assert ex.code == 4002
    assert ex.message == "记录不存在"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_exceptions.py -v`
Expected: FAIL

- [ ] **Step 7: Implement exceptions and response**

```python
# app/common/exceptions.py
from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 0
    PARAM_ERROR = 4001
    NOT_FOUND = 4002
    BIZ_VALIDATION_FAILED = 4003
    EXTERNAL_API_FAILED = 5001
    DB_ERROR = 5002
    SCHEDULE_CALC_FAILED = 5003
    EXPORT_FAILED = 5004


class BizException(Exception):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
```

```python
# app/common/response.py
from typing import Any
from pydantic import BaseModel

from app.common.exceptions import ErrorCode


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None) -> "ApiResponse":
        return cls(code=ErrorCode.SUCCESS, message="success", data=data)

    @classmethod
    def fail(cls, code: ErrorCode, message: str) -> "ApiResponse":
        return cls(code=code, message=message, data=None)
```

- [ ] **Step 8: Run all common tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/ -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add app/common/ tests/test_common/
git commit -m "feat: add enums, exceptions, and API response model"
```

---

### Task 3: Common — Calendar Utils (Workday Math)

This is critical business logic. All scheduling uses workday calculations.

**Files:**
- Create: `auto-scheduling-system/services/api/app/common/calendar_utils.py`
- Test: `auto-scheduling-system/services/api/tests/test_common/test_calendar_utils.py`

**Key rules:**
- `subtract_workdays(date, n, calendar)` → go back n workdays from date
- `add_workdays(date, n, calendar)` → go forward n workdays from date
- Calendar is a `dict[date, bool]` where `True` = workday
- If a date is not in calendar, treat weekdays (Mon-Fri) as workdays

- [ ] **Step 1: Write failing tests for workday subtraction**

```python
# tests/test_common/test_calendar_utils.py
from datetime import date
from app.common.calendar_utils import subtract_workdays, add_workdays


def _make_calendar() -> dict[date, bool]:
    """Build a simple calendar: Mon-Fri workday, Sat-Sun off.
    2026-04 starts on Wednesday.
    Override: 2026-04-05 (Sun) is a workday (调休), 2026-04-06 (Mon) is off (清明).
    """
    cal = {}
    d = date(2026, 3, 1)
    end = date(2026, 5, 1)
    while d < end:
        cal[d] = d.weekday() < 5  # Mon-Fri
        d += __import__("datetime").timedelta(days=1)
    cal[date(2026, 4, 5)] = True   # Sunday override: workday
    cal[date(2026, 4, 6)] = False  # Monday override: holiday
    return cal


def test_subtract_workdays_no_weekends():
    cal = _make_calendar()
    # 2026-04-10 (Fri) - 3 workdays = 2026-04-07 (Tue)
    # 4/6 is holiday, so skip it. 4/5 (Sun) is workday override.
    # From 4/10: step back → 4/9(Thu,work) → 4/8(Wed,work) → 4/7(Tue,work)
    result = subtract_workdays(date(2026, 4, 10), 3, cal)
    assert result == date(2026, 4, 7)


def test_subtract_workdays_across_holiday():
    cal = _make_calendar()
    # 2026-04-10 (Fri) - 5 workdays
    # 4/9(Thu) 4/8(Wed) 4/7(Tue) 4/5(Sun=work) 4/3(Fri)
    # Skip 4/6(Mon=holiday) and 4/4(Sat=off)
    result = subtract_workdays(date(2026, 4, 10), 5, cal)
    assert result == date(2026, 4, 3)


def test_subtract_zero_workdays():
    cal = _make_calendar()
    result = subtract_workdays(date(2026, 4, 10), 0, cal)
    assert result == date(2026, 4, 10)


def test_add_workdays_basic():
    cal = _make_calendar()
    # 2026-04-01 (Wed) + 3 workdays = 2026-04-06? No, 4/6 is holiday.
    # 4/2(Thu) 4/3(Fri) 4/5(Sun=work) → result is 4/5
    # Skip 4/4(Sat=off) and 4/6(Mon=holiday)
    result = add_workdays(date(2026, 4, 1), 3, cal)
    assert result == date(2026, 4, 5)


def test_add_zero_workdays():
    cal = _make_calendar()
    result = add_workdays(date(2026, 4, 1), 0, cal)
    assert result == date(2026, 4, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_calendar_utils.py -v`
Expected: FAIL

- [ ] **Step 3: Implement calendar_utils**

```python
# app/common/calendar_utils.py
from datetime import date, timedelta


def _is_workday(d: date, calendar: dict[date, bool]) -> bool:
    if d in calendar:
        return calendar[d]
    return d.weekday() < 5  # fallback: Mon-Fri


def subtract_workdays(from_date: date, n: int, calendar: dict[date, bool]) -> date:
    """从 from_date 往前减 n 个工作日。"""
    if n <= 0:
        return from_date
    current = from_date
    count = 0
    while count < n:
        current -= timedelta(days=1)
        if _is_workday(current, calendar):
            count += 1
    return current


def add_workdays(from_date: date, n: int, calendar: dict[date, bool]) -> date:
    """从 from_date 往后加 n 个工作日。"""
    if n <= 0:
        return from_date
    current = from_date
    count = 0
    while count < n:
        current += timedelta(days=1)
        if _is_workday(current, calendar):
            count += 1
    return current
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_calendar_utils.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/common/calendar_utils.py tests/test_common/test_calendar_utils.py
git commit -m "feat: add workday calendar utils (subtract/add workdays)"
```

---

### Task 4: Common — Text Parse Utils

Used for extracting Chinese prefix from BOM component descriptions to identify assembly names.

**Files:**
- Create: `auto-scheduling-system/services/api/app/common/text_parse_utils.py`
- Test: `auto-scheduling-system/services/api/tests/test_common/test_text_parse_utils.py`

**Rules:**
- Extract leading Chinese characters from a string as the assembly name
- Exclude assemblies matching: 润滑, 附件, 油漆, 标牌, 包装

- [ ] **Step 1: Write failing tests**

```python
# tests/test_common/test_text_parse_utils.py
from app.common.text_parse_utils import extract_chinese_prefix, is_excluded_assembly

def test_extract_chinese_prefix_normal():
    assert extract_chinese_prefix("机身MC1-80.1(253464)") == "机身"

def test_extract_chinese_prefix_multi_char():
    assert extract_chinese_prefix("空气管路总成 ABC-123") == "空气管路总成"

def test_extract_chinese_prefix_only_chinese():
    assert extract_chinese_prefix("传动") == "传动"

def test_extract_chinese_prefix_no_chinese():
    assert extract_chinese_prefix("ABC-123") == ""

def test_extract_chinese_prefix_empty():
    assert extract_chinese_prefix("") == ""

def test_is_excluded_assembly():
    assert is_excluded_assembly("润滑系统") is True
    assert is_excluded_assembly("附件") is True
    assert is_excluded_assembly("油漆") is True
    assert is_excluded_assembly("标牌") is True
    assert is_excluded_assembly("包装") is True
    assert is_excluded_assembly("机身") is False
    assert is_excluded_assembly("传动") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_text_parse_utils.py -v`
Expected: FAIL

- [ ] **Step 3: Implement text_parse_utils**

```python
# app/common/text_parse_utils.py
import re

_CHINESE_PREFIX_RE = re.compile(r"^[\u4e00-\u9fff]+")
_EXCLUDED_PREFIXES = {"润滑", "附件", "油漆", "标牌", "包装"}


def extract_chinese_prefix(text: str) -> str:
    """取字符串开头连续中文字符作为部装名。"""
    if not text:
        return ""
    m = _CHINESE_PREFIX_RE.match(text)
    return m.group(0) if m else ""


def is_excluded_assembly(assembly_name: str) -> bool:
    """判断部装名是否属于排除项。"""
    return any(assembly_name.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_common/test_text_parse_utils.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/common/text_parse_utils.py tests/test_common/test_text_parse_utils.py
git commit -m "feat: add text parse utils for assembly name extraction"
```

---

### Task 5: SQLAlchemy Models — Base + Source Tables (6 models)

**Files:**
- Create: `auto-scheduling-system/services/api/app/models/__init__.py`
- Create: `auto-scheduling-system/services/api/app/models/base.py`
- Create: `auto-scheduling-system/services/api/app/models/sales_plan.py`
- Create: `auto-scheduling-system/services/api/app/models/bom_relation.py`
- Create: `auto-scheduling-system/services/api/app/models/production_order.py`
- Create: `auto-scheduling-system/services/api/app/models/machine_cycle_history.py`
- Create: `auto-scheduling-system/services/api/app/models/work_calendar.py`
- Create: `auto-scheduling-system/services/api/app/models/sync_job_log.py`

Reference: `02_SQL/01_核心表结构.sql`

- [ ] **Step 1: Create base model with timestamp mixin**

```python
# app/models/base.py
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)
```

- [ ] **Step 2: Create SalesPlanOrderLineSrc model**

```python
# app/models/sales_plan.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalesPlanOrderLineSrc(TimestampMixin, Base):
    __tablename__ = "sales_plan_order_line_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    crm_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    custom_no: Mapped[Optional[str]] = mapped_column(String(100))
    sales_person_name: Mapped[Optional[str]] = mapped_column(String(100))
    sales_person_job_no: Mapped[Optional[str]] = mapped_column(String(50))
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    product_model: Mapped[Optional[str]] = mapped_column(String(100))
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    contract_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    line_total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    confirmed_delivery_date: Mapped[Optional[datetime]] = mapped_column()
    delivery_date: Mapped[Optional[datetime]] = mapped_column()
    order_type: Mapped[Optional[str]] = mapped_column(String(50), comment="订单类型枚举：1=常规, 2=选配, 3=定制")
    is_automation_project: Mapped[Optional[bool]] = mapped_column(Boolean)
    business_group: Mapped[Optional[str]] = mapped_column(String(100))
    order_date: Mapped[Optional[datetime]] = mapped_column()
    sales_branch_company: Mapped[Optional[str]] = mapped_column(String(100))
    sales_sub_branch: Mapped[Optional[str]] = mapped_column(String(100))
    oa_flow_id: Mapped[Optional[str]] = mapped_column(String(100))
    operator_name: Mapped[Optional[str]] = mapped_column(String(100))
    operator_job_no: Mapped[Optional[str]] = mapped_column(String(50))
    sap_code: Mapped[Optional[str]] = mapped_column(String(100))
    sap_line_no: Mapped[Optional[str]] = mapped_column(String(100))
    delivery_plant: Mapped[Optional[str]] = mapped_column(String(50))
    custom_requirement: Mapped[Optional[str]] = mapped_column(Text)
    review_comment: Mapped[Optional[str]] = mapped_column(Text)
    drawing_released: Mapped[bool] = mapped_column(Boolean, default=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    detail_id: Mapped[Optional[str]] = mapped_column(String(100))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))

    __table_args__ = (
        UniqueConstraint("sap_code", "sap_line_no", name="uk_sales_plan_order_line_src"),
        Index("idx_sales_plan_detail_id", "detail_id"),
        Index("idx_sales_plan_order_no", "order_no"),
        Index("idx_sales_plan_material_no", "material_no"),
        Index("idx_sales_plan_confirmed_delivery_date", "confirmed_delivery_date"),
    )
```

- [ ] **Step 3: Create BomRelationSrc model**

```python
# app/models/bom_relation.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BomRelationSrc(TimestampMixin, Base):
    __tablename__ = "bom_relation_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_material_no: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    plant: Mapped[Optional[str]] = mapped_column(String(50))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    bom_component_no: Mapped[Optional[str]] = mapped_column(String(100))
    bom_component_desc: Mapped[Optional[str]] = mapped_column(String(255))
    part_type: Mapped[Optional[str]] = mapped_column(String(50))
    component_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    bom_level: Mapped[Optional[int]] = mapped_column(Integer)
    is_top_level: Mapped[bool] = mapped_column(Boolean, default=False)
    is_self_made: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_time: Mapped[Optional[datetime]] = mapped_column()

    __table_args__ = (
        Index("idx_bom_machine_material_no", "machine_material_no"),
        Index("idx_bom_component_no", "bom_component_no"),
        Index("idx_bom_part_type", "part_type"),
    )
```

- [ ] **Step 4: Create ProductionOrderHistorySrc model**

```python
# app/models/production_order.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProductionOrderHistorySrc(TimestampMixin, Base):
    __tablename__ = "production_order_history_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    production_order_no: Mapped[str] = mapped_column(String(100), nullable=False)
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    machine_model: Mapped[Optional[str]] = mapped_column(String(100))
    plant: Mapped[Optional[str]] = mapped_column(String(50))
    processing_dept: Mapped[Optional[str]] = mapped_column(String(100))
    start_time_actual: Mapped[Optional[datetime]] = mapped_column()
    finish_time_actual: Mapped[Optional[datetime]] = mapped_column()
    production_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    order_status: Mapped[Optional[str]] = mapped_column(String(50))
    sales_order_no: Mapped[Optional[str]] = mapped_column(String(100))
    created_time_src: Mapped[Optional[datetime]] = mapped_column()
    last_modified_time_src: Mapped[Optional[datetime]] = mapped_column()

    __table_args__ = (
        UniqueConstraint("production_order_no", name="uk_production_order_history_src"),
        Index("idx_prod_order_material_no", "material_no"),
        Index("idx_prod_order_machine_model", "machine_model"),
        Index("idx_prod_order_last_modified", "last_modified_time_src"),
    )
```

- [ ] **Step 5: Create MachineCycleHistorySrc model**

```python
# app/models/machine_cycle_history.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MachineCycleHistorySrc(TimestampMixin, Base):
    __tablename__ = "machine_cycle_history_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    detail_id: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_material_no: Mapped[Optional[str]] = mapped_column(String(100))
    machine_model: Mapped[str] = mapped_column(String(100), nullable=False)
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    inspection_date: Mapped[Optional[datetime]] = mapped_column()
    custom_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))
    business_group: Mapped[Optional[str]] = mapped_column(String(100))
    order_type: Mapped[Optional[str]] = mapped_column(String(50))
    cycle_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    __table_args__ = (
        UniqueConstraint("detail_id", name="uk_machine_cycle_history_detail_id"),
        Index("idx_mch_machine_model", "machine_model"),
        Index("idx_mch_machine_material_no", "machine_material_no"),
        Index("idx_mch_order_no", "order_no"),
    )
```

- [ ] **Step 6: Create WorkCalendar and SyncJobLog models**

```python
# app/models/work_calendar.py
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WorkCalendar(TimestampMixin, Base):
    __tablename__ = "work_calendar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    calendar_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_workday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("calendar_date", name="uk_work_calendar"),
    )
```

```python
# app/models/sync_job_log.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SyncJobLog(Base):
    __tablename__ = "sync_job_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column()
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_sync_job_type", "job_type"),
        Index("idx_sync_source_system", "source_system"),
        Index("idx_sync_start_time", "start_time"),
    )
```

- [ ] **Step 7: Create models/__init__.py exporting all models**

```python
# app/models/__init__.py
from app.models.base import Base
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.bom_relation import BomRelationSrc
from app.models.production_order import ProductionOrderHistorySrc
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.models.work_calendar import WorkCalendar
from app.models.sync_job_log import SyncJobLog

__all__ = [
    "Base",
    "SalesPlanOrderLineSrc",
    "BomRelationSrc",
    "ProductionOrderHistorySrc",
    "MachineCycleHistorySrc",
    "WorkCalendar",
    "SyncJobLog",
]
```

- [ ] **Step 8: Verify models can be imported**

Run: `cd auto-scheduling-system/services/api && python -c "from app.models import Base, SalesPlanOrderLineSrc, BomRelationSrc, ProductionOrderHistorySrc, MachineCycleHistorySrc, WorkCalendar, SyncJobLog; print('OK')" `
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add app/models/
git commit -m "feat: add SQLAlchemy models for 6 source tables"
```

---

### Task 6: SQLAlchemy Models — Baseline + Result + Issue Tables (6 models)

**Files:**
- Create: `auto-scheduling-system/services/api/app/models/machine_cycle_baseline.py`
- Create: `auto-scheduling-system/services/api/app/models/part_cycle_baseline.py`
- Create: `auto-scheduling-system/services/api/app/models/assembly_time.py`
- Create: `auto-scheduling-system/services/api/app/models/data_issue.py`
- Create: `auto-scheduling-system/services/api/app/models/machine_schedule_result.py`
- Create: `auto-scheduling-system/services/api/app/models/part_schedule_result.py`
- Modify: `auto-scheduling-system/services/api/app/models/__init__.py`

Reference: `02_SQL/01_核心表结构.sql`, `02_SQL/02_排产结果表.sql`

- [ ] **Step 1: Create MachineCycleBaseline model**

```python
# app/models/machine_cycle_baseline.py
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MachineCycleBaseline(TimestampMixin, Base):
    __tablename__ = "machine_cycle_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    machine_model: Mapped[str] = mapped_column(String(100), nullable=False)
    order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cycle_days_median: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_mcb_machine_model", "machine_model"),
        Index("idx_mcb_product_series", "product_series"),
    )
```

- [ ] **Step 2: Create PartCycleBaseline model**

```python
# app/models/part_cycle_baseline.py
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PartCycleBaseline(TimestampMixin, Base):
    __tablename__ = "part_cycle_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_no: Mapped[str] = mapped_column(String(100), nullable=False)
    material_desc: Mapped[str] = mapped_column(String(255), nullable=False)
    core_part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_model: Mapped[Optional[str]] = mapped_column(String(100))
    ref_batch_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cycle_days: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cycle_days: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cycle_source: Mapped[Optional[str]] = mapped_column(String(50))
    match_rule: Mapped[Optional[str]] = mapped_column(String(100))
    confidence_level: Mapped[Optional[str]] = mapped_column(String(50))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_pcb_material_no", "material_no"),
        Index("idx_pcb_core_part_name", "core_part_name"),
        Index("idx_pcb_machine_model", "machine_model"),
    )
```

- [ ] **Step 3: Create AssemblyTimeBaseline model**

```python
# app/models/assembly_time.py
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssemblyTimeBaseline(TimestampMixin, Base):
    __tablename__ = "assembly_time_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_model: Mapped[str] = mapped_column(String(100), nullable=False)
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    assembly_name: Mapped[str] = mapped_column(String(100), nullable=False)
    assembly_time_days: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_final_assembly: Mapped[bool] = mapped_column(Boolean, default=False)
    production_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_atb_machine_model", "machine_model"),
        Index("idx_atb_product_series", "product_series"),
        Index("idx_atb_assembly_name", "assembly_name"),
    )
```

- [ ] **Step 4: Create DataIssueRecord model**

```python
# app/models/data_issue.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DataIssueRecord(TimestampMixin, Base):
    __tablename__ = "data_issue_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_level: Mapped[Optional[str]] = mapped_column(String(50))
    source_system: Mapped[Optional[str]] = mapped_column(String(50))
    biz_key: Mapped[Optional[str]] = mapped_column(String(200))
    issue_title: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_detail: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    handler: Mapped[Optional[str]] = mapped_column(String(100))
    handled_at: Mapped[Optional[datetime]] = mapped_column()
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_issue_type", "issue_type"),
        Index("idx_issue_status", "status"),
        Index("idx_issue_biz_key", "biz_key"),
    )
```

- [ ] **Step 5: Create MachineScheduleResult model**

```python
# app/models/machine_schedule_result.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import String, Numeric, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MachineScheduleResult(TimestampMixin, Base):
    __tablename__ = "machine_schedule_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_line_id: Mapped[int] = mapped_column(nullable=False)
    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    product_model: Mapped[Optional[str]] = mapped_column(String(100))
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))
    sap_code: Mapped[Optional[str]] = mapped_column(String(100))
    sap_line_no: Mapped[Optional[str]] = mapped_column(String(100))
    delivery_plant: Mapped[Optional[str]] = mapped_column(String(50))
    confirmed_delivery_date: Mapped[Optional[datetime]] = mapped_column()
    drawing_released: Mapped[bool] = mapped_column(Boolean, default=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    schedule_date: Mapped[Optional[datetime]] = mapped_column()
    trigger_date: Mapped[Optional[datetime]] = mapped_column()
    machine_cycle_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    machine_assembly_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    planned_start_date: Mapped[Optional[datetime]] = mapped_column()
    planned_end_date: Mapped[Optional[datetime]] = mapped_column()
    warning_level: Mapped[Optional[str]] = mapped_column(String(50))
    schedule_status: Mapped[Optional[str]] = mapped_column(String(50),
        comment="pending_drawing/pending_trigger/schedulable/scheduled")
    default_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    issue_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    run_batch_no: Mapped[Optional[str]] = mapped_column(String(100))
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("order_line_id", name="uk_msr_order_line_id"),
        Index("idx_msr_contract_no", "contract_no"),
        Index("idx_msr_order_no", "order_no"),
        Index("idx_msr_confirmed_delivery_date", "confirmed_delivery_date"),
        Index("idx_msr_schedule_date", "schedule_date"),
        Index("idx_msr_schedule_status", "schedule_status"),
    )
```

- [ ] **Step 6: Create PartScheduleResult model**

```python
# app/models/part_schedule_result.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import String, Numeric, Boolean, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PartScheduleResult(TimestampMixin, Base):
    __tablename__ = "part_schedule_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_line_id: Mapped[int] = mapped_column(nullable=False)
    machine_schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("machine_schedule_result.id"))
    assembly_name: Mapped[str] = mapped_column(String(100), nullable=False)
    production_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    assembly_time_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    assembly_is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    key_part_material_no: Mapped[Optional[str]] = mapped_column(String(100))
    key_part_name: Mapped[Optional[str]] = mapped_column(String(255))
    key_part_raw_material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    key_part_cycle_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    key_part_is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    cycle_match_rule: Mapped[Optional[str]] = mapped_column(String(100))
    planned_start_date: Mapped[Optional[datetime]] = mapped_column()
    planned_end_date: Mapped[Optional[datetime]] = mapped_column()
    warning_level: Mapped[Optional[str]] = mapped_column(String(50))
    default_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    issue_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    run_batch_no: Mapped[Optional[str]] = mapped_column(String(100))
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_psr_order_line_id", "order_line_id"),
        Index("idx_psr_machine_schedule_id", "machine_schedule_id"),
        Index("idx_psr_assembly_name", "assembly_name"),
        Index("idx_psr_production_sequence", "production_sequence"),
    )
```

- [ ] **Step 7: Update models/__init__.py with all 12 models**

```python
# app/models/__init__.py
from app.models.base import Base
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.bom_relation import BomRelationSrc
from app.models.production_order import ProductionOrderHistorySrc
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline
from app.models.work_calendar import WorkCalendar
from app.models.sync_job_log import SyncJobLog
from app.models.data_issue import DataIssueRecord
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_schedule_result import PartScheduleResult

__all__ = [
    "Base",
    "SalesPlanOrderLineSrc",
    "BomRelationSrc",
    "ProductionOrderHistorySrc",
    "MachineCycleHistorySrc",
    "MachineCycleBaseline",
    "PartCycleBaseline",
    "AssemblyTimeBaseline",
    "WorkCalendar",
    "SyncJobLog",
    "DataIssueRecord",
    "MachineScheduleResult",
    "PartScheduleResult",
]
```

- [ ] **Step 8: Verify all models import cleanly**

Run: `cd auto-scheduling-system/services/api && python -c "from app.models import *; print(f'{len(__all__)} models loaded OK')" `
Expected: `13 models loaded OK`

- [ ] **Step 9: Commit**

```bash
git add app/models/
git commit -m "feat: add SQLAlchemy models for baseline, result, and issue tables"
```

---

### Task 7: Test Infrastructure — conftest with In-Memory SQLite

**Files:**
- Create: `auto-scheduling-system/services/api/tests/__init__.py`
- Create: `auto-scheduling-system/services/api/tests/conftest.py`
- Create: `auto-scheduling-system/services/api/tests/test_common/__init__.py`
- Create: `auto-scheduling-system/services/api/tests/test_repository/__init__.py`

- [ ] **Step 1: Create conftest.py with async SQLite test DB**

Note: Models use PostgreSQL `JSONB` type. For SQLite compatibility in tests, we register
a type adapter so `JSONB` columns fall back to `JSON` (stored as TEXT in SQLite).

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy import event, JSON
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


@pytest_asyncio.fixture
async def db_session():
    """Provide an async session backed by in-memory SQLite for testing.
    JSONB columns are rendered as JSON (TEXT) for SQLite compatibility.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Make JSONB work with SQLite by treating it as plain JSON
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        pass  # placeholder for any SQLite-specific setup

    async with engine.begin() as conn:
        # Replace JSONB with JSON in the metadata for SQLite
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
```

```python
# tests/__init__.py
```

```python
# tests/test_common/__init__.py
```

```python
# tests/test_repository/__init__.py
```

- [ ] **Step 2: Write a smoke test to verify DB setup**

```python
# tests/test_repository/test_smoke.py
import pytest
from app.models import WorkCalendar
from datetime import date

@pytest.mark.asyncio
async def test_db_session_works(db_session):
    cal = WorkCalendar(calendar_date=date(2026, 1, 1), is_workday=False, remark="元旦")
    db_session.add(cal)
    await db_session.commit()
    await db_session.refresh(cal)
    assert cal.id is not None
    assert cal.calendar_date == date(2026, 1, 1)
    assert cal.is_workday is False
```

- [ ] **Step 3: Run smoke test**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/test_smoke.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "feat: add test infrastructure with async SQLite fixture"
```

---

### Task 8: Repository — Base Repository

**Files:**
- Create: `auto-scheduling-system/services/api/app/repository/__init__.py`
- Create: `auto-scheduling-system/services/api/app/repository/base.py`

- [ ] **Step 1: Create base repository with common CRUD methods**

```python
# app/repository/__init__.py
```

```python
# app/repository/base.py
from typing import TypeVar, Generic, Type, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model_class: Type[ModelT]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model_class, id_)

    async def list_all(self) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model_class))
        return result.scalars().all()

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_all(self, entities: list[ModelT]) -> list[ModelT]:
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model_class)
        )
        return result.scalar_one()

    async def commit(self) -> None:
        await self.session.commit()
```

- [ ] **Step 2: Verify import**

Run: `cd auto-scheduling-system/services/api && python -c "from app.repository.base import BaseRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/repository/
git commit -m "feat: add base repository with generic CRUD methods"
```

---

### Task 9: Repository — Work Calendar Repo

The most important repo for business logic — calendar lookups for workday calculations.

**Files:**
- Create: `auto-scheduling-system/services/api/app/repository/work_calendar_repo.py`
- Test: `auto-scheduling-system/services/api/tests/test_repository/test_work_calendar_repo.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_repository/test_work_calendar_repo.py
import pytest
from datetime import date
from app.models import WorkCalendar
from app.repository.work_calendar_repo import WorkCalendarRepo


@pytest.mark.asyncio
async def test_get_calendar_map(db_session):
    db_session.add_all([
        WorkCalendar(calendar_date=date(2026, 4, 1), is_workday=True),
        WorkCalendar(calendar_date=date(2026, 4, 4), is_workday=False, remark="Sat"),
        WorkCalendar(calendar_date=date(2026, 4, 5), is_workday=True, remark="调休"),
    ])
    await db_session.commit()

    repo = WorkCalendarRepo(db_session)
    cal_map = await repo.get_calendar_map(date(2026, 4, 1), date(2026, 4, 5))
    assert cal_map[date(2026, 4, 1)] is True
    assert cal_map[date(2026, 4, 4)] is False
    assert cal_map[date(2026, 4, 5)] is True


@pytest.mark.asyncio
async def test_upsert_calendar(db_session):
    repo = WorkCalendarRepo(db_session)
    await repo.upsert(date(2026, 1, 1), is_workday=False, remark="元旦")
    await db_session.commit()

    cal_map = await repo.get_calendar_map(date(2026, 1, 1), date(2026, 1, 1))
    assert cal_map[date(2026, 1, 1)] is False

    # upsert again — change to workday
    await repo.upsert(date(2026, 1, 1), is_workday=True, remark="调休")
    await db_session.commit()

    cal_map = await repo.get_calendar_map(date(2026, 1, 1), date(2026, 1, 1))
    assert cal_map[date(2026, 1, 1)] is True


@pytest.mark.asyncio
async def test_get_month(db_session):
    db_session.add_all([
        WorkCalendar(calendar_date=date(2026, 3, 1), is_workday=True),
        WorkCalendar(calendar_date=date(2026, 3, 15), is_workday=True),
        WorkCalendar(calendar_date=date(2026, 4, 1), is_workday=True),
    ])
    await db_session.commit()

    repo = WorkCalendarRepo(db_session)
    items = await repo.get_by_month(2026, 3)
    assert len(items) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/test_work_calendar_repo.py -v`
Expected: FAIL

- [ ] **Step 3: Implement WorkCalendarRepo**

```python
# app/repository/work_calendar_repo.py
from datetime import date
from typing import Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_calendar import WorkCalendar
from app.repository.base import BaseRepository


class WorkCalendarRepo(BaseRepository[WorkCalendar]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkCalendar)

    async def get_calendar_map(self, start: date, end: date) -> dict[date, bool]:
        stmt = select(WorkCalendar).where(
            and_(
                WorkCalendar.calendar_date >= start,
                WorkCalendar.calendar_date <= end,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return {r.calendar_date: r.is_workday for r in rows}

    async def upsert(self, calendar_date: date, is_workday: bool, remark: str | None = None) -> WorkCalendar:
        stmt = select(WorkCalendar).where(WorkCalendar.calendar_date == calendar_date)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_workday = is_workday
            existing.remark = remark
            await self.session.flush()
            return existing
        entity = WorkCalendar(calendar_date=calendar_date, is_workday=is_workday, remark=remark)
        return await self.add(entity)

    async def get_by_month(self, year: int, month: int) -> Sequence[WorkCalendar]:
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)
        stmt = select(WorkCalendar).where(
            and_(
                WorkCalendar.calendar_date >= start,
                WorkCalendar.calendar_date <= end,
            )
        ).order_by(WorkCalendar.calendar_date)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/test_work_calendar_repo.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/repository/work_calendar_repo.py tests/test_repository/test_work_calendar_repo.py
git commit -m "feat: add work calendar repository with upsert and date range query"
```

---

### Task 10: Repository — Sales Plan Repo

**Files:**
- Create: `auto-scheduling-system/services/api/app/repository/sales_plan_repo.py`
- Test: `auto-scheduling-system/services/api/tests/test_repository/test_sales_plan_repo.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_repository/test_sales_plan_repo.py
import pytest
from datetime import datetime
from decimal import Decimal
from app.models import SalesPlanOrderLineSrc
from app.repository.sales_plan_repo import SalesPlanRepo


@pytest.mark.asyncio
async def test_upsert_insert(db_session):
    repo = SalesPlanRepo(db_session)
    row = await repo.upsert_by_sap_key(
        sap_code="SAP001", sap_line_no="10",
        data={"contract_no": "HT001", "customer_name": "客户A", "quantity": Decimal("1")}
    )
    await db_session.commit()
    assert row.id is not None
    assert row.contract_no == "HT001"


@pytest.mark.asyncio
async def test_upsert_update(db_session):
    repo = SalesPlanRepo(db_session)
    await repo.upsert_by_sap_key(
        sap_code="SAP001", sap_line_no="10",
        data={"contract_no": "HT001", "customer_name": "客户A"}
    )
    await db_session.commit()

    await repo.upsert_by_sap_key(
        sap_code="SAP001", sap_line_no="10",
        data={"contract_no": "HT001", "customer_name": "客户B"}
    )
    await db_session.commit()

    count = await repo.count()
    assert count == 1

    rows = await repo.list_all()
    assert rows[0].customer_name == "客户B"


@pytest.mark.asyncio
async def test_paginate(db_session):
    repo = SalesPlanRepo(db_session)
    for i in range(5):
        db_session.add(SalesPlanOrderLineSrc(
            sap_code=f"SAP{i:03d}", sap_line_no="10",
            contract_no=f"HT{i:03d}", customer_name=f"客户{i}"
        ))
    await db_session.commit()

    items, total = await repo.paginate(page_no=1, page_size=2)
    assert total == 5
    assert len(items) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/test_sales_plan_repo.py -v`
Expected: FAIL

- [ ] **Step 3: Implement SalesPlanRepo**

```python
# app/repository/sales_plan_repo.py
from typing import Any, Sequence
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.base import BaseRepository


class SalesPlanRepo(BaseRepository[SalesPlanOrderLineSrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SalesPlanOrderLineSrc)

    async def upsert_by_sap_key(
        self, sap_code: str, sap_line_no: str, data: dict[str, Any]
    ) -> SalesPlanOrderLineSrc:
        stmt = select(SalesPlanOrderLineSrc).where(
            and_(
                SalesPlanOrderLineSrc.sap_code == sap_code,
                SalesPlanOrderLineSrc.sap_line_no == sap_line_no,
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = SalesPlanOrderLineSrc(sap_code=sap_code, sap_line_no=sap_line_no, **data)
        return await self.add(entity)

    async def find_by_detail_id(self, detail_id: str) -> SalesPlanOrderLineSrc | None:
        stmt = select(SalesPlanOrderLineSrc).where(
            SalesPlanOrderLineSrc.detail_id == detail_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[SalesPlanOrderLineSrc], int]:
        base = select(SalesPlanOrderLineSrc)
        count_stmt = select(func.count()).select_from(SalesPlanOrderLineSrc)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.offset((page_no - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return items, total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/test_sales_plan_repo.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/repository/sales_plan_repo.py tests/test_repository/test_sales_plan_repo.py
git commit -m "feat: add sales plan repository with upsert and pagination"
```

---

### Task 11: Repository — Remaining Repos (BOM, Production Order, Baselines, Results, Logs)

These repos follow the same pattern as above. Create them with their specific business methods.

**Files:**
- Create: `auto-scheduling-system/services/api/app/repository/bom_relation_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/production_order_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/machine_cycle_history_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/machine_cycle_baseline_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/part_cycle_baseline_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/assembly_time_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/sync_job_log_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/data_issue_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/machine_schedule_result_repo.py`
- Create: `auto-scheduling-system/services/api/app/repository/part_schedule_result_repo.py`
- Test: `auto-scheduling-system/services/api/tests/test_repository/test_machine_schedule_result_repo.py`
- Test: `auto-scheduling-system/services/api/tests/test_repository/test_data_issue_repo.py`

- [ ] **Step 1: Write failing test for machine schedule result repo**

```python
# tests/test_repository/test_machine_schedule_result_repo.py
import pytest
from decimal import Decimal
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo


@pytest.mark.asyncio
async def test_upsert_by_order_line_id(db_session):
    repo = MachineScheduleResultRepo(db_session)
    row = await repo.upsert_by_order_line_id(
        order_line_id=101,
        data={
            "contract_no": "HT001",
            "schedule_status": "scheduled",
            "machine_cycle_days": Decimal("20"),
            "run_batch_no": "SCH001",
        }
    )
    await db_session.commit()
    assert row.id is not None
    assert row.order_line_id == 101

    # Upsert again — should update
    row2 = await repo.upsert_by_order_line_id(
        order_line_id=101,
        data={"schedule_status": "scheduled", "run_batch_no": "SCH002"}
    )
    await db_session.commit()
    assert row2.id == row.id
    assert row2.run_batch_no == "SCH002"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/test_machine_schedule_result_repo.py -v`
Expected: FAIL

- [ ] **Step 3: Implement all remaining repos**

```python
# app/repository/bom_relation_repo.py
from typing import Sequence
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom_relation import BomRelationSrc
from app.repository.base import BaseRepository


class BomRelationRepo(BaseRepository[BomRelationSrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BomRelationSrc)

    async def delete_by_machine_and_plant(self, machine_material_no: str, plant: str) -> int:
        stmt = delete(BomRelationSrc).where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                BomRelationSrc.plant == plant,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def find_by_machine(self, machine_material_no: str) -> Sequence[BomRelationSrc]:
        stmt = select(BomRelationSrc).where(
            BomRelationSrc.machine_material_no == machine_material_no
        ).order_by(BomRelationSrc.bom_level)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_second_level(self, machine_material_no: str) -> Sequence[BomRelationSrc]:
        stmt = select(BomRelationSrc).where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                BomRelationSrc.bom_level == 2,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

```python
# app/repository/production_order_repo.py
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_order import ProductionOrderHistorySrc
from app.repository.base import BaseRepository


class ProductionOrderRepo(BaseRepository[ProductionOrderHistorySrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ProductionOrderHistorySrc)

    async def upsert_by_order_no(
        self, production_order_no: str, data: dict[str, Any]
    ) -> ProductionOrderHistorySrc:
        stmt = select(ProductionOrderHistorySrc).where(
            ProductionOrderHistorySrc.production_order_no == production_order_no
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = ProductionOrderHistorySrc(production_order_no=production_order_no, **data)
        return await self.add(entity)
```

```python
# app/repository/machine_cycle_history_repo.py
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.repository.base import BaseRepository


class MachineCycleHistoryRepo(BaseRepository[MachineCycleHistorySrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MachineCycleHistorySrc)

    async def upsert_by_detail_id(
        self, detail_id: str, data: dict[str, Any]
    ) -> MachineCycleHistorySrc:
        stmt = select(MachineCycleHistorySrc).where(
            MachineCycleHistorySrc.detail_id == detail_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = MachineCycleHistorySrc(detail_id=detail_id, **data)
        return await self.add(entity)
```

```python
# app/repository/machine_cycle_baseline_repo.py
from typing import Sequence
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.repository.base import BaseRepository


class MachineCycleBaselineRepo(BaseRepository[MachineCycleBaseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MachineCycleBaseline)

    async def find_by_model_and_qty(
        self, machine_model: str, order_qty: Decimal
    ) -> MachineCycleBaseline | None:
        stmt = select(MachineCycleBaseline).where(
            and_(
                MachineCycleBaseline.machine_model == machine_model,
                MachineCycleBaseline.order_qty == order_qty,
                MachineCycleBaseline.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all_by_model(self, machine_model: str) -> Sequence[MachineCycleBaseline]:
        stmt = select(MachineCycleBaseline).where(
            and_(
                MachineCycleBaseline.machine_model == machine_model,
                MachineCycleBaseline.is_active == True,
            )
        ).order_by(MachineCycleBaseline.order_qty)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

```python
# app/repository/part_cycle_baseline_repo.py
from typing import Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part_cycle_baseline import PartCycleBaseline
from app.repository.base import BaseRepository


class PartCycleBaselineRepo(BaseRepository[PartCycleBaseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PartCycleBaseline)

    async def find_by_model_and_material(
        self, machine_model: str, material_no: str
    ) -> PartCycleBaseline | None:
        stmt = select(PartCycleBaseline).where(
            and_(
                PartCycleBaseline.machine_model == machine_model,
                PartCycleBaseline.material_no == material_no,
                PartCycleBaseline.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_model_and_desc_prefix(
        self, machine_model: str, desc_prefix: str
    ) -> PartCycleBaseline | None:
        stmt = select(PartCycleBaseline).where(
            and_(
                PartCycleBaseline.machine_model == machine_model,
                PartCycleBaseline.material_desc.startswith(desc_prefix),
                PartCycleBaseline.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
```

```python
# app/repository/assembly_time_repo.py
from typing import Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assembly_time import AssemblyTimeBaseline
from app.repository.base import BaseRepository


class AssemblyTimeRepo(BaseRepository[AssemblyTimeBaseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AssemblyTimeBaseline)

    async def find_by_model_and_assembly(
        self, machine_model: str, assembly_name: str
    ) -> AssemblyTimeBaseline | None:
        stmt = select(AssemblyTimeBaseline).where(
            and_(
                AssemblyTimeBaseline.machine_model == machine_model,
                AssemblyTimeBaseline.assembly_name == assembly_name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_final_assembly(self, machine_model: str) -> AssemblyTimeBaseline | None:
        stmt = select(AssemblyTimeBaseline).where(
            and_(
                AssemblyTimeBaseline.machine_model == machine_model,
                AssemblyTimeBaseline.is_final_assembly == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all_by_model(self, machine_model: str) -> Sequence[AssemblyTimeBaseline]:
        stmt = select(AssemblyTimeBaseline).where(
            AssemblyTimeBaseline.machine_model == machine_model
        ).order_by(AssemblyTimeBaseline.production_sequence)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

```python
# app/repository/sync_job_log_repo.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_job_log import SyncJobLog
from app.repository.base import BaseRepository


class SyncJobLogRepo(BaseRepository[SyncJobLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SyncJobLog)
```

```python
# app/repository/data_issue_repo.py
from typing import Any, Sequence
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_issue import DataIssueRecord
from app.repository.base import BaseRepository


class DataIssueRepo(BaseRepository[DataIssueRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DataIssueRecord)

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[DataIssueRecord], int]:
        base = select(DataIssueRecord)
        count_base = select(func.count()).select_from(DataIssueRecord)

        conditions = []
        if "status" in filters and filters["status"]:
            conditions.append(DataIssueRecord.status == filters["status"])
        if "issue_type" in filters and filters["issue_type"]:
            conditions.append(DataIssueRecord.issue_type == filters["issue_type"])

        if conditions:
            base = base.where(and_(*conditions))
            count_base = count_base.where(and_(*conditions))

        total = (await self.session.execute(count_base)).scalar_one()
        stmt = base.order_by(DataIssueRecord.id.desc()).offset((page_no - 1) * page_size).limit(page_size)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
```

```python
# app/repository/machine_schedule_result_repo.py
from typing import Any, Sequence
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_schedule_result import MachineScheduleResult
from app.repository.base import BaseRepository


class MachineScheduleResultRepo(BaseRepository[MachineScheduleResult]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MachineScheduleResult)

    async def upsert_by_order_line_id(
        self, order_line_id: int, data: dict[str, Any]
    ) -> MachineScheduleResult:
        stmt = select(MachineScheduleResult).where(
            MachineScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = MachineScheduleResult(order_line_id=order_line_id, **data)
        return await self.add(entity)

    async def find_by_order_line_id(self, order_line_id: int) -> MachineScheduleResult | None:
        stmt = select(MachineScheduleResult).where(
            MachineScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[MachineScheduleResult], int]:
        base = select(MachineScheduleResult)
        count_base = select(func.count()).select_from(MachineScheduleResult)

        total = (await self.session.execute(count_base)).scalar_one()
        stmt = base.offset((page_no - 1) * page_size).limit(page_size)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
```

```python
# app/repository/part_schedule_result_repo.py
from typing import Sequence
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part_schedule_result import PartScheduleResult
from app.repository.base import BaseRepository


class PartScheduleResultRepo(BaseRepository[PartScheduleResult]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PartScheduleResult)

    async def delete_by_order_line_id(self, order_line_id: int) -> int:
        stmt = delete(PartScheduleResult).where(
            PartScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def find_by_order_line_id(self, order_line_id: int) -> Sequence[PartScheduleResult]:
        stmt = select(PartScheduleResult).where(
            PartScheduleResult.order_line_id == order_line_id
        ).order_by(PartScheduleResult.production_sequence)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

- [ ] **Step 4: Run all repo tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_repository/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/repository/ tests/test_repository/
git commit -m "feat: add all 12 repository classes"
```

---

### Task 12: Work Calendar Initialization Script

**Files:**
- Create: `auto-scheduling-system/services/api/scripts/init_work_calendar.py`

Initializes 2026-2027 work calendar (weekdays = workday, weekends = off).

- [ ] **Step 1: Create init script**

```python
# scripts/init_work_calendar.py
"""Initialize work calendar for 2026-2027. Run once after DB setup.

Usage: python -m scripts.init_work_calendar
"""
import asyncio
from datetime import date, timedelta

from app.database import async_session_factory
from app.models.base import Base
from app.models.work_calendar import WorkCalendar
from app.database import engine


async def init_calendar():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        start = date(2026, 1, 1)
        end = date(2027, 12, 31)
        current = start
        batch = []
        while current <= end:
            batch.append(WorkCalendar(
                calendar_date=current,
                is_workday=current.weekday() < 5,
                remark=None,
            ))
            current += timedelta(days=1)

        session.add_all(batch)
        await session.commit()
        print(f"Initialized {len(batch)} calendar days ({start} to {end})")


if __name__ == "__main__":
    asyncio.run(init_calendar())
```

- [ ] **Step 2: Verify script can be imported**

Run: `cd auto-scheduling-system/services/api && python -c "from scripts.init_work_calendar import init_calendar; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: add work calendar initialization script for 2026-2027"
```

---

### Task 13: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS (approx 15-20 tests)

- [ ] **Step 2: Final commit if anything was missed**

```bash
git status
# If clean, no commit needed
```

---

## Phase 1 Completion Checklist

After completing all tasks above, you should have:

- [x] FastAPI project scaffold with config, database, health check
- [x] All enums: ScheduleStatus, WarningLevel, OrderType, IssueStatus
- [x] Business exceptions with error codes
- [x] Unified API response model
- [x] Workday calendar utils (add/subtract workdays)
- [x] Chinese text prefix extraction for assembly name parsing
- [x] 12 SQLAlchemy models matching the SQL schema
- [x] Base repository with generic CRUD
- [x] 12 concrete repositories with business-specific queries
- [x] Work calendar initialization script (2026-2027)
- [x] Full test suite passing

**Next:** Proceed to Phase 2 plan (Integration + Sync layer).
