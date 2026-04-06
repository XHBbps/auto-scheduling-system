from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.part_cycle_precision import normalize_part_cycle_payload
from app.models.part_cycle_baseline import PartCycleBaseline
from app.repository.base import BaseRepository


class PartCycleBaselineRepo(BaseRepository[PartCycleBaseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PartCycleBaseline)

    async def find_by_model_and_material(
        self,
        machine_model: str,
        material_no: str,
        plant: str | None = None,
    ) -> PartCycleBaseline | None:
        return await self.find_by_model_and_part_type(machine_model, material_no, plant)

    async def find_by_model_and_part_type(
        self,
        machine_model: str,
        part_type: str,
        plant: str | None = None,
    ) -> PartCycleBaseline | None:
        stmt = (
            select(PartCycleBaseline)
            .where(
                PartCycleBaseline.machine_model == machine_model,
                PartCycleBaseline.material_no == part_type,
                PartCycleBaseline.is_active.is_(True),
            )
            .order_by(*self._lookup_order_by(plant))
        )
        stmt = self._apply_plant_lookup(stmt, plant)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def find_by_model_and_desc_prefix(
        self,
        machine_model: str,
        desc_prefix: str,
        plant: str | None = None,
    ) -> PartCycleBaseline | None:
        stmt = (
            select(PartCycleBaseline)
            .where(
                PartCycleBaseline.machine_model == machine_model,
                PartCycleBaseline.material_desc.startswith(desc_prefix),
                PartCycleBaseline.is_active.is_(True),
            )
            .order_by(*self._lookup_order_by(plant))
        )
        stmt = self._apply_plant_lookup(stmt, plant)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_active_by_model(
        self,
        machine_model: str,
        plant: str | None = None,
    ) -> Sequence[PartCycleBaseline]:
        stmt = (
            select(PartCycleBaseline)
            .where(
                PartCycleBaseline.machine_model == machine_model,
                PartCycleBaseline.is_active.is_(True),
            )
            .order_by(*self._lookup_order_by(plant), PartCycleBaseline.core_part_name.asc())
        )
        stmt = self._apply_plant_lookup(stmt, plant)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_by_scope(
        self,
        material_no: str,
        machine_model: str,
        plant: str | None,
    ) -> PartCycleBaseline | None:
        stmt = select(PartCycleBaseline).where(
            PartCycleBaseline.material_no == material_no,
            PartCycleBaseline.machine_model == machine_model,
            self._scope_plant_predicate(plant),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_scopes(
        self,
        scopes: Sequence[tuple[str, str, str | None]],
    ) -> dict[tuple[str, str, str | None], PartCycleBaseline]:
        normalized_scopes = [self._normalize_scope(scope) for scope in scopes]
        if not normalized_scopes:
            return {}
        stmt = select(PartCycleBaseline).where(
            or_(
                *[
                    and_(
                        PartCycleBaseline.material_no == material_no,
                        PartCycleBaseline.machine_model == machine_model,
                        self._scope_plant_predicate(plant),
                    )
                    for material_no, machine_model, plant in normalized_scopes
                ]
            )
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return {self._scope_key(row.material_no, row.machine_model, row.plant): row for row in rows}

    async def list_active_history(self) -> Sequence[PartCycleBaseline]:
        stmt = (
            select(PartCycleBaseline)
            .where(
                PartCycleBaseline.cycle_source == "history",
                PartCycleBaseline.is_active.is_(True),
            )
            .order_by(
                PartCycleBaseline.machine_model.asc(),
                PartCycleBaseline.material_no.asc(),
                PartCycleBaseline.plant.asc().nullsfirst(),
                PartCycleBaseline.id.asc(),
            )
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def deactivate_history_ids(self, ids: Sequence[int]) -> int:
        target_ids = [int(item) for item in ids if item is not None]
        if not target_ids:
            return 0
        stmt = update(PartCycleBaseline).where(PartCycleBaseline.id.in_(target_ids)).values(is_active=False)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def save_manual(
        self,
        *,
        record_id: int | None,
        data: dict[str, Any],
    ) -> PartCycleBaseline:
        normalized = normalize_part_cycle_payload(data)
        normalized["material_no"] = (normalized.get("material_no") or "").strip()
        normalized["core_part_name"] = (normalized.get("core_part_name") or normalized["material_no"]).strip()
        normalized["machine_model"] = (normalized.get("machine_model") or "").strip()
        normalized["plant"] = self._normalize_plant(normalized.get("plant"))

        entity = await self.session.get(PartCycleBaseline, int(record_id)) if record_id else None
        if entity is not None:
            for key, value in normalized.items():
                setattr(entity, key, value)
            await self.session.flush()
            return entity

        if self._is_postgresql():
            return await self._upsert_manual_postgresql(normalized)

        existing = await self.find_by_scope(
            normalized["material_no"],
            normalized["machine_model"],
            normalized.get("plant"),
        )
        if existing is not None:
            for key, value in normalized.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing

        entity = PartCycleBaseline(**normalized)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def bulk_upsert_history_rows(self, rows: Sequence[dict[str, Any]]) -> None:
        if not rows:
            return

        normalized_rows = [
            {
                **normalize_part_cycle_payload(row),
                "plant": self._normalize_plant(row.get("plant")),
            }
            for row in rows
        ]

        if not self._is_postgresql():
            await self._bulk_upsert_history_rows_fallback(normalized_rows)
            return

        table = PartCycleBaseline.__table__
        stmt = pg_insert(table).values(normalized_rows)
        excluded = stmt.excluded
        set_values = {
            "material_desc": excluded.material_desc,
            "core_part_name": excluded.core_part_name,
            "ref_batch_qty": excluded.ref_batch_qty,
            "cycle_days": excluded.cycle_days,
            "unit_cycle_days": excluded.unit_cycle_days,
            "sample_count": excluded.sample_count,
            "source_updated_at": excluded.source_updated_at,
            "cycle_source": excluded.cycle_source,
            "match_rule": excluded.match_rule,
            "confidence_level": excluded.confidence_level,
            "is_default": excluded.is_default,
            "is_active": excluded.is_active,
            "remark": excluded.remark,
            "updated_at": excluded.updated_at,
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pcb_material_machine_plant",
            set_=set_values,
            where=table.c.cycle_source != "manual",
        )
        await self.session.execute(stmt)

    async def _bulk_upsert_history_rows_fallback(self, rows: Sequence[dict[str, Any]]) -> None:
        for row in rows:
            existing = await self.find_by_scope(
                row["material_no"],
                row["machine_model"],
                row.get("plant"),
            )
            if existing is not None and existing.cycle_source == "manual":
                continue
            if existing is not None:
                for key, value in row.items():
                    setattr(existing, key, value)
                continue
            self.session.add(PartCycleBaseline(**row))
        await self.session.flush()

    async def _upsert_manual_postgresql(self, data: dict[str, Any]) -> PartCycleBaseline:
        table = PartCycleBaseline.__table__
        stmt = pg_insert(table).values(data)
        excluded = stmt.excluded
        set_values = {
            "material_desc": excluded.material_desc,
            "core_part_name": excluded.core_part_name,
            "ref_batch_qty": excluded.ref_batch_qty,
            "cycle_days": excluded.cycle_days,
            "unit_cycle_days": excluded.unit_cycle_days,
            "sample_count": excluded.sample_count,
            "source_updated_at": excluded.source_updated_at,
            "cycle_source": excluded.cycle_source,
            "match_rule": excluded.match_rule,
            "confidence_level": excluded.confidence_level,
            "is_default": excluded.is_default,
            "is_active": excluded.is_active,
            "remark": excluded.remark,
            "updated_at": excluded.updated_at,
        }

        if data.get("plant") is None:
            stmt = stmt.on_conflict_do_update(
                index_elements=[table.c.material_no, table.c.machine_model],
                index_where=table.c.plant.is_(None),
                set_=set_values,
            )
        else:
            stmt = stmt.on_conflict_do_update(
                constraint="uq_pcb_material_machine_plant",
                set_=set_values,
            )

        stmt = stmt.returning(table.c.id)
        record_id = (await self.session.execute(stmt)).scalar_one()
        await self.session.flush()
        entity = await self.session.get(PartCycleBaseline, int(record_id))
        assert entity is not None
        return entity

    def _apply_plant_lookup(self, stmt, plant: str | None):
        normalized_plant = self._normalize_plant(plant)
        if normalized_plant is None:
            return stmt.where(PartCycleBaseline.plant.is_(None))
        return stmt.where(
            or_(
                PartCycleBaseline.plant == normalized_plant,
                PartCycleBaseline.plant.is_(None),
            )
        )

    def _lookup_order_by(self, plant: str | None):
        normalized_plant = self._normalize_plant(plant)
        if normalized_plant is None:
            plant_priority = case((PartCycleBaseline.plant.is_(None), 0), else_=1)
        else:
            plant_priority = case((PartCycleBaseline.plant == normalized_plant, 0), else_=1)
        return (
            plant_priority,
            PartCycleBaseline.sample_count.desc(),
            PartCycleBaseline.updated_at.desc(),
            PartCycleBaseline.id.desc(),
        )

    def _scope_plant_predicate(self, plant: str | None):
        normalized_plant = self._normalize_plant(plant)
        if normalized_plant is None:
            return PartCycleBaseline.plant.is_(None)
        return PartCycleBaseline.plant == normalized_plant

    @staticmethod
    def _normalize_plant(plant: str | None) -> str | None:
        value = (plant or "").strip()
        return value or None

    @classmethod
    def _scope_key(cls, material_no: str, machine_model: str, plant: str | None) -> tuple[str, str, str | None]:
        return (material_no, machine_model, cls._normalize_plant(plant))

    @classmethod
    def _normalize_scope(cls, scope: tuple[str, str, str | None]) -> tuple[str, str, str | None]:
        material_no, machine_model, plant = scope
        return material_no, machine_model, cls._normalize_plant(plant)

    def _is_postgresql(self) -> bool:
        bind = self.session.bind
        return bool(bind is not None and bind.dialect.name == "postgresql")
