# Phase 3: Baseline + Scheduler Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the baseline computation services (machine cycle, part cycle, assembly time defaults) and the scheduling engine that backward-schedules whole-machine and key-part production dates.

**Architecture:** Baseline layer reads sync'd history data, groups/aggregates, and writes baselines. Scheduler layer reads baselines + BOM + calendar to backward-schedule from delivery dates. All services are stateless functions operating on the async DB session.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0 (async), pytest, pytest-asyncio, statistics.median

**This is Plan 3 of 4:**
1. **Foundation** (done): scaffold, models, repos, common utils
2. **Integration + Sync** (done): external API clients, data sync services
3. **Baseline + Scheduler** (this plan): cycle baselines, scheduling engine
4. **API Layer**: REST endpoints, export, admin

---

## File Structure

```
auto-scheduling-system/services/api/
├── app/
│   ├── baseline/
│   │   ├── __init__.py
│   │   ├── machine_cycle_baseline_service.py   # Compute machine cycle medians
│   │   ├── part_cycle_baseline_service.py      # Compute part cycle from prod orders
│   │   └── assembly_time_default_service.py    # Ensure default assembly times
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── schedule_check_service.py           # Schedulability check + trigger date
│   │   ├── assembly_identify_service.py        # Identify assemblies from BOM
│   │   ├── key_part_identify_service.py        # Find key self-made part per assembly
│   │   ├── machine_schedule_service.py         # Whole-machine schedule computation
│   │   ├── part_schedule_service.py            # Key-part schedule computation
│   │   └── schedule_orchestrator.py            # Coordinate full scheduling
├── tests/
│   ├── test_baseline/
│   │   ├── __init__.py
│   │   ├── test_machine_cycle_baseline_service.py
│   │   ├── test_part_cycle_baseline_service.py
│   │   └── test_assembly_time_default_service.py
│   ├── test_scheduler/
│   │   ├── __init__.py
│   │   ├── test_schedule_check_service.py
│   │   ├── test_assembly_identify_service.py
│   │   ├── test_key_part_identify_service.py
│   │   ├── test_machine_schedule_service.py
│   │   ├── test_part_schedule_service.py
│   │   └── test_schedule_orchestrator.py
```

---

### Task 1: Baseline — Machine Cycle Baseline Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/baseline/__init__.py`
- Create: `auto-scheduling-system/services/api/app/baseline/machine_cycle_baseline_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_baseline/__init__.py`
- Test: `auto-scheduling-system/services/api/tests/test_baseline/test_machine_cycle_baseline_service.py`

**Key rules:**
- Read all rows from `machine_cycle_history_src` where `cycle_days` is not null
- Group by `product_series + machine_model + order_qty`
- Compute median of `cycle_days` per group
- Upsert into `machine_cycle_baseline`
- Return a result summary (groups processed, baselines written)

- [ ] **Step 1: Write failing test**

```python
# tests/test_baseline/test_machine_cycle_baseline_service.py
import pytest
from decimal import Decimal

from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.baseline.machine_cycle_baseline_service import MachineCycleBaselineService
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo


@pytest.mark.asyncio
async def test_build_baseline_single_group(db_session):
    # Insert 3 history records for same model+qty
    for i, days in enumerate([Decimal("60"), Decimal("80"), Decimal("70")]):
        db_session.add(MachineCycleHistorySrc(
            detail_id=f"DT00{i}",
            machine_model="MC1-80",
            product_series="MC1",
            order_qty=Decimal("1"),
            cycle_days=days,
        ))
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_qty("MC1-80", Decimal("1"))
    assert baseline is not None
    assert baseline.cycle_days_median == Decimal("70")  # median of 60, 70, 80
    assert baseline.sample_count == 3
    assert result["groups_processed"] == 1


@pytest.mark.asyncio
async def test_build_baseline_multiple_groups(db_session):
    # Group 1: MC1-80, qty=1
    for i, days in enumerate([Decimal("60"), Decimal("80")]):
        db_session.add(MachineCycleHistorySrc(
            detail_id=f"G1-{i}", machine_model="MC1-80",
            product_series="MC1", order_qty=Decimal("1"), cycle_days=days,
        ))
    # Group 2: MC1-80, qty=2
    db_session.add(MachineCycleHistorySrc(
        detail_id="G2-0", machine_model="MC1-80",
        product_series="MC1", order_qty=Decimal("2"), cycle_days=Decimal("100"),
    ))
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    b1 = await repo.find_by_model_and_qty("MC1-80", Decimal("1"))
    b2 = await repo.find_by_model_and_qty("MC1-80", Decimal("2"))
    assert b1 is not None
    assert b1.cycle_days_median == Decimal("70")  # median of 60, 80
    assert b2 is not None
    assert b2.cycle_days_median == Decimal("100")
    assert result["groups_processed"] == 2


@pytest.mark.asyncio
async def test_build_baseline_skips_null_cycle(db_session):
    db_session.add(MachineCycleHistorySrc(
        detail_id="DT-NULL", machine_model="MC1-80",
        product_series="MC1", order_qty=Decimal("1"), cycle_days=None,
    ))
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_qty("MC1-80", Decimal("1"))
    assert baseline is None
    assert result["groups_processed"] == 0
```

- [ ] **Step 2: Implement MachineCycleBaselineService**

```python
# app/baseline/__init__.py
```

```python
# app/baseline/machine_cycle_baseline_service.py
import logging
from collections import defaultdict
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo

logger = logging.getLogger(__name__)


class MachineCycleBaselineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MachineCycleBaselineRepo(session)

    async def rebuild(self) -> dict[str, Any]:
        """Rebuild all machine cycle baselines from history data."""
        # Read all history with non-null cycle_days
        stmt = select(MachineCycleHistorySrc).where(
            MachineCycleHistorySrc.cycle_days.isnot(None)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # Group by (product_series, machine_model, order_qty)
        groups: dict[tuple, list[Decimal]] = defaultdict(list)
        for row in rows:
            key = (row.product_series or "", row.machine_model, row.order_qty)
            groups[key].append(row.cycle_days)

        # Compute median per group and upsert
        groups_processed = 0
        for (series, model, qty), cycle_values in groups.items():
            float_values = [float(v) for v in cycle_values]
            median_val = Decimal(str(round(median(float_values), 4)))

            await self.repo.upsert_baseline(
                product_series=series,
                machine_model=model,
                order_qty=qty,
                data={
                    "cycle_days_median": median_val,
                    "sample_count": len(cycle_values),
                    "is_active": True,
                },
            )
            groups_processed += 1

        return {"groups_processed": groups_processed, "total_samples": len(rows)}
```

- [ ] **Step 3: Add upsert_baseline to MachineCycleBaselineRepo**

The existing repo needs an `upsert_baseline` method. Add to `app/repository/machine_cycle_baseline_repo.py`:

