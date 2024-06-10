from typing import Any

from prbot.config.settings import get_global_settings


def get_orm_configuration() -> dict[str, Any]:
    settings = get_global_settings()

    return {
        "connections": {
            "default": settings.database_url,
        },
        "apps": {
            "prbot": {
                "models": ["prbot.modules.database.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }


TORTOISE_ORM = get_orm_configuration()
