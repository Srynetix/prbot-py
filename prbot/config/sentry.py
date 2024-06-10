import sentry_sdk

from prbot.version import __version__

from .settings import get_global_settings


def setup_sentry() -> None:
    settings = get_global_settings()

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        release=__version__,
        environment=settings.sentry_environment,
    )