```python
async def upsert_baseline(
    self, product_series: str, machine_model: str, order_qty: Decimal,
    data: dict[str, Any],
) -> MachineCycleBaseline:
    stmt = select(MachineCycleBaseline).where(
        and_(
            MachineCycleBaseline.product_series == product_series,
            MachineCycleBaseline.machine_model == machine_model,
            MachineCycleBaseline.order_qty == order_qty,
        )
    )
    existing = (await self.session.execute(stmt)).scalar_one_or_none()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        await self.session.flush()
        return existing
    else:
        entity = MachineCycleBaseline(
            product_series=product_series,
            machine_model=machine_model,
            order_qty=order_qty,
            **data,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity
```

- [ ] **Step 4: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_baseline/test_machine_cycle_baseline_service.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/baseline/ app/repository/machine_cycle_baseline_repo.py tests/test_baseline/
git commit -m "feat: add machine cycle baseline computation service"
```

---

### Task 2: Baseline — Part Cycle Baseline Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/baseline/part_cycle_baseline_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_baseline/test_part_cycle_baseline_service.py`

**Key rules:**
- Read completed production orders (`order_status == "已完工"`) with both start and finish times
- Compute `cycle_days = finish_time_actual - start_time_actual` (in days)
- Compute `unit_cycle_days = cycle_days / production_qty`
- Extract `core_part_name` from `material_desc` using `extract_chinese_prefix()`
- Group by `material_no + machine_model`
- For each group, take the median of `cycle_days`
- Write to `part_cycle_baseline`

- [ ] **Step 1: Write failing test**

```python
# tests/test_baseline/test_part_cycle_baseline_service.py
import pytest
from decimal import Decimal
from datetime import datetime

from app.models.production_order import ProductionOrderHistorySrc
from app.baseline.part_cycle_baseline_service import PartCycleBaselineService
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo


@pytest.mark.asyncio
async def test_build_baseline_from_completed_orders(db_session):
    # Insert completed production orders
    db_session.add(ProductionOrderHistorySrc(
        production_order_no="PO001",
        material_no="COMP001",
        material_desc="机身MC1-80",
        machine_model="MC1-80",
        start_time_actual=datetime(2026, 1, 1),
        finish_time_actual=datetime(2026, 1, 31),  # 30 days
        production_qty=Decimal("2"),
        order_status="已完工",
    ))
    db_session.add(ProductionOrderHistorySrc(
        production_order_no="PO002",
        material_no="COMP001",
        material_desc="机身MC1-80",
        machine_model="MC1-80",
        start_time_actual=datetime(2026, 2, 1),
        finish_time_actual=datetime(2026, 2, 21),  # 20 days
        production_qty=Decimal("2"),
        order_status="已完工",
    ))
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = PartCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_material("MC1-80", "COMP001")
    assert baseline is not None
    # median of 30, 20 = 25
    assert baseline.cycle_days == Decimal("25")
    assert baseline.core_part_name == "机身"
    assert result["groups_processed"] == 1


@pytest.mark.asyncio
async def test_skips_non_completed_orders(db_session):
    db_session.add(ProductionOrderHistorySrc(
        production_order_no="PO003",
        material_no="COMP002",
        material_desc="传动部件A",
        machine_model="MC1-80",
        start_time_actual=datetime(2026, 1, 1),
        finish_time_actual=datetime(2026, 1, 10),
        production_qty=Decimal("1"),
        order_status="生产中",  # not completed
    ))
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    assert result["groups_processed"] == 0


@pytest.mark.asyncio
async def test_skips_missing_times(db_session):
    db_session.add(ProductionOrderHistorySrc(
        production_order_no="PO004",
        material_no="COMP003",
        material_desc="滑块部件",
        machine_model="MC1-80",
        start_time_actual=None,
        finish_time_actual=datetime(2026, 1, 10),
        production_qty=Decimal("1"),
        order_status="已完工",
    ))
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    assert result["groups_processed"] == 0
```

- [ ] **Step 2: Implement PartCycleBaselineService**

```python
# app/baseline/part_cycle_baseline_service.py
import logging
from collections import defaultdict
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.text_parse_utils import extract_chinese_prefix
from app.models.production_order import ProductionOrderHistorySrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo

logger = logging.getLogger(__name__)


class PartCycleBaselineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PartCycleBaselineRepo(session)

    async def rebuild(self) -> dict[str, Any]:
        """Rebuild all part cycle baselines from completed production orders."""
        stmt = select(ProductionOrderHistorySrc).where(
            and_(
                ProductionOrderHistorySrc.order_status == "已完工",
                ProductionOrderHistorySrc.start_time_actual.isnot(None),
                ProductionOrderHistorySrc.finish_time_actual.isnot(None),
                ProductionOrderHistorySrc.production_qty.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # Group by (material_no, machine_model)
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for row in rows:
            delta = row.finish_time_actual - row.start_time_actual
            cycle_days = Decimal(str(delta.days))
            if cycle_days <= 0:
                continue
            qty = row.production_qty or Decimal("1")
            unit_cycle = cycle_days / qty

            key = (row.material_no, row.machine_model or "")
            groups[key].append({
                "cycle_days": cycle_days,
                "unit_cycle_days": unit_cycle,
                "material_desc": row.material_desc or "",
                "batch_qty": qty,
            })

        groups_processed = 0
        for (material_no, machine_model), entries in groups.items():
            cycle_values = [float(e["cycle_days"]) for e in entries]
            median_cycle = Decimal(str(round(median(cycle_values), 4)))

            unit_values = [float(e["unit_cycle_days"]) for e in entries]
            median_unit = Decimal(str(round(median(unit_values), 6)))

            desc = entries[0]["material_desc"]
            core_name = extract_chinese_prefix(desc) or desc[:20]
            ref_batch = entries[0]["batch_qty"]

            await self._upsert_baseline(
                material_no=material_no,
                machine_model=machine_model,
                data={
                    "material_desc": desc,
                    "core_part_name": core_name,
                    "ref_batch_qty": ref_batch,
                    "cycle_days": median_cycle,
                    "unit_cycle_days": median_unit,
                    "cycle_source": "history",
                    "match_rule": "exact_material",
                    "confidence_level": "high" if len(entries) >= 3 else "medium",
                    "is_active": True,
                    "is_default": False,
                },
            )
            groups_processed += 1

        return {"groups_processed": groups_processed, "total_orders": len(rows)}

    async def _upsert_baseline(
        self, material_no: str, machine_model: str, data: dict[str, Any]
    ) -> PartCycleBaseline:
        stmt = select(PartCycleBaseline).where(
            and_(
                PartCycleBaseline.material_no == material_no,
                PartCycleBaseline.machine_model == machine_model,
                PartCycleBaseline.is_active == True,
            )
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        else:
            entity = PartCycleBaseline(
                material_no=material_no,
                machine_model=machine_model,
                **data,
            )
            self.session.add(entity)
            await self.session.flush()
            return entity
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_baseline/test_part_cycle_baseline_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/baseline/part_cycle_baseline_service.py tests/test_baseline/test_part_cycle_baseline_service.py
git commit -m "feat: add part cycle baseline computation service"
```

