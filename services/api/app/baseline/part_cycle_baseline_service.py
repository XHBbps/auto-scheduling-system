from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.part_cycle_precision import normalize_part_cycle_days, normalize_part_unit_cycle_days
from app.common.text_parse_utils import extract_part_type
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.production_order import ProductionOrderHistorySrc
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

logger = logging.getLogger(__name__)

_DECIMAL_4 = Decimal("0.0001")
_DECIMAL_6 = Decimal("0.000001")
_MIN_SAMPLE_COUNT = 1
_MAX_VARIANCE_RATIO = Decimal("2")


class PartCycleBaselineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PartCycleBaselineRepo(session)

    async def rebuild(
        self,
        *,
        persist_changes: bool = True,
        refresh_source: str = "part_cycle_baseline_rebuild",
        refresh_reason: str = "part_cycle_baseline_rebuild",
    ) -> dict[str, Any]:
        rows = await self._load_completed_production_orders()
        grouped_entries, collection_stats = self._collect_group_entries(rows)
        promoted_rows, promoted_keys, summary = self._build_promoted_rows(grouped_entries, collection_stats)

        if not persist_changes:
            return {
                **summary,
                "groups_processed": summary["promoted_groups"],
                "persisted_groups": 0,
                "unchanged_groups": 0,
                "manual_protected_groups": 0,
                "deactivated_groups": 0,
                "snapshot_refresh": self._empty_refresh_summary(),
            }

        existing_by_key = await self.repo.list_by_scopes(list(promoted_keys))
        history_rows = await self.repo.list_active_history()

        rows_to_upsert: list[dict[str, Any]] = []
        kept_history_keys: set[tuple[str, str, str | None]] = set()
        changed_keys: set[tuple[str, str, str | None]] = set()
        unchanged_groups = 0
        manual_protected_groups = 0

        for row in promoted_rows:
            key = self._scope_key(row)
            existing = existing_by_key.get(key)
            if existing is not None and existing.cycle_source == "manual":
                manual_protected_groups += 1
                continue
            if existing is not None and not self._history_row_changed(existing, row):
                kept_history_keys.add(key)
                unchanged_groups += 1
                continue
            rows_to_upsert.append(row)
            kept_history_keys.add(key)
            changed_keys.add(key)

        await self.repo.bulk_upsert_history_rows(rows_to_upsert)

        stale_history_ids: list[int] = []
        for existing in history_rows:
            key = self._scope_key_from_model(existing)
            if key in kept_history_keys:
                continue
            stale_history_ids.append(existing.id)
            changed_keys.add(key)

        deactivated_groups = await self.repo.deactivate_history_ids(stale_history_ids)
        await self.session.flush()

        refresh_summary = self._empty_refresh_summary()
        if changed_keys:
            refresh_summary = await self._refresh_changed_keys(
                changed_keys,
                source=refresh_source,
                reason=refresh_reason,
            )

        return {
            **summary,
            "groups_processed": summary["promoted_groups"],
            "persisted_groups": len(rows_to_upsert),
            "unchanged_groups": unchanged_groups,
            "manual_protected_groups": manual_protected_groups,
            "deactivated_groups": deactivated_groups,
            "snapshot_refresh": refresh_summary,
        }

    async def _load_completed_production_orders(self) -> list[ProductionOrderHistorySrc]:
        stmt = select(ProductionOrderHistorySrc).where(
            and_(
                ProductionOrderHistorySrc.order_status == "已完工",
                ProductionOrderHistorySrc.start_time_actual.is_not(None),
                ProductionOrderHistorySrc.finish_time_actual.is_not(None),
                ProductionOrderHistorySrc.production_qty.is_not(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def _collect_group_entries(
        self,
        rows: list[ProductionOrderHistorySrc],
    ) -> tuple[dict[tuple[str, str, str], list[dict[str, Any]]], dict[str, int]]:
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        skipped_missing_scope = 0
        skipped_invalid_cycle = 0
        eligible_orders = 0

        for row in rows:
            machine_model = (row.machine_model or "").strip()
            plant = (row.plant or "").strip()
            part_type = extract_part_type(row.material_desc or "")
            if not machine_model or not plant or not part_type:
                skipped_missing_scope += 1
                continue

            cycle_days = self._calculate_cycle_days(row.start_time_actual, row.finish_time_actual)
            if cycle_days is None or cycle_days <= 0:
                skipped_invalid_cycle += 1
                continue

            qty = row.production_qty or Decimal("1")
            if qty <= 0:
                skipped_invalid_cycle += 1
                continue

            unit_cycle_days = (cycle_days / qty).quantize(_DECIMAL_6, rounding=ROUND_HALF_UP)
            groups[(part_type, machine_model, plant)].append(
                {
                    "cycle_days": cycle_days,
                    "unit_cycle_days": unit_cycle_days,
                    "material_desc": (row.material_desc or "").strip(),
                    "batch_qty": qty.quantize(_DECIMAL_4, rounding=ROUND_HALF_UP),
                    "source_updated_at": row.last_modified_time_src or row.finish_time_actual,
                }
            )
            eligible_orders += 1

        return groups, {
            "total_orders": len(rows),
            "eligible_orders": eligible_orders,
            "eligible_groups": len(groups),
            "skipped_missing_scope": skipped_missing_scope,
            "skipped_invalid_cycle": skipped_invalid_cycle,
        }

    def _build_promoted_rows(
        self,
        groups: dict[tuple[str, str, str], list[dict[str, Any]]],
        collection_stats: dict[str, int],
    ) -> tuple[list[dict[str, Any]], set[tuple[str, str, str | None]], dict[str, Any]]:
        promoted_rows: list[dict[str, Any]] = []
        promoted_keys: set[tuple[str, str, str | None]] = set()
        skipped_low_sample = 0
        skipped_high_variance = 0
        stats_preview: list[dict[str, Any]] = []

        for (part_type, machine_model, plant), entries in groups.items():
            cycle_values = [entry["cycle_days"] for entry in entries]
            unit_cycle_values = [entry["unit_cycle_days"] for entry in entries]
            batch_values = [entry["batch_qty"] for entry in entries]
            sample_count = len(entries)
            variance_ratio = self._calculate_variance_ratio(cycle_values)
            representative_entry = self._pick_representative_entry(entries)

            stats_preview.append(
                {
                    "part_type": part_type,
                    "machine_model": machine_model,
                    "plant": plant,
                    "sample_count": sample_count,
                    "variance_ratio": float(variance_ratio),
                }
            )

            if sample_count < _MIN_SAMPLE_COUNT:
                skipped_low_sample += 1
                continue
            if variance_ratio > _MAX_VARIANCE_RATIO:
                skipped_high_variance += 1
                continue

            row = {
                "material_no": part_type,
                "material_desc": representative_entry["material_desc"] or part_type,
                "core_part_name": part_type,
                "machine_model": machine_model,
                "plant": plant,
                "ref_batch_qty": self._decimal_median(batch_values, _DECIMAL_4),
                "cycle_days": normalize_part_cycle_days(self._decimal_median(cycle_values, _DECIMAL_4)),
                "unit_cycle_days": normalize_part_unit_cycle_days(self._decimal_median(unit_cycle_values, _DECIMAL_6)),
                "sample_count": sample_count,
                "source_updated_at": representative_entry["source_updated_at"],
                "cycle_source": "history",
                "match_rule": "part_type_exact_with_plant",
                "confidence_level": self._resolve_confidence_level(sample_count, variance_ratio),
                "is_default": False,
                "is_active": True,
                "remark": f"历史回算自动生成（样本数={sample_count}，波动比={variance_ratio}）",
            }
            promoted_rows.append(row)
            promoted_keys.add(self._scope_key(row))

        summary = {
            **collection_stats,
            "promoted_groups": len(promoted_rows),
            "skipped_low_sample": skipped_low_sample,
            "skipped_high_variance": skipped_high_variance,
            "group_stats": stats_preview,
        }
        return promoted_rows, promoted_keys, summary

    async def _refresh_changed_keys(
        self,
        changed_keys: set[tuple[str, str, str | None]],
        *,
        source: str,
        reason: str,
    ) -> dict[str, int]:
        refresh_service = ScheduleSnapshotRefreshService(self.session)
        summary = self._empty_refresh_summary()
        for part_type, machine_model, plant in sorted(
            changed_keys,
            key=lambda item: (item[1], item[2] or "", item[0]),
        ):
            batch_result = await refresh_service.refresh_by_part_type(
                part_type,
                source=source,
                reason=reason,
                machine_model=machine_model,
                plant=plant,
            )
            summary = self._merge_refresh_summary(summary, batch_result)
        return summary

    @staticmethod
    def _calculate_cycle_days(start_time: datetime | None, finish_time: datetime | None) -> Decimal | None:
        if start_time is None or finish_time is None:
            return None
        total_seconds = finish_time.timestamp() - start_time.timestamp()
        if total_seconds <= 0:
            return None
        return (Decimal(str(total_seconds)) / Decimal("86400")).quantize(_DECIMAL_4, rounding=ROUND_HALF_UP)

    @staticmethod
    def _calculate_variance_ratio(values: list[Decimal]) -> Decimal:
        if not values:
            return Decimal("0")
        min_value = min(values)
        max_value = max(values)
        if min_value <= 0:
            return Decimal("999999")
        return (max_value / min_value).quantize(_DECIMAL_4, rounding=ROUND_HALF_UP)

    @staticmethod
    def _pick_representative_entry(entries: list[dict[str, Any]]) -> dict[str, Any]:
        return max(entries, key=lambda item: item.get("source_updated_at") or datetime.min)

    @staticmethod
    def _decimal_median(values: list[Decimal], quant: Decimal) -> Decimal:
        numeric_values = [float(value) for value in values]
        return Decimal(str(median(numeric_values))).quantize(quant, rounding=ROUND_HALF_UP)

    @staticmethod
    def _resolve_confidence_level(sample_count: int, variance_ratio: Decimal) -> str:
        if sample_count >= 5 and variance_ratio <= Decimal("1.5"):
            return "high"
        return "medium"

    @staticmethod
    def _scope_key(data: dict[str, Any]) -> tuple[str, str, str | None]:
        plant = (data.get("plant") or "").strip() or None
        return data["material_no"], data["machine_model"], plant

    @staticmethod
    def _scope_key_from_model(item: PartCycleBaseline) -> tuple[str, str, str | None]:
        plant = (item.plant or "").strip() or None
        return item.material_no, item.machine_model, plant

    @staticmethod
    def _history_row_changed(existing: PartCycleBaseline, incoming: dict[str, Any]) -> bool:
        comparable_fields = (
            "material_desc",
            "core_part_name",
            "machine_model",
            "plant",
            "ref_batch_qty",
            "cycle_days",
            "unit_cycle_days",
            "sample_count",
            "source_updated_at",
            "cycle_source",
            "match_rule",
            "confidence_level",
            "is_default",
            "is_active",
            "remark",
        )
        for field in comparable_fields:
            existing_value = getattr(existing, field)
            incoming_value = incoming.get(field)
            if existing_value != incoming_value:
                return True
        return False

    @staticmethod
    def _empty_refresh_summary() -> dict[str, int]:
        return {
            "total": 0,
            "refreshed": 0,
            "scheduled": 0,
            "scheduled_stale": 0,
            "deleted": 0,
        }

    @classmethod
    def _merge_refresh_summary(cls, current: dict[str, int], incoming: dict[str, int]) -> dict[str, int]:
        merged = dict(current)
        for key in cls._empty_refresh_summary():
            merged[key] = int(merged.get(key, 0)) + int(incoming.get(key, 0))
        return merged
