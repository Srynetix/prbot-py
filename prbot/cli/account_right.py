from rich import print

from prbot.cli.common import (
    RepositoryPathArg,
    async_command,
    build_typer,
    ensure_external_account,
    ensure_repository,
)
from prbot.core.models import ExternalAccountRight
from prbot.injection import inject_instance
from prbot.modules.database.repository import ExternalAccountRightDatabase

app = build_typer()


@async_command(app)
async def add(
    username: str,
    repository_path: RepositoryPathArg,
) -> None:
    """Add a new account right."""
    account = await ensure_external_account(username)
    await ensure_repository(repository_path)

    right_db = inject_instance(ExternalAccountRightDatabase)
    right = await right_db.create(
        ExternalAccountRight(repository_path=repository_path, username=account.username)
    )

    print(right)


@async_command(app)
async def remove(
    username: str,
    repository_path: RepositoryPathArg,
) -> None:
    """Remove a specific account right."""
    await ensure_external_account(username)
    await ensure_repository(repository_path)

    right_db = inject_instance(ExternalAccountRightDatabase)
    await right_db.delete(
        owner=repository_path.owner,
        name=repository_path.name,
        username=username,
    )

    print(
        f"[green]Account '{username}' right on repository '{repository_path}' deleted.[/green]"
    )


@async_command(app)
async def list(username: str) -> None:
    """List known account rights."""
    await ensure_external_account(username)

    right_db = inject_instance(ExternalAccountRightDatabase)
    rights = await right_db.filter(username=username)

    if len(rights) == 0:
        print("[yellow]No right found.[/yellow]")
        return

    for right in rights:
        print(f"- [green]{right.repository_path}[/green]")