---

### Task 3: Baseline — Assembly Time Default Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/baseline/assembly_time_default_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_baseline/test_assembly_time_default_service.py`

**Key rules:**
- Auto-create default assembly time if none exists for a given machine_model + assembly_name
- Sub-assembly default: 1 day, `is_default=True`
- Final assembly (整机) default: 3 days, `is_default=True`
- Default production sequences: 机身=1, 传动=2, 滑块=2, 平衡缸=3, 空气管路=4, 电气=5, others=3

- [ ] **Step 1: Write failing test**

```python
# tests/test_baseline/test_assembly_time_default_service.py
import pytest
from decimal import Decimal

from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.repository.assembly_time_repo import AssemblyTimeRepo


@pytest.mark.asyncio
async def test_ensure_default_sub_assembly(db_session):
    service = AssemblyTimeDefaultService(db_session)
    record = await service.ensure_default(
        machine_model="MC1-80",
        product_series="MC1",
        assembly_name="机身",
        is_final_assembly=False,
    )
    await db_session.commit()

    assert record is not None
    assert record.assembly_time_days == Decimal("1")
    assert record.is_default is True
    assert record.production_sequence == 1  # 机身 = 1


@pytest.mark.asyncio
async def test_ensure_default_final_assembly(db_session):
    service = AssemblyTimeDefaultService(db_session)
    record = await service.ensure_default(
        machine_model="MC1-80",
        product_series="MC1",
        assembly_name="整机总装",
        is_final_assembly=True,
    )
    await db_session.commit()

    assert record is not None
    assert record.assembly_time_days == Decimal("3")
    assert record.is_final_assembly is True


@pytest.mark.asyncio
async def test_does_not_overwrite_existing(db_session):
    service = AssemblyTimeDefaultService(db_session)
    # Create default
    await service.ensure_default("MC1-80", "MC1", "机身", False)
    await db_session.commit()

    # Manually update
    repo = AssemblyTimeRepo(db_session)
    existing = await repo.find_by_model_and_assembly("MC1-80", "机身")
    existing.assembly_time_days = Decimal("5")
    existing.is_default = False
    await db_session.commit()

    # ensure_default should not overwrite
    record = await service.ensure_default("MC1-80", "MC1", "机身", False)
    await db_session.commit()

    assert record.assembly_time_days == Decimal("5")
    assert record.is_default is False


@pytest.mark.asyncio
async def test_default_sequence_mapping(db_session):
    service = AssemblyTimeDefaultService(db_session)

    await service.ensure_default("MC1-80", "MC1", "传动", False)
    await service.ensure_default("MC1-80", "MC1", "滑块", False)
    await service.ensure_default("MC1-80", "MC1", "电气", False)
    await service.ensure_default("MC1-80", "MC1", "离合器", False)
    await db_session.commit()

    repo = AssemblyTimeRepo(db_session)
    t = await repo.find_by_model_and_assembly("MC1-80", "传动")
    assert t.production_sequence == 2
    s = await repo.find_by_model_and_assembly("MC1-80", "滑块")
    assert s.production_sequence == 2
    e = await repo.find_by_model_and_assembly("MC1-80", "电气")
    assert e.production_sequence == 5
    c = await repo.find_by_model_and_assembly("MC1-80", "离合器")
    assert c.production_sequence == 3  # unknown = 3
```

- [ ] **Step 2: Implement AssemblyTimeDefaultService**

```python
# app/baseline/assembly_time_default_service.py
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assembly_time import AssemblyTimeBaseline
from app.repository.assembly_time_repo import AssemblyTimeRepo

logger = logging.getLogger(__name__)

_DEFAULT_SUB_ASSEMBLY_DAYS = Decimal("1")
_DEFAULT_FINAL_ASSEMBLY_DAYS = Decimal("3")

_DEFAULT_SEQUENCE_MAP = {
    "机身": 1,
    "传动": 2,
    "滑块": 2,
    "平衡缸": 3,
    "空气管路": 4,
    "电气": 5,
}
_DEFAULT_SEQUENCE_FALLBACK = 3


class AssemblyTimeDefaultService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AssemblyTimeRepo(session)

    async def ensure_default(
        self,
        machine_model: str,
        product_series: str | None,
        assembly_name: str,
        is_final_assembly: bool,
    ) -> AssemblyTimeBaseline:
        """Return existing record or create a default one."""
        existing = await self.repo.find_by_model_and_assembly(machine_model, assembly_name)
        if existing:
            return existing

        days = _DEFAULT_FINAL_ASSEMBLY_DAYS if is_final_assembly else _DEFAULT_SUB_ASSEMBLY_DAYS
        sequence = _DEFAULT_SEQUENCE_MAP.get(assembly_name, _DEFAULT_SEQUENCE_FALLBACK)

        entity = AssemblyTimeBaseline(
            machine_model=machine_model,
            product_series=product_series,
            assembly_name=assembly_name,
            assembly_time_days=days,
            is_final_assembly=is_final_assembly,
            production_sequence=sequence,
            is_default=True,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_baseline/test_assembly_time_default_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/baseline/assembly_time_default_service.py tests/test_baseline/test_assembly_time_default_service.py
git commit -m "feat: add assembly time default service with sequence mapping"
```

---

### Task 4: Scheduler — Schedule Check Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/scheduler/__init__.py`
- Create: `auto-scheduling-system/services/api/app/scheduler/schedule_check_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/__init__.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/test_schedule_check_service.py`

**Key rules:**
- Three conditions for schedulability:
  1. `confirmed_delivery_date` is not null
  2. `drawing_released == True`
  3. Current date >= `trigger_date` (= delivery_date - machine_cycle_days)
- Compute trigger_date from machine cycle baseline
- If no baseline, use a configurable default (e.g., 90 days) and flag
- Return status: pending_drawing / pending_trigger / schedulable

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler/test_schedule_check_service.py
import pytest
from decimal import Decimal
from datetime import datetime, date

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.scheduler.schedule_check_service import ScheduleCheckService


@pytest.mark.asyncio
async def test_pending_drawing(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 9, 1),
        drawing_released=False,
        product_model="MC1-80",
        quantity=Decimal("1"),
    )
    db_session.add(order)
    await db_session.commit()

    service = ScheduleCheckService(db_session)
    result = await service.check(order.id)

    assert result["status"] == "pending_drawing"
    assert result["is_schedulable"] is False


