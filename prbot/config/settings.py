from contextvars import ContextVar
from typing import Annotated, cast

from pydantic import AfterValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

PrivateKeyField = Annotated[str, AfterValidator(lambda x: x.replace("\\n", "\n"))]


class Settings(BaseSettings):
    bot_nickname: str = "bot"

    database_url: str
    lock_url: str
    tenor_key: str

    # Logging
    log_level: str = "INFO"

    # GitHub
    github_webhook_secret: str
    github_personal_token: str = ""
    github_app_client_id: str = ""
    github_app_private_key: PrivateKeyField = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0
    sentry_profiles_sample_rate: float = 0.0
    sentry_environment: str = "production"

    # Server
    server_port: int = 8000
    server_ip: str = "0.0.0.0"

    model_config = SettingsConfigDict(env_prefix="prbot_")


_SETTINGS: ContextVar[Settings | None] = ContextVar("_SETTINGS", default=None)


def set_global_settings(settings: Settings) -> None:
    _SETTINGS.set(settings)


def get_global_settings() -> Settings:
    if _SETTINGS.get() is None:
        instance = Settings()  # type: ignore
        _SETTINGS.set(instance)
    return cast(Settings, _SETTINGS.get())
