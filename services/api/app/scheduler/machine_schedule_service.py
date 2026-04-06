import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.common.calendar_utils import subtract_workdays
from app.common.datetime_utils import utc_now
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.assembly_time_repo import AssemblyTimeRepo
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
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

        # Get machine cycle
        machine_cycle, is_default_cycle = await self._get_machine_cycle(order.product_model, order.quantity)

        # Get final assembly time
        assembly_days, is_default_assembly = await self._get_final_assembly_time(
            order.product_model, order.product_series
        )

        # Compute dates
        delivery = order.confirmed_delivery_date
        delivery_date = delivery.date() if isinstance(delivery, datetime) else delivery

        # Load calendar for the range
        start_range = delivery_date - timedelta(days=int(machine_cycle) * 2 + 60)
        end_range = delivery_date + timedelta(days=30)
        calendar = await self.calendar_repo.get_calendar_map(start_range, end_range)

        planned_end = delivery_date
        planned_start = subtract_workdays(planned_end, int(machine_cycle), calendar)
        trigger_date = planned_start

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
            "schedule_date": utc_now(),
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

    async def _get_machine_cycle(self, machine_model: str | None, quantity: Decimal | None) -> tuple[Decimal, bool]:
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

        record = await self.assembly_default.ensure_default(
            machine_model=machine_model,
            product_series=product_series,
            assembly_name="整机总装",
            is_final_assembly=True,
        )
        return record.assembly_time_days, True
