from enum import StrEnum


class ScheduleStatus(StrEnum):
    PENDING_DELIVERY = "pending_delivery"
    PENDING_DRAWING = "pending_drawing"
    MISSING_BOM = "missing_bom"
    PENDING_TRIGGER = "pending_trigger"
    SCHEDULABLE = "schedulable"
    SCHEDULED = "scheduled"
    SCHEDULED_STALE = "scheduled_stale"


class WarningLevel(StrEnum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"


class OrderType(StrEnum):
    REGULAR = "1"
    OPTIONAL = "2"
    CUSTOM = "3"


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class BomBackfillQueueStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRY_WAIT = "retry_wait"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


class BomBackfillFailureKind(StrEnum):
    TRANSIENT_ERROR = "transient_error"
    EMPTY_RESULT = "empty_result"
    PERMANENT_ERROR = "permanent_error"


class BackgroundTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SchedulerRuntimeState(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
