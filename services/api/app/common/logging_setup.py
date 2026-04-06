"""Centralized logging configuration.

Call ``configure_logging()`` once at process startup (worker, scheduler,
or the ASGI entry-point) to switch every logger to structured JSON output
with an optional *request_id* field.
"""

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _AppJsonFormatter(JsonFormatter):
    """JSON formatter that injects *request_id* from the current context."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["request_id"] = request_id_var.get("-")
        log_record["level"] = record.levelname
        log_record["logger"] = record.name


def configure_logging(*, level: int = logging.INFO) -> None:
    """Replace the root logger's handlers with a single JSON handler."""
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicate output.
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _AppJsonFormatter(
            fmt="%(asctime)s %(level)s %(logger)s %(message)s",
            rename_fields={"asctime": "timestamp"},
        )
    )
    root.addHandler(handler)
