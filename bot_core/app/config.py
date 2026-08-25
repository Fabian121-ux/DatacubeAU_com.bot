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
    admin_username: str = Field(default="zina", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")
    admin_session_secret: str = Field(default="", alias="ADMIN_SESSION_SECRET")
    admin_session_ttl_seconds: int = Field(default=86400, alias="ADMIN_SESSION_TTL_SECONDS")
    admin_login_max_failures: int = Field(default=5, alias="ADMIN_LOGIN_MAX_FAILURES")
    admin_login_lockout_seconds: int = Field(default=900, alias="ADMIN_LOGIN_LOCKOUT_SECONDS")
    admin_cookie_secure: bool = Field(default=False, alias="ADMIN_COOKIE_SECURE")
    startup_validate_db: bool = Field(default=True, alias="STARTUP_VALIDATE_DB")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    waha_service_url: str = Field(default="http://localhost:3000", alias="WAHA_SERVICE_URL")
    waha_base_url: str = Field(default="", alias="WAHA_BASE_URL")
    waha_api_key: str = Field(default="", validation_alias=AliasChoices("WAHA_API_KEY", "WHATSAPP_API_KEY"))
    waha_session_name: str = Field(default="default", alias="WAHA_SESSION_NAME")
    waha_send_path: str = Field(default="/api/sendText", alias="WAHA_SEND_PATH")
    waha_send_image_path: str = Field(default="/api/sendImage", alias="WAHA_SEND_IMAGE_PATH")
    waha_session_status_path: str = Field(default="/api/sessions", alias="WAHA_SESSION_STATUS_PATH")
    waha_chats_path: str = Field(default="/api/{session}/chats", alias="WAHA_CHATS_PATH")
    waha_request_timeout_seconds: int = Field(default=15, alias="WAHA_REQUEST_TIMEOUT_SECONDS")
    waha_request_retry_count: int = Field(default=2, alias="WAHA_REQUEST_RETRY_COUNT")
    waha_request_retry_backoff_seconds: float = Field(default=1.0, alias="WAHA_REQUEST_RETRY_BACKOFF_SECONDS")

    bot_wa_number: str = Field(default="", alias="BOT_WA_NUMBER")
    owner_whatsapp_ids: str = Field(default="", alias="OWNER_WHATSAPP_IDS")
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
    openrouter_max_tokens: int = Field(default=600, alias="OPENROUTER_MAX_TOKENS")

    searxng_url: str = Field(default="http://localhost:8081", alias="SEARXNG_URL")
    brave_search_api_key: str = Field(default="", alias="BRAVE_SEARCH_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    exchangerate_api_key: str = Field(default="", alias="EXCHANGERATE_API_KEY")
    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")
    giphy_api_key: str = Field(default="", alias="GIPHY_API_KEY")
    internet_enabled: bool = Field(default=False, alias="INTERNET_ENABLED")
    web_search_enabled: bool = Field(default=False, alias="WEB_SEARCH_ENABLED")
    news_enabled: bool = Field(default=False, alias="NEWS_ENABLED")
    weather_enabled: bool = Field(default=False, alias="WEATHER_ENABLED")
    currency_enabled: bool = Field(default=False, alias="CURRENCY_ENABLED")
    youtube_enabled: bool = Field(default=False, alias="YOUTUBE_ENABLED")
    image_search_enabled: bool = Field(default=False, alias="IMAGE_SEARCH_ENABLED")
    sticker_search_enabled: bool = Field(default=False, alias="STICKER_SEARCH_ENABLED")
    internet_provider: str = Field(default="searxng", alias="INTERNET_PROVIDER")
    internet_daily_limit_per_user: int = Field(default=25, alias="INTERNET_DAILY_LIMIT_PER_USER")
    internet_cache_ttl_seconds: int = Field(default=900, alias="INTERNET_CACHE_TTL_SECONDS")
    internet_smart_detection_enabled: bool = Field(default=True, alias="INTERNET_SMART_DETECTION_ENABLED")

    typing_delay_enabled: bool = Field(default=True, alias="TYPING_DELAY_ENABLED")
    min_typing_delay_seconds: float = Field(default=1.0, alias="MIN_TYPING_DELAY_SECONDS")
    max_typing_delay_seconds: float = Field(default=6.0, alias="MAX_TYPING_DELAY_SECONDS")
    show_source_badges: bool = Field(default=False, alias="SHOW_SOURCE_BADGES")
    show_context_badges: bool = Field(default=True, alias="SHOW_CONTEXT_BADGES")
    enable_signature_style: bool = Field(default=True, alias="ENABLE_SIGNATURE_STYLE")
    whatsapp_message_format: str = Field(default="automatic", alias="WHATSAPP_MESSAGE_FORMAT")

    local_test_dm_whatsapp_id: str = Field(default="234000000000@c.us", alias="LOCAL_TEST_DM_WHATSAPP_ID")
    local_test_group_chat_id: str = Field(default="120363000000000000@g.us", alias="LOCAL_TEST_GROUP_CHAT_ID")

    def validate_runtime(self) -> None:
        errors: list[str] = []
        if not self.database_url:
            errors.append("DATABASE_URL is required.")
        if not self.waha_service_url:
            errors.append("WAHA_SERVICE_URL is required.")
        if not self.waha_session_name:
            errors.append("WAHA_SESSION_NAME is required.")
        if self.environment == "production" and not self.waha_api_key:
            errors.append("WAHA_API_KEY is required in production for authenticated webhook delivery.")
        if not self.admin_username:
            errors.append("ADMIN_USERNAME is required.")
        if not self.admin_password:
            errors.append("ADMIN_PASSWORD is required.")
        elif len(self.admin_password) < 12 or self.admin_password.startswith("replace-with-"):
            errors.append("ADMIN_PASSWORD must be at least 12 characters and must not be the example placeholder.")
        if self.admin_session_secret:
            if len(self.admin_session_secret) < 32 or self.admin_session_secret.startswith("replace-with-"):
                errors.append("ADMIN_SESSION_SECRET must be at least 32 characters and must not be the example placeholder.")
        elif self.environment == "production":
            errors.append("ADMIN_SESSION_SECRET is required in production.")
        if self.admin_session_ttl_seconds <= 0:
            errors.append("ADMIN_SESSION_TTL_SECONDS must be greater than 0.")
        if self.admin_login_max_failures <= 0:
            errors.append("ADMIN_LOGIN_MAX_FAILURES must be greater than 0.")
        if self.admin_login_lockout_seconds <= 0:
            errors.append("ADMIN_LOGIN_LOCKOUT_SECONDS must be greater than 0.")
        if self.waha_request_retry_count < 0:
            errors.append("WAHA_REQUEST_RETRY_COUNT must be 0 or greater.")
        if self.waha_request_retry_backoff_seconds < 0:
            errors.append("WAHA_REQUEST_RETRY_BACKOFF_SECONDS must be 0 or greater.")
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
            if self.openrouter_max_tokens <= 0:
                errors.append("OPENROUTER_MAX_TOKENS must be greater than 0 when AI_ENABLED=true.")
        if self.internet_provider not in {"searxng", "brave", "tavily"}:
            errors.append("INTERNET_PROVIDER must be 'searxng', 'brave', or 'tavily'.")
        if self.internet_daily_limit_per_user < 0:
            errors.append("INTERNET_DAILY_LIMIT_PER_USER must be 0 or greater.")
        if self.internet_cache_ttl_seconds < 0:
            errors.append("INTERNET_CACHE_TTL_SECONDS must be 0 or greater.")
        if self.min_typing_delay_seconds < 0:
            errors.append("MIN_TYPING_DELAY_SECONDS must be 0 or greater.")
        if self.max_typing_delay_seconds < 0:
            errors.append("MAX_TYPING_DELAY_SECONDS must be 0 or greater.")
        if self.max_typing_delay_seconds < self.min_typing_delay_seconds:
            errors.append("MAX_TYPING_DELAY_SECONDS must be greater than or equal to MIN_TYPING_DELAY_SECONDS.")
        if self.whatsapp_message_format.strip().lower() not in {"standard", "quote", "automatic"}:
            errors.append("WHATSAPP_MESSAGE_FORMAT must be 'standard', 'quote', or 'automatic'.")
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
            "waha_base_url": self.waha_base_url,
            "waha_session_name": self.waha_session_name,
            "waha_send_path": self.waha_send_path,
            "waha_send_image_path": self.waha_send_image_path,
            "waha_chats_path": self.waha_chats_path,
            "waha_request_retry_count": self.waha_request_retry_count,
            "waha_request_retry_backoff_seconds": self.waha_request_retry_backoff_seconds,
            "enable_auto_reply": self.enable_auto_reply,
            "owner_whatsapp_ids_configured": bool(self.owner_whatsapp_ids),
            "group_default_reply_mode": self.group_default_reply_mode,
            "group_default_cooldown_seconds": self.group_default_cooldown_seconds,
            "dm_default_cooldown_seconds": self.dm_default_cooldown_seconds,
            "kb_max_chunks": self.kb_max_chunks,
            "kb_min_score": self.kb_min_score,
            "ai_enabled": self.ai_enabled,
            "openrouter_base_url": self.openrouter_base_url if self.ai_enabled else "",
            "openrouter_model_light": self.openrouter_model_light if self.ai_enabled else "",
            "openrouter_model_deep": self.openrouter_model_deep if self.ai_enabled else "",
            "openrouter_max_tokens": self.openrouter_max_tokens if self.ai_enabled else 0,
            "internet_enabled": self.internet_enabled,
            "web_search_enabled": self.web_search_enabled,
            "news_enabled": self.news_enabled,
            "weather_enabled": self.weather_enabled,
            "currency_enabled": self.currency_enabled,
            "youtube_enabled": self.youtube_enabled,
            "image_search_enabled": self.image_search_enabled,
            "sticker_search_enabled": self.sticker_search_enabled,
            "internet_provider": self.internet_provider,
            "searxng_url": self.searxng_url,
            "internet_daily_limit_per_user": self.internet_daily_limit_per_user,
            "internet_cache_ttl_seconds": self.internet_cache_ttl_seconds,
            "internet_smart_detection_enabled": self.internet_smart_detection_enabled,
            "brave_search_api_key_configured": bool(self.brave_search_api_key),
            "tavily_api_key_configured": bool(self.tavily_api_key),
            "openweather_api_key_configured": bool(self.openweather_api_key),
            "exchangerate_api_key_configured": bool(self.exchangerate_api_key),
            "youtube_api_key_configured": bool(self.youtube_api_key),
            "giphy_api_key_configured": bool(self.giphy_api_key),
            "typing_delay_enabled": self.typing_delay_enabled,
            "min_typing_delay_seconds": self.min_typing_delay_seconds,
            "max_typing_delay_seconds": self.max_typing_delay_seconds,
            "show_source_badges": self.show_source_badges,
            "show_context_badges": self.show_context_badges,
            "enable_signature_style": self.enable_signature_style,
            "whatsapp_message_format": self.whatsapp_message_format,
            "admin_api_token_configured": bool(self.admin_api_token),
            "admin_username": self.admin_username,
            "admin_session_ttl_seconds": self.admin_session_ttl_seconds,
            "admin_login_max_failures": self.admin_login_max_failures,
            "admin_login_lockout_seconds": self.admin_login_lockout_seconds,
            "admin_cookie_secure": self.admin_cookie_secure,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