@pytest.mark.asyncio
async def test_pending_trigger(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002", sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 12, 1),
        drawing_released=True,
        product_model="MC1-80",
        quantity=Decimal("1"),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("90"),
        sample_count=5, is_active=True,
    ))
    await db_session.commit()

    service = ScheduleCheckService(db_session, today=date(2026, 3, 17))
    result = await service.check(order.id)

    assert result["status"] == "pending_trigger"
    assert result["trigger_date"] is not None


@pytest.mark.asyncio
async def test_schedulable(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP003", sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 6, 1),
        drawing_released=True,
        product_model="MC1-80",
        quantity=Decimal("1"),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("60"),
        sample_count=5, is_active=True,
    ))
    await db_session.commit()

    # today is 2026-03-17, trigger = 2026-06-01 - 60 workdays ≈ 2026-03-05
    service = ScheduleCheckService(db_session, today=date(2026, 3, 17))
    result = await service.check(order.id)

    assert result["status"] == "schedulable"
    assert result["is_schedulable"] is True


@pytest.mark.asyncio
async def test_no_delivery_date(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP004", sap_line_no="10",
        confirmed_delivery_date=None,
        drawing_released=True,
        product_model="MC1-80",
        quantity=Decimal("1"),
    )
    db_session.add(order)
    await db_session.commit()

    service = ScheduleCheckService(db_session)
    result = await service.check(order.id)

    assert result["is_schedulable"] is False
```

- [ ] **Step 2: Implement ScheduleCheckService**

```python
# app/scheduler/__init__.py
```

```python
# app/scheduler/schedule_check_service.py
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.calendar_utils import subtract_workdays
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo
from app.repository.work_calendar_repo import WorkCalendarRepo

logger = logging.getLogger(__name__)

_DEFAULT_MACHINE_CYCLE_DAYS = Decimal("90")


class ScheduleCheckService:
    def __init__(self, session: AsyncSession, today: date | None = None):
        self.session = session
        self.today = today or date.today()
        self.baseline_repo = MachineCycleBaselineRepo(session)
        self.calendar_repo = WorkCalendarRepo(session)

    async def check(self, order_line_id: int) -> dict[str, Any]:
        """Check if an order is schedulable. Returns status dict."""
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order:
            return {"is_schedulable": False, "status": "not_found", "reason": "Order not found"}

        # Condition 1: delivery date
        if not order.confirmed_delivery_date:
            return {
                "is_schedulable": False,
                "status": "pending_drawing",
                "reason": "No confirmed delivery date",
            }

        # Condition 2: drawing released
        if not order.drawing_released:
            return {
                "is_schedulable": False,
                "status": "pending_drawing",
                "reason": "Drawing not released",
            }

        # Compute trigger date
        machine_cycle_days, is_default = await self._get_machine_cycle(
            order.product_model, order.quantity
        )
        calendar = await self._get_calendar()
        delivery = order.confirmed_delivery_date
        if isinstance(delivery, datetime):
            delivery = delivery.date()

        trigger_date = subtract_workdays(delivery, int(machine_cycle_days), calendar)

        # Condition 3: trigger date reached
        if self.today < trigger_date:
            return {
                "is_schedulable": False,
                "status": "pending_trigger",
                "trigger_date": trigger_date,
                "machine_cycle_days": machine_cycle_days,
                "is_default_cycle": is_default,
            }

        return {
            "is_schedulable": True,
            "status": "schedulable",
            "trigger_date": trigger_date,
            "machine_cycle_days": machine_cycle_days,
            "is_default_cycle": is_default,
        }

    async def _get_machine_cycle(
        self, machine_model: str | None, quantity: Decimal | None
    ) -> tuple[Decimal, bool]:
        """Get machine cycle days. Returns (days, is_default)."""
        if not machine_model:
            return _DEFAULT_MACHINE_CYCLE_DAYS, True

        qty = quantity or Decimal("1")

        # Exact match
        baseline = await self.baseline_repo.find_by_model_and_qty(machine_model, qty)
        if baseline:
            return baseline.cycle_days_median, False

        # Nearest quantity fallback
        all_baselines = await self.baseline_repo.find_all_by_model(machine_model)
        if all_baselines:
            nearest = min(all_baselines, key=lambda b: abs(b.order_qty - qty))
            coefficient = float(qty) / float(nearest.order_qty) if nearest.order_qty else 1.0
            adjusted = Decimal(str(round(float(nearest.cycle_days_median) * coefficient, 4)))
            return adjusted, False

        return _DEFAULT_MACHINE_CYCLE_DAYS, True

    async def _get_calendar(self) -> dict[date, bool]:
        """Load work calendar as dict."""
        return await self.calendar_repo.get_calendar_map()
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_scheduler/test_schedule_check_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/scheduler/ tests/test_scheduler/
git commit -m "feat: add schedule check service with trigger date computation"
```

---

### Task 5: Scheduler — Assembly Identify Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/scheduler/assembly_identify_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/test_assembly_identify_service.py`

**Key rules:**
- Read BOM second-level rows (`bom_level == 2`, `is_self_made == True`) for machine_material_no
- Extract Chinese prefix from `bom_component_desc` → `assembly_name`
- Filter excluded assemblies (润滑/附件/油漆/标牌/包装)
- Deduplicate by assembly_name (keep first occurrence)
- Look up or create assembly time records via AssemblyTimeDefaultService

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler/test_assembly_identify_service.py
import pytest
from decimal import Decimal

from app.models.bom_relation import BomRelationSrc
from app.scheduler.assembly_identify_service import AssemblyIdentifyService


@pytest.mark.asyncio
async def test_identify_assemblies(db_session):
    # Insert BOM rows
    bom_rows = [
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            bom_component_no="COMP001", bom_component_desc="机身MC1-80",
            bom_level=2, is_self_made=True, is_top_level=False, part_type="自产件",
        ),
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            bom_component_no="COMP002", bom_component_desc="传动总成",
            bom_level=2, is_self_made=True, is_top_level=False, part_type="自产件",
        ),
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            bom_component_no="COMP003", bom_component_desc="润滑系统",
            bom_level=2, is_self_made=True, is_top_level=False, part_type="自产件",
        ),
    ]
    for r in bom_rows:
        db_session.add(r)
    await db_session.commit()

    service = AssemblyIdentifyService(db_session)
    assemblies = await service.identify(
        machine_material_no="MACH001",
        machine_model="MC1-80",
        product_series="MC1",
    )

    names = [a["assembly_name"] for a in assemblies]
    assert "机身" in names
    assert "传动" in names
    assert "润滑" not in names  # excluded


@pytest.mark.asyncio
async def test_empty_bom(db_session):
    service = AssemblyIdentifyService(db_session)
    assemblies = await service.identify(
        machine_material_no="NONEXIST",
        machine_model="MC1-80",
        product_series="MC1",
    )
    assert assemblies == []
