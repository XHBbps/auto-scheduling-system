from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def normalize_sort_order(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.lower()
    if normalized in {"asc", "ascending"}:
        return "asc"
    if normalized in {"desc", "descending"}:
        return "desc"
    return None


def build_sort_expression(
    *,
    sort_field: str | None,
    sort_order: str | None,
    allowed_fields: Mapping[str, Any],
):
    normalized_order = normalize_sort_order(sort_order)
    if not sort_field or not normalized_order:
        return None

    column = allowed_fields.get(sort_field)
    if column is None:
        return None

    if normalized_order == "desc":
        return column.desc().nullslast()
    return column.asc().nullslast()


def resolve_order_by(
    *,
    sort_expression: Any,
    default_order_by: Iterable[Any],
) -> list[Any]:
    default_items = list(default_order_by)
    if sort_expression is None:
        return default_items
    return [sort_expression, *default_items]
