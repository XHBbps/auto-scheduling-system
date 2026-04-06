import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.calendar_utils import subtract_workdays
from app.common.plant_utils import normalize_plant
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.bom_relation_repo import BomRelationRepo
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo
from app.repository.work_calendar_repo import WorkCalendarRepo
from app.services.schedule_constraint_read_service import ScheduleConstraintReadService

logger = logging.getLogger(__name__)

_DEFAULT_MACHINE_CYCLE_DAYS = Decimal("90")


class ScheduleCheckService:
    def __init__(self, session: AsyncSession, today: date | None = None):
        self.session = session
        self.today = today or date.today()
        self.bom_repo = BomRelationRepo(session)
        self.baseline_repo = MachineCycleBaselineRepo(session)
        self.calendar_repo = WorkCalendarRepo(session)
        self.constraint_read_service = ScheduleConstraintReadService(session)

    async def check(self, order_line_id: int) -> dict[str, Any]:
        """Check if an order is schedulable. Returns status dict."""
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order:
            return {"is_schedulable": False, "status": "not_found", "reason": "Order not found"}

        return await self.check_order(order)

    async def check_order(
        self,
        order: SalesPlanOrderLineSrc,
        *,
        bom_material_pairs: set[tuple[str, str]] | None = None,
        bom_materials: set[str] | None = None,
        baselines_by_model: dict[str, list[MachineCycleBaseline]] | None = None,
        calendar: dict[date, bool] | None = None,
    ) -> dict[str, Any]:
        if not order:
            return {"is_schedulable": False, "status": "not_found", "reason": "Order not found"}

        resource_snapshot = await self.constraint_read_service.build_order_resource_snapshot(order)

        # Condition 1: delivery date
        if not order.confirmed_delivery_date:
            return {
                "is_schedulable": False,
                "status": "pending_delivery",
                "reason": "No confirmed delivery date",
                "resource_snapshot": resource_snapshot,
            }

        # Condition 2: drawing released
        if not order.drawing_released:
            return {
                "is_schedulable": False,
                "status": "pending_drawing",
                "reason": "Drawing not released",
                "resource_snapshot": resource_snapshot,
            }

        # Condition 2.5: BOM ready
        has_bom = (
            bool(
                order.material_no
                and (
                    (
                        bom_material_pairs is not None
                        and (order.material_no, normalize_plant(order.delivery_plant)) in bom_material_pairs
                    )
                    or (bom_materials is not None and order.material_no in bom_materials)
                )
            )
            if bom_material_pairs is not None or bom_materials is not None
            else bool(
                order.material_no and await self.bom_repo.has_machine_bom(order.material_no, order.delivery_plant)
            )
        )
        if not has_bom:
            return {
                "is_schedulable": False,
                "status": "missing_bom",
                "reason": "BOM not found",
                "resource_snapshot": resource_snapshot,
            }

        # Compute trigger date
        machine_cycle_days, is_default = await self._get_machine_cycle(
            order.product_model,
            order.quantity,
            baselines_by_model=baselines_by_model,
        )
        calendar_map = calendar or await self._get_calendar(order.confirmed_delivery_date)
        delivery = order.confirmed_delivery_date
        if isinstance(delivery, datetime):
            delivery = delivery.date()

        trigger_date = subtract_workdays(delivery, int(machine_cycle_days), calendar_map)
        resource_snapshot = await self.constraint_read_service.build_order_resource_snapshot(
            order,
            trigger_date=trigger_date,
            machine_cycle_days=machine_cycle_days,
        )

        # Condition 3: trigger date reached
        if self.today < trigger_date:
            return {
                "is_schedulable": False,
                "status": "pending_trigger",
                "trigger_date": trigger_date,
                "machine_cycle_days": machine_cycle_days,
                "is_default_cycle": is_default,
                "resource_snapshot": resource_snapshot,
            }

        return {
            "is_schedulable": True,
            "status": "schedulable",
            "trigger_date": trigger_date,
            "machine_cycle_days": machine_cycle_days,
            "is_default_cycle": is_default,
            "resource_snapshot": resource_snapshot,
        }

    async def _get_machine_cycle(
        self,
        machine_model: str | None,
        quantity: Decimal | None,
        *,
        baselines_by_model: dict[str, list[MachineCycleBaseline]] | None = None,
    ) -> tuple[Decimal, bool]:
        """Get machine cycle days. Returns (days, is_default)."""
        if not machine_model:
            return _DEFAULT_MACHINE_CYCLE_DAYS, True

        qty = quantity or Decimal("1")

        if baselines_by_model is not None:
            all_baselines = baselines_by_model.get(machine_model) or []
            exact = next((baseline for baseline in all_baselines if baseline.order_qty == qty), None)
            if exact:
                return exact.cycle_days_median, False
            if all_baselines:
                nearest = min(all_baselines, key=lambda b: abs(b.order_qty - qty))
                coefficient = float(qty) / float(nearest.order_qty) if nearest.order_qty else 1.0
                adjusted = Decimal(str(round(float(nearest.cycle_days_median) * coefficient, 4)))
                return adjusted, False
            return _DEFAULT_MACHINE_CYCLE_DAYS, True

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

    async def _get_calendar(self, delivery_date: datetime | date) -> dict[date, bool]:
        """Load work calendar covering a reasonable range."""
        end = delivery_date.date() if isinstance(delivery_date, datetime) else delivery_date
        from datetime import timedelta

        start = self.today - timedelta(days=30)
        end = end + timedelta(days=30)
        return await self.calendar_repo.get_calendar_map(start, end)