```

- [ ] **Step 2: Implement AssemblyIdentifyService**

```python
# app/scheduler/assembly_identify_service.py
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.text_parse_utils import extract_chinese_prefix, is_excluded_assembly
from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.repository.bom_relation_repo import BomRelationRepo

logger = logging.getLogger(__name__)


class AssemblyIdentifyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bom_repo = BomRelationRepo(session)
        self.assembly_default = AssemblyTimeDefaultService(session)

    async def identify(
        self,
        machine_material_no: str,
        machine_model: str,
        product_series: str | None = None,
    ) -> list[dict[str, Any]]:
        """Identify assemblies from BOM second-level self-made parts."""
        second_level = await self.bom_repo.find_second_level(machine_material_no)

        seen_names: set[str] = set()
        assemblies = []

        for bom_row in second_level:
            if not bom_row.is_self_made:
                continue

            name = extract_chinese_prefix(bom_row.bom_component_desc or "")
            if not name:
                continue
            if is_excluded_assembly(name):
                continue
            if name in seen_names:
                continue
            seen_names.add(name)

            # Ensure assembly time record exists
            at_record = await self.assembly_default.ensure_default(
                machine_model=machine_model,
                product_series=product_series,
                assembly_name=name,
                is_final_assembly=False,
            )

            assemblies.append({
                "assembly_name": name,
                "production_sequence": at_record.production_sequence,
                "assembly_time_days": at_record.assembly_time_days,
                "is_default_time": at_record.is_default,
                "bom_component_no": bom_row.bom_component_no,
                "bom_component_desc": bom_row.bom_component_desc,
            })

        # Sort by production_sequence
        assemblies.sort(key=lambda a: a["production_sequence"])
        return assemblies
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_scheduler/test_assembly_identify_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/scheduler/assembly_identify_service.py tests/test_scheduler/test_assembly_identify_service.py
git commit -m "feat: add assembly identify service with exclusion filtering"
```

---

### Task 6: Scheduler — Key Part Identify Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/scheduler/key_part_identify_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/test_key_part_identify_service.py`

**Key rules:**
- For a given assembly, find all direct child self-made parts from BOM
- Look up part cycle baseline for each part
- Select the part with the longest cycle as the "key part"
- If no baseline found, use default 1 day and flag `is_default=True`
- Support fuzzy match by core Chinese prefix if exact match fails

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler/test_key_part_identify_service.py
import pytest
from decimal import Decimal

from app.models.bom_relation import BomRelationSrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.scheduler.key_part_identify_service import KeyPartIdentifyService


@pytest.mark.asyncio
async def test_selects_longest_cycle_part(db_session):
    # BOM: assembly COMP001 has two child self-made parts
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="COMP001", bom_component_no="PART_A",
        bom_component_desc="铸件A", bom_level=3,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="COMP001", bom_component_no="PART_B",
        bom_component_desc="铸件B", bom_level=3,
        is_self_made=True, part_type="自产件",
    ))

    # Baselines
    db_session.add(PartCycleBaseline(
        material_no="PART_A", material_desc="铸件A",
        core_part_name="铸件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("10"),
        unit_cycle_days=Decimal("10"), is_active=True,
    ))
    db_session.add(PartCycleBaseline(
        material_no="PART_B", material_desc="铸件B",
        core_part_name="铸件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("20"),
        unit_cycle_days=Decimal("20"), is_active=True,
    ))
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    result = await service.identify(
        machine_material_no="MACH001",
        assembly_bom_component_no="COMP001",
        machine_model="MC1-80",
    )

    assert result is not None
    assert result["key_part_material_no"] == "PART_B"
    assert result["key_part_cycle_days"] == Decimal("20")
    assert result["is_default"] is False


@pytest.mark.asyncio
async def test_default_when_no_baseline(db_session):
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="COMP001", bom_component_no="PART_C",
        bom_component_desc="零件C", bom_level=3,
        is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    result = await service.identify(
        machine_material_no="MACH001",
        assembly_bom_component_no="COMP001",
        machine_model="MC1-80",
    )

    assert result is not None
    assert result["key_part_cycle_days"] == Decimal("1")
    assert result["is_default"] is True


@pytest.mark.asyncio
async def test_no_self_made_children(db_session):
    # Only purchased parts
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="COMP001", bom_component_no="PURCH_A",
        bom_component_desc="外购件A", bom_level=3,
        is_self_made=False, part_type="外购件",
    ))
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    result = await service.identify(
        machine_material_no="MACH001",
        assembly_bom_component_no="COMP001",
        machine_model="MC1-80",
    )

    assert result is None
```

- [ ] **Step 2: Implement KeyPartIdentifyService**

```python
# app/scheduler/key_part_identify_service.py
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.text_parse_utils import extract_chinese_prefix
from app.models.bom_relation import BomRelationSrc
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo

logger = logging.getLogger(__name__)

_DEFAULT_PART_CYCLE_DAYS = Decimal("1")


class KeyPartIdentifyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.baseline_repo = PartCycleBaselineRepo(session)

    async def identify(
        self,
        machine_material_no: str,
        assembly_bom_component_no: str,
        machine_model: str,
    ) -> dict[str, Any] | None:
        """Find the key self-made part (longest cycle) for an assembly."""
        # Find direct children of this assembly component
        stmt = select(BomRelationSrc).where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                BomRelationSrc.material_no == assembly_bom_component_no,
                BomRelationSrc.is_self_made == True,
            )
        )
        result = await self.session.execute(stmt)
        children = result.scalars().all()

        if not children:
            return None

        # Look up cycle for each child, pick the longest
        best: dict[str, Any] | None = None
        best_cycle = Decimal("-1")

        for child in children:
            cycle, is_default, match_rule = await self._get_part_cycle(
                child.bom_component_no, machine_model, child.bom_component_desc
            )
            if cycle > best_cycle:
                best_cycle = cycle
                best = {
                    "key_part_material_no": child.bom_component_no,
                    "key_part_name": child.bom_component_desc,
                    "key_part_raw_material_desc": child.bom_component_desc,
                    "key_part_cycle_days": cycle,
                    "is_default": is_default,
                    "match_rule": match_rule,
                }

        return best

    async def _get_part_cycle(
        self, material_no: str, machine_model: str, desc: str | None
    ) -> tuple[Decimal, bool, str]:
        """Get part cycle days. Returns (days, is_default, match_rule)."""
        # Exact match
        baseline = await self.baseline_repo.find_by_model_and_material(
            machine_model, material_no
        )
        if baseline:
            return baseline.cycle_days, False, "exact_material"

        # Fuzzy match by description prefix
        if desc:
            prefix = extract_chinese_prefix(desc)
            if prefix:
                baseline = await self.baseline_repo.find_by_model_and_desc_prefix(
                    machine_model, prefix
                )
                if baseline:
                    return baseline.cycle_days, False, "desc_prefix"

        return _DEFAULT_PART_CYCLE_DAYS, True, "default"
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_scheduler/test_key_part_identify_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/scheduler/key_part_identify_service.py tests/test_scheduler/test_key_part_identify_service.py
git commit -m "feat: add key part identify service with fallback matching"
```

---

### Task 7: Scheduler — Machine Schedule Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/scheduler/machine_schedule_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/test_machine_schedule_service.py`

