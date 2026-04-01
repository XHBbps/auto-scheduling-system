from __future__ import annotations

from app.config import settings


def normalize_plant(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or settings.default_plant
