from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Datacube AU WhatsApp Bot", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8080, alias="API_PORT")
    admin_api_token: str = Field(default="", alias="ADMIN_API_TOKEN")
    startup_validate_db: bool = Field(default=True, alias="STARTUP_VALIDATE_DB")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    waha_service_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("WAHA_SERVICE_URL", "WAHA_BASE_URL"),
    )
    waha_api_key: str = Field(default="", validation_alias=AliasChoices("WAHA_API_KEY", "WHATSAPP_API_KEY"))
    waha_session_name: str = Field(default="default", alias="WAHA_SESSION_NAME")
    waha_send_path: str = Field(default="/api/sendText", alias="WAHA_SEND_PATH")
    waha_session_status_path: str = Field(default="/api/sessions", alias="WAHA_SESSION_STATUS_PATH")
    waha_request_timeout_seconds: int = Field(default=15, alias="WAHA_REQUEST_TIMEOUT_SECONDS")

    bot_wa_number: str = Field(default="", alias="BOT_WA_NUMBER")
    bot_mention_aliases: str = Field(default="datacube bot,datacubeau", alias="BOT_MENTION_ALIASES")
    enable_auto_reply: bool = Field(default=True, alias="ENABLE_AUTO_REPLY")
    group_default_reply_mode: str = Field(default="mention_only", alias="GROUP_DEFAULT_REPLY_MODE")
    group_default_cooldown_seconds: int = Field(default=45, alias="GROUP_DEFAULT_COOLDOWN_SECONDS")
    dm_default_cooldown_seconds: int = Field(default=6, alias="DM_DEFAULT_COOLDOWN_SECONDS")
    kb_max_chunks: int = Field(default=3, alias="KB_MAX_CHUNKS")
    kb_min_score: float = Field(default=0.34, alias="KB_MIN_SCORE")
    kb_reply_max_chars: int = Field(default=420, alias="KB_REPLY_MAX_CHARS")
    recent_items_limit: int = Field(default=50, alias="RECENT_ITEMS_LIMIT")

    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_model_light: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL_LIGHT")
    openrouter_model_deep: str = Field(default="openai/gpt-4o", alias="OPENROUTER_MODEL_DEEP")
    openrouter_timeout_seconds: int = Field(default=25, alias="OPENROUTER_TIMEOUT_SECONDS")
    openrouter_retry_count: int = Field(default=2, alias="OPENROUTER_RETRY_COUNT")

    local_test_dm_whatsapp_id: str = Field(default="234000000000@c.us", alias="LOCAL_TEST_DM_WHATSAPP_ID")
    local_test_group_chat_id: str = Field(default="120363000000000000@g.us", alias="LOCAL_TEST_GROUP_CHAT_ID")

    def validate_runtime(self) -> None:
        errors: list[str] = []
        if not self.database_url:
            errors.append("DATABASE_URL is required.")
        if not self.waha_service_url:
            errors.append("WAHA_SERVICE_URL or WAHA_BASE_URL is required.")
        if not self.waha_session_name:
            errors.append("WAHA_SESSION_NAME is required.")
        if self.group_default_reply_mode not in {"mention_only", "off"}:
            errors.append("GROUP_DEFAULT_REPLY_MODE must be 'mention_only' or 'off'.")
        if self.kb_min_score < 0 or self.kb_min_score > 1:
            errors.append("KB_MIN_SCORE must be between 0 and 1.")
        if self.ai_enabled:
            if not self.openrouter_api_key:
                errors.append("OPENROUTER_API_KEY is required when AI_ENABLED=true.")
            if not self.openrouter_model_light:
                errors.append("OPENROUTER_MODEL_LIGHT is required when AI_ENABLED=true.")
            if not self.openrouter_model_deep:
                errors.append("OPENROUTER_MODEL_DEEP is required when AI_ENABLED=true.")
        if errors:
            raise RuntimeError("Invalid runtime settings: " + " ".join(errors))

    def debug_view(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "database_url_configured": bool(self.database_url),
            "startup_validate_db": self.startup_validate_db,
            "waha_service_url": self.waha_service_url,
            "waha_session_name": self.waha_session_name,
            "waha_send_path": self.waha_send_path,
            "enable_auto_reply": self.enable_auto_reply,
            "group_default_reply_mode": self.group_default_reply_mode,
            "group_default_cooldown_seconds": self.group_default_cooldown_seconds,
            "dm_default_cooldown_seconds": self.dm_default_cooldown_seconds,
            "kb_max_chunks": self.kb_max_chunks,
            "kb_min_score": self.kb_min_score,
            "ai_enabled": self.ai_enabled,
            "openrouter_base_url": self.openrouter_base_url if self.ai_enabled else "",
            "openrouter_model_light": self.openrouter_model_light if self.ai_enabled else "",
            "openrouter_model_deep": self.openrouter_model_deep if self.ai_enabled else "",
            "admin_api_token_configured": bool(self.admin_api_token),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
