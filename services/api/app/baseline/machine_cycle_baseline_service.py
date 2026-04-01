import logging
from collections import defaultdict
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo

logger = logging.getLogger(__name__)


class MachineCycleBaselineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MachineCycleBaselineRepo(session)

    async def rebuild(self) -> dict[str, Any]:
        """Rebuild all machine cycle baselines from history data."""
        await self.repo.deactivate_duplicate_active_rows()

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
