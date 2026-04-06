import json

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/auto_scheduling"
    database_auto_create_all: bool = False

    user_session_cookie_name: str = "user_session"
    user_session_ttl_minutes: int = 480
    user_session_cookie_secure: bool = True

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_display_name: str = "系统管理员"
    bootstrap_admin_password: str = ""

    wait_for_db_on_startup: bool = True
    wait_for_db_timeout_seconds: int = 120
    wait_for_db_poll_interval_seconds: float = 2.0
    snapshot_prewarm_on_startup: bool = False
    snapshot_refresh_batch_size: int = 500
    snapshot_observability_warn_refresh_age_minutes: int = 180
    external_http_timeout_seconds: float = 30.0
    external_http_max_retries: int = 2
    external_http_retry_backoff_seconds: float = 1.0
    auto_bom_backfill_batch_size: int = 5
    auto_bom_backfill_max_items_per_run: int = 20
    auto_bom_backfill_batch_pause_seconds: float = 1.0
    bom_backfill_queue_consume_enabled: bool = True
    bom_backfill_queue_consume_minutes: int = 10
    bom_backfill_max_fail_count: int = 5
    bom_backfill_retry_base_minutes: int = 10
    bom_backfill_empty_result_retry_minutes: int = 180
    sync_job_timeout_seconds: int = 7200
    sync_job_heartbeat_interval_seconds: int = 30
    sync_task_default_max_attempts: int = 3
    sync_task_retry_backoff_seconds: float = 10.0
    sync_task_worker_poll_interval_seconds: float = 2.0
    sync_task_worker_batch_size: int = 4
    sync_task_claim_timeout_seconds: int = 7200
    sync_scheduler_control_poll_seconds: float = 5.0
    sync_scheduler_stale_seconds: int = 30
    export_excel_max_rows: int = 5000
    export_batch_size: int = 1000
    export_spool_max_size_bytes: int = 5 * 1024 * 1024
    default_plant: str = "1000"

    guandata_base_url: str = ""
    guandata_domain: str = ""
    guandata_login_id: str = ""
    guandata_password: str = ""
    guandata_ds_id: str = ""

    sap_bom_base_url: str = ""

    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_production_app_token: str = ""
    feishu_production_table_id: str = ""
    feishu_research_app_token: str = ""
    feishu_research_table_id: str = ""

    schedule_trigger_advance_days: int = 28
    sync_window_days: int = 15
    snapshot_refresh_window_days: int = 365

    sync_scheduler_enabled: bool = False
    sync_scheduler_timezone: str = "Asia/Shanghai"
    sales_plan_sync_hour: int = 6
    sales_plan_sync_minute: int = 0
    bom_sync_hour: int = 6
    bom_sync_minute: int = 30
    production_order_sync_hour: int = 7
    production_order_sync_minute: int = 0
    research_sync_hour: int = 7
    research_sync_minute: int = 30
    schedule_snapshot_reconcile_hour: int = 8
    schedule_snapshot_reconcile_minute: int = 0

    trusted_proxy_cidrs: list[str] = [
        "127.0.0.1",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]

    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_allowed_origins(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _validate_user_session_cookie_security(self):
        if self.app_env.lower() in {"production", "prod"} and not self.user_session_cookie_secure:
            raise ValueError("USER_SESSION_COOKIE_SECURE must be true when APP_ENV is production.")
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