**Key rules:**
- `planned_end_date = confirmed_delivery_date`
- `planned_start_date = subtract_workdays(planned_end_date, machine_cycle_days)`
- `machine_assembly_days` from assembly_time_baseline (final assembly, default 3 days)
- Write result to `machine_schedule_result` via upsert

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler/test_machine_schedule_service.py
import pytest
from decimal import Decimal
from datetime import datetime, date

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline
from app.scheduler.machine_schedule_service import MachineScheduleService
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo


@pytest.mark.asyncio
async def test_build_machine_schedule(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        contract_no="HT001", customer_name="客户A",
        product_series="MC1", product_model="MC1-80",
        product_name="压力机", material_no="MACH001",
        quantity=Decimal("1"), order_no="SO001",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("60"),
        sample_count=5, is_active=True,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))
    await db_session.commit()

    service = MachineScheduleService(db_session, today=date(2026, 3, 17))
    result = await service.build(order.id)
    await db_session.commit()

    assert result is not None
    assert result.planned_end_date.date() == date(2026, 6, 30)
    assert result.machine_cycle_days == Decimal("60")
    assert result.machine_assembly_days == Decimal("3")
    assert result.planned_start_date is not None
    assert result.schedule_status == "scheduled"


@pytest.mark.asyncio
async def test_default_final_assembly(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002", sap_line_no="10",
        product_model="MC2-100", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.commit()

    service = MachineScheduleService(db_session, today=date(2026, 3, 17))
    result = await service.build(order.id)
    await db_session.commit()

    # No baseline → default 90 days; no assembly time → default 3 days
    assert result is not None
    assert result.machine_assembly_days == Decimal("3")
```

- [ ] **Step 2: Implement MachineScheduleService**

```python
# app/scheduler/machine_schedule_service.py
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.calendar_utils import subtract_workdays
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_schedule_result import MachineScheduleResult
from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.repository.assembly_time_repo import AssemblyTimeRepo
from app.repository.work_calendar_repo import WorkCalendarRepo

logger = logging.getLogger(__name__)

_DEFAULT_MACHINE_CYCLE_DAYS = Decimal("90")
_DEFAULT_FINAL_ASSEMBLY_DAYS = Decimal("3")


class MachineScheduleService:
    def __init__(self, session: AsyncSession, today: date | None = None):
        self.session = session
        self.today = today or date.today()
        self.baseline_repo = MachineCycleBaselineRepo(session)
        self.result_repo = MachineScheduleResultRepo(session)
        self.assembly_repo = AssemblyTimeRepo(session)
        self.assembly_default = AssemblyTimeDefaultService(session)
        self.calendar_repo = WorkCalendarRepo(session)

    async def build(self, order_line_id: int) -> MachineScheduleResult | None:
        """Build and save machine schedule for an order."""
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order or not order.confirmed_delivery_date:
            return None

        calendar = await self.calendar_repo.get_calendar_map()

        # Get machine cycle
        machine_cycle, is_default_cycle = await self._get_machine_cycle(
            order.product_model, order.quantity
        )

        # Get final assembly time
        assembly_days, is_default_assembly = await self._get_final_assembly_time(
            order.product_model, order.product_series
        )

        # Compute dates
        delivery = order.confirmed_delivery_date
        if isinstance(delivery, datetime):
            delivery_date = delivery.date()
        else:
            delivery_date = delivery

        planned_end = delivery_date
        planned_start = subtract_workdays(planned_end, int(machine_cycle), calendar)
        trigger_date = subtract_workdays(planned_end, int(machine_cycle), calendar)

        # Build default flags
        default_flags = {}
        if is_default_cycle:
            default_flags["machine_cycle"] = True
        if is_default_assembly:
            default_flags["final_assembly_time"] = True

        data = {
            "contract_no": order.contract_no,
            "customer_name": order.customer_name,
            "product_series": order.product_series,
            "product_model": order.product_model,
            "product_name": order.product_name,
            "material_no": order.material_no,
            "quantity": order.quantity,
            "order_no": order.order_no,
            "sap_code": order.sap_code,
            "sap_line_no": order.sap_line_no,
            "delivery_plant": order.delivery_plant,
            "confirmed_delivery_date": order.confirmed_delivery_date,
            "drawing_released": order.drawing_released,
            "drawing_release_date": order.drawing_release_date,
            "schedule_date": datetime.now(),
            "trigger_date": datetime.combine(trigger_date, datetime.min.time()),
            "machine_cycle_days": machine_cycle,
            "machine_assembly_days": assembly_days,
            "planned_start_date": datetime.combine(planned_start, datetime.min.time()),
            "planned_end_date": datetime.combine(planned_end, datetime.min.time()),
            "schedule_status": "scheduled",
            "warning_level": "normal",
            "default_flags": default_flags if default_flags else None,
        }

        result = await self.result_repo.upsert_by_order_line_id(order_line_id, data)
        return result

    async def _get_machine_cycle(
        self, machine_model: str | None, quantity: Decimal | None
    ) -> tuple[Decimal, bool]:
        if not machine_model:
            return _DEFAULT_MACHINE_CYCLE_DAYS, True

        qty = quantity or Decimal("1")
        baseline = await self.baseline_repo.find_by_model_and_qty(machine_model, qty)
        if baseline:
            return baseline.cycle_days_median, False

        all_baselines = await self.baseline_repo.find_all_by_model(machine_model)
        if all_baselines:
            nearest = min(all_baselines, key=lambda b: abs(b.order_qty - qty))
            coefficient = float(qty) / float(nearest.order_qty) if nearest.order_qty else 1.0
            adjusted = Decimal(str(round(float(nearest.cycle_days_median) * coefficient, 4)))
            return adjusted, False

        return _DEFAULT_MACHINE_CYCLE_DAYS, True

    async def _get_final_assembly_time(
        self, machine_model: str | None, product_series: str | None
    ) -> tuple[Decimal, bool]:
        if not machine_model:
            return _DEFAULT_FINAL_ASSEMBLY_DAYS, True

        existing = await self.assembly_repo.find_final_assembly(machine_model)
        if existing:
            return existing.assembly_time_days, existing.is_default

        # Create default
        record = await self.assembly_default.ensure_default(
            machine_model=machine_model,
            product_series=product_series,
            assembly_name="整机总装",
            is_final_assembly=True,
        )
        return record.assembly_time_days, True
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_scheduler/test_machine_schedule_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/scheduler/machine_schedule_service.py tests/test_scheduler/test_machine_schedule_service.py
git commit -m "feat: add machine schedule service with backward date computation"
```

---

### Task 8: Scheduler — Part Schedule Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/scheduler/part_schedule_service.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/test_part_schedule_service.py`

**Key rules:**
- For each assembly (by production_sequence), compute key part schedule
- Same sequence = parallel (same end date)
- Backward from machine planned_end_date, subtract assembly times in sequence order
- Key part planned_end_date = assembly's end point
- Key part planned_start_date = subtract_workdays(end, key_part_cycle_days)
- Delete existing part results, then insert

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler/test_part_schedule_service.py
import pytest
from decimal import Decimal
from datetime import datetime, date

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.bom_relation import BomRelationSrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.scheduler.part_schedule_service import PartScheduleService
from app.repository.part_schedule_result_repo import PartScheduleResultRepo


@pytest.mark.asyncio
async def test_build_part_schedules(db_session):
    # Setup order
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH001", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.flush()

    # Machine schedule result
    msr = MachineScheduleResult(
        order_line_id=order.id,
        product_model="MC1-80",
        planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    )
    db_session.add(msr)

    # BOM: machine -> assembly (level 2) -> part (level 3)
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="MACH001", bom_component_no="ASM_BODY",
        bom_component_desc="机身组件", bom_level=2,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="ASM_BODY", bom_component_no="PART_CAST",
        bom_component_desc="铸件机身", bom_level=3,
        is_self_made=True, part_type="自产件",
    ))

    # Assembly time
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="机身",
        assembly_time_days=Decimal("2"), production_sequence=1,
        is_final_assembly=False,
    ))

    # Part baseline
    db_session.add(PartCycleBaseline(
        material_no="PART_CAST", material_desc="铸件机身",
        core_part_name="铸件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("15"),
        unit_cycle_days=Decimal("15"), is_active=True,
    ))
    await db_session.commit()

    service = PartScheduleService(db_session)
    parts = await service.build(order.id, msr.id)
    await db_session.commit()

    assert len(parts) >= 1
    body_part = [p for p in parts if p.assembly_name == "机身"][0]
    assert body_part.key_part_material_no == "PART_CAST"
    assert body_part.key_part_cycle_days == Decimal("15")
    assert body_part.planned_end_date is not None
    assert body_part.planned_start_date is not None
