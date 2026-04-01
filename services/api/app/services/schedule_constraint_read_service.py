from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.plant_utils import normalize_plant
from app.models.sales_plan import SalesPlanOrderLineSrc


class ScheduleConstraintReadService:
    """Reserved read layer for future inventory and capacity validation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def build_order_resource_snapshot(
        self,
        order: SalesPlanOrderLineSrc,
        *,
        trigger_date: date | None = None,
        machine_cycle_days: Decimal | None = None,
    ) -> dict[str, Any]:
        delivery_date = self._to_date(getattr(order, "confirmed_delivery_date", None))
        plant = normalize_plant(getattr(order, "delivery_plant", None))
        cycle_text = str(machine_cycle_days) if machine_cycle_days is not None else None

        return {
            "inventory": {
                "status": "not_integrated",
                "blocking": False,
                "source": "reserved_read_layer",
                "material_no": getattr(order, "material_no", None),
                "plant": plant,
            },
            "capacity": {
                "status": "not_integrated",
                "blocking": False,
                "source": "reserved_read_layer",
                "product_model": getattr(order, "product_model", None),
                "plant": plant,
                "delivery_date": delivery_date.isoformat() if delivery_date else None,
                "trigger_date": trigger_date.isoformat() if trigger_date else None,
                "machine_cycle_days": cycle_text,
            },
        }

    @staticmethod
    def _to_date(value: datetime | date | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value
