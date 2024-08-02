from rich import print

from prbot.core.sync.processor import SyncProcessor
from prbot.injection import inject_instance
from prbot.modules.database.repository import PullRequestDatabase

from .common import (
    PullRequestPathArg,
    RepositoryPathArg,
    async_command,
    build_typer,
    ensure_pull_request,
)

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


@async_command(app)
async def list(path: RepositoryPathArg) -> None:
    """List known pull requests for a specific repository."""
    pull_request_db = inject_instance(PullRequestDatabase)
    pull_requests = await pull_request_db.filter(owner=path.owner, name=path.name)
    if len(pull_requests) == 0:
        print("[yellow]No pull request found.[/yellow]")
        return

    for pull_request in pull_requests:
        print(pull_request)


@async_command(app)
async def show(path: PullRequestPathArg) -> None:
    """Show info about a specific pull request."""
    pull_request = await ensure_pull_request(path)
    print(pull_request)