```

- [ ] **Step 2: Implement PartScheduleService**

```python
# app/scheduler/part_schedule_service.py
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.calendar_utils import subtract_workdays
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_schedule_result import PartScheduleResult
from app.scheduler.assembly_identify_service import AssemblyIdentifyService
from app.scheduler.key_part_identify_service import KeyPartIdentifyService
from app.repository.part_schedule_result_repo import PartScheduleResultRepo
from app.repository.work_calendar_repo import WorkCalendarRepo

logger = logging.getLogger(__name__)


class PartScheduleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.assembly_service = AssemblyIdentifyService(session)
        self.key_part_service = KeyPartIdentifyService(session)
        self.result_repo = PartScheduleResultRepo(session)
        self.calendar_repo = WorkCalendarRepo(session)

    async def build(
        self,
        order_line_id: int,
        machine_schedule_id: int,
    ) -> list[PartScheduleResult]:
        """Build part schedules for all assemblies of an order."""
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        msr = await self.session.get(MachineScheduleResult, machine_schedule_id)
        if not order or not msr:
            return []

        calendar = await self.calendar_repo.get_calendar_map()

        # Identify assemblies
        assemblies = await self.assembly_service.identify(
            machine_material_no=order.material_no or "",
            machine_model=order.product_model or "",
            product_series=order.product_series,
        )

        if not assemblies:
            return []

        # Machine end date
        machine_end = msr.planned_end_date
        if isinstance(machine_end, datetime):
            machine_end_date = machine_end.date()
        else:
            machine_end_date = machine_end

        # Delete existing part results
        await self.result_repo.delete_by_order_line_id(order_line_id)

        # Backward schedule: group by production_sequence
        # Same sequence = parallel, different sequence = sequential
        seq_groups: dict[int, list[dict]] = {}
        for asm in assemblies:
            seq = asm["production_sequence"]
            seq_groups.setdefault(seq, []).append(asm)

        sorted_seqs = sorted(seq_groups.keys(), reverse=True)  # highest seq first (closest to end)

        # Walk backward from machine end date
        current_end_date = machine_end_date
        # First subtract final assembly time
        final_asm_days = int(msr.machine_assembly_days or 3)
        current_end_date = subtract_workdays(current_end_date, final_asm_days, calendar)

        results = []
        for seq in sorted_seqs:
            group = seq_groups[seq]
            # All assemblies in this group share the same end date (parallel)
            group_end_date = current_end_date

            max_assembly_time = Decimal("0")
            for asm in group:
                # Find key part
                key_part = await self.key_part_service.identify(
                    machine_material_no=order.material_no or "",
                    assembly_bom_component_no=asm["bom_component_no"],
                    machine_model=order.product_model or "",
                )

                part_end = group_end_date
                part_start = part_end
                key_part_cycle = Decimal("0")
                key_part_data: dict[str, Any] = {}
                is_default_part = False
                match_rule = ""

                if key_part:
                    key_part_cycle = key_part["key_part_cycle_days"]
                    part_start = subtract_workdays(part_end, int(key_part_cycle), calendar)
                    key_part_data = key_part
                    is_default_part = key_part["is_default"]
                    match_rule = key_part["match_rule"]

                asm_time = asm["assembly_time_days"]
                if asm_time > max_assembly_time:
                    max_assembly_time = asm_time

                default_flags = {}
                if asm["is_default_time"]:
                    default_flags["assembly_time"] = True
                if is_default_part:
                    default_flags["key_part_cycle"] = True

                entity = PartScheduleResult(
                    order_line_id=order_line_id,
                    machine_schedule_id=machine_schedule_id,
                    assembly_name=asm["assembly_name"],
                    production_sequence=asm["production_sequence"],
                    assembly_time_days=asm_time,
                    assembly_is_default=asm["is_default_time"],
                    key_part_material_no=key_part_data.get("key_part_material_no"),
                    key_part_name=key_part_data.get("key_part_name"),
                    key_part_raw_material_desc=key_part_data.get("key_part_raw_material_desc"),
                    key_part_cycle_days=key_part_cycle if key_part else None,
                    key_part_is_default=is_default_part,
                    cycle_match_rule=match_rule,
                    planned_start_date=datetime.combine(part_start, datetime.min.time()) if key_part else None,
                    planned_end_date=datetime.combine(part_end, datetime.min.time()),
                    warning_level="normal",
                    default_flags=default_flags if default_flags else None,
                )
                self.session.add(entity)
                results.append(entity)

            # Move end date backward by the max assembly time in this group
            current_end_date = subtract_workdays(current_end_date, int(max_assembly_time), calendar)

        await self.session.flush()
        return results
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_scheduler/test_part_schedule_service.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/scheduler/part_schedule_service.py tests/test_scheduler/test_part_schedule_service.py
git commit -m "feat: add part schedule service with backward scheduling by sequence"
```

---

### Task 9: Scheduler — Schedule Orchestrator

**Files:**
- Create: `auto-scheduling-system/services/api/app/scheduler/schedule_orchestrator.py`
- Test: `auto-scheduling-system/services/api/tests/test_scheduler/test_schedule_orchestrator.py`

**Key rules:**
- Coordinate full scheduling for one order:
  1. Check schedulability
  2. Build machine schedule
  3. Build part schedules
  4. Record any data issues
- Support batch scheduling
- Return summary result

- [ ] **Step 1: Write failing test**

```python
# tests/test_scheduler/test_schedule_orchestrator.py
import pytest
from decimal import Decimal
from datetime import datetime, date

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.repository.part_schedule_result_repo import PartScheduleResultRepo


