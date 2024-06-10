import logging

import structlog

from prbot.config.settings import get_global_settings


def setup_logging() -> None:
    settings = get_global_settings()
    level = logging.getLevelName(settings.log_level)

    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level))
