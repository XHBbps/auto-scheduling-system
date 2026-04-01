from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

_CYCLE_DAYS_QUANT = Decimal('1')
_UNIT_CYCLE_DAYS_QUANT = Decimal('0.1')


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def normalize_part_cycle_days(value: Decimal | int | float | str) -> Decimal:
    return _to_decimal(value).quantize(_CYCLE_DAYS_QUANT, rounding=ROUND_HALF_UP)


def normalize_part_unit_cycle_days(value: Decimal | int | float | str) -> Decimal:
    return _to_decimal(value).quantize(_UNIT_CYCLE_DAYS_QUANT, rounding=ROUND_HALF_UP)


def normalize_part_cycle_payload(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if normalized.get('cycle_days') is not None:
        normalized['cycle_days'] = normalize_part_cycle_days(normalized['cycle_days'])
    if normalized.get('unit_cycle_days') is not None:
        normalized['unit_cycle_days'] = normalize_part_unit_cycle_days(normalized['unit_cycle_days'])
    return normalized