@pytest.mark.asyncio
async def test_full_schedule_single_order(db_session):
    # Setup complete data
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        contract_no="HT001", customer_name="客户A",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH001", quantity=Decimal("1"),
        order_no="SO001",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)

    # Baseline
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("60"),
        sample_count=5, is_active=True,
    ))

    # BOM
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="MACH001", bom_component_no="ASM_BODY",
        bom_component_desc="机身组件", bom_level=2,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="ASM_BODY", bom_component_no="PART_CAST",
        bom_component_desc="铸件机身", bom_level=3,
        is_self_made=True, part_type="自产件",
    ))

    # Assembly time
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))

    # Part baseline
    db_session.add(PartCycleBaseline(
        material_no="PART_CAST", material_desc="铸件机身",
        core_part_name="铸件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("15"),
        unit_cycle_days=Decimal("15"), is_active=True,
    ))
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 3, 17))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    assert result["success"] is True
    assert result["machine_schedule"] is not None
    assert len(result["part_schedules"]) >= 1


@pytest.mark.asyncio
async def test_skip_not_schedulable(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002", sap_line_no="10",
        product_model="MC1-80",
        confirmed_delivery_date=None,  # missing
        drawing_released=False,
    )
    db_session.add(order)
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 3, 17))
    result = await orchestrator.schedule_order(order.id)

    assert result["success"] is False
    assert result["reason"] is not None


@pytest.mark.asyncio
async def test_batch_schedule(db_session):
    orders = []
    for i in range(3):
        o = SalesPlanOrderLineSrc(
            sap_code=f"SAP00{i}", sap_line_no="10",
            product_model="MC1-80", quantity=Decimal("1"),
            material_no="MACH001",
            confirmed_delivery_date=datetime(2026, 6, 30),
            drawing_released=True,
        )
        db_session.add(o)
        orders.append(o)
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 3, 17))
    batch_result = await orchestrator.schedule_batch([o.id for o in orders])
    await db_session.commit()

    assert batch_result["total"] == 3
    assert batch_result["scheduled"] + batch_result["failed"] == 3
```

- [ ] **Step 2: Implement ScheduleOrchestrator**

```python
# app/scheduler/schedule_orchestrator.py
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.scheduler.schedule_check_service import ScheduleCheckService
from app.scheduler.machine_schedule_service import MachineScheduleService
from app.scheduler.part_schedule_service import PartScheduleService

logger = logging.getLogger(__name__)


class ScheduleOrchestrator:
    def __init__(self, session: AsyncSession, today: date | None = None):
        self.session = session
        self.today = today or date.today()
        self.check_service = ScheduleCheckService(session, today=self.today)
        self.machine_service = MachineScheduleService(session, today=self.today)
        self.part_service = PartScheduleService(session)

    async def schedule_order(self, order_line_id: int) -> dict[str, Any]:
        """Full scheduling for a single order."""
        # Step 1: Check schedulability
        check = await self.check_service.check(order_line_id)
        if not check.get("is_schedulable"):
            return {
                "success": False,
                "order_line_id": order_line_id,
                "reason": check.get("reason", check.get("status")),
                "status": check.get("status"),
                "machine_schedule": None,
                "part_schedules": [],
            }

        # Step 2: Build machine schedule
        machine_result = await self.machine_service.build(order_line_id)
        if not machine_result:
            return {
                "success": False,
                "order_line_id": order_line_id,
                "reason": "Failed to build machine schedule",
                "machine_schedule": None,
                "part_schedules": [],
            }

        # Step 3: Build part schedules
        part_results = await self.part_service.build(
            order_line_id, machine_result.id
        )

        return {
            "success": True,
            "order_line_id": order_line_id,
            "machine_schedule": machine_result,
            "part_schedules": part_results,
        }

    async def schedule_batch(
        self, order_line_ids: list[int]
    ) -> dict[str, Any]:
        """Schedule a batch of orders."""
        scheduled = 0
        failed = 0
        results = []

        for oid in order_line_ids:
            try:
                result = await self.schedule_order(oid)
                if result["success"]:
                    scheduled += 1
                else:
                    failed += 1
                results.append(result)
            except Exception as e:
                logger.error(f"Scheduling failed for order {oid}: {e}")
                failed += 1
                results.append({
                    "success": False,
                    "order_line_id": oid,
                    "reason": str(e),
                })

        return {
            "total": len(order_line_ids),
            "scheduled": scheduled,
            "failed": failed,
            "results": results,
        }
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_scheduler/test_schedule_orchestrator.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/scheduler/schedule_orchestrator.py tests/test_scheduler/test_schedule_orchestrator.py
git commit -m "feat: add schedule orchestrator for single and batch scheduling"
```

---

### Task 10: Run Full Test Suite + Final Commit

- [ ] **Step 1: Run all tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS (approx 60-70 tests)

- [ ] **Step 2: Final commit if anything missed**

```bash
git status
# If clean, no commit needed
```

---

## Phase 3 Completion Checklist

After completing all tasks above, you should have:

- [x] MachineCycleBaselineService: group by model+qty, compute median
- [x] PartCycleBaselineService: compute from completed production orders
- [x] AssemblyTimeDefaultService: ensure defaults with sequence mapping
- [x] ScheduleCheckService: 3 conditions + trigger date computation
- [x] AssemblyIdentifyService: BOM 2nd level + exclusion filtering
- [x] KeyPartIdentifyService: longest cycle self-made part with fallback
- [x] MachineScheduleService: backward date computation + upsert
- [x] PartScheduleService: backward scheduling by sequence with parallel groups
- [x] ScheduleOrchestrator: single + batch scheduling coordination
- [x] Full test suite passing

**Next:** Proceed to Phase 4 plan (API Layer — REST endpoints, export, admin).
