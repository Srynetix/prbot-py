from prbot.core.sync.processor import SyncProcessor
from prbot.injection import inject_instance

from .common import PullRequestPathArg, async_command, build_typer

app = build_typer()


@async_command(app)
async def sync(path: PullRequestPathArg) -> None:
    """
    Synchronize a specific pull request.
    Will synchronize even if the pull request is not yet present in the database.
    """
    sync = inject_instance(SyncProcessor)
    await sync.process(
        owner=path.owner, name=path.name, number=path.number, force_creation=True
    )
