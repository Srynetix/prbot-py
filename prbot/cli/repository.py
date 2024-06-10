from rich import print

from prbot.core.models import (
    MergeStrategy,
    Repository,
)
from prbot.injection import inject_instance
from prbot.modules.database.repository import (
    RepositoryDatabase,
)

from .common import (
    RegexPattern,
    RepositoryPathArg,
    async_command,
    build_typer,
    ensure_repository,
)
from .repository_rules import app as rules_app

app = build_typer()
app.add_typer(rules_app, name="rule", help="Manage repository rules.")


@async_command(app)
async def sync(repository_path: RepositoryPathArg) -> None:
    """Synchonize a specific repository."""
    repository_db = inject_instance(RepositoryDatabase)
    repository = await repository_db.get(
        owner=repository_path.owner, name=repository_path.name
    )
    if repository is None:
        repository = await repository_db.create(
            Repository(owner=repository_path.owner, name=repository_path.name)
        )

    print(repository)


@async_command(app)
async def list() -> None:
    """List all known repositories."""
    repository_db = inject_instance(RepositoryDatabase)
    repositories = await repository_db.all()
    if len(repositories) == 0:
        print("[yellow]No repository found.[/yellow]")
        return

    for repository in repositories:
        print(repository)


@async_command(app)
async def show(repository_path: RepositoryPathArg) -> None:
    """Show info about a specific repository."""
    repository = await ensure_repository(repository_path)
    print(repository)


@async_command(app)
async def set_manual_interaction(
    repository_path: RepositoryPathArg, value: bool
) -> None:
    """Enable/Disable the manual interaction mode for a specific repository."""
    await ensure_repository(repository_path)

    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.set_manual_interaction(
        owner=repository_path.owner, name=repository_path.name, value=value
    )

    print(
        f'[green]Manual interaction set to "{value}" for repository "{repository_path}".[/green]'
    )


@async_command(app)
async def set_title_validation_regex(
    repository_path: RepositoryPathArg, regex: RegexPattern
) -> None:
    """Set the title validation regex for a specific repository."""
    await ensure_repository(repository_path)

    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.set_pr_title_validation_regex(
        owner=repository_path.owner, name=repository_path.name, value=regex
    )

    print(
        f'[green]Title validation regex set to "{regex.pattern}" for repository "{repository_path}".[/green]'
    )


@async_command(app)
async def set_default_strategy(
    repository_path: RepositoryPathArg, strategy: MergeStrategy
) -> None:
    """Set the default merge strategy for a specific repository."""
    await ensure_repository(repository_path)

    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.set_default_strategy(
        owner=repository_path.owner, name=repository_path.name, strategy=strategy
    )

    print(
        f'[green]Default strategy set to "{strategy}" for repository "{repository_path}".[/green]'
    )


@async_command(app)
async def set_default_automerge(
    repository_path: RepositoryPathArg, value: bool
) -> None:
    """Set the default automerge value for a specific repository."""
    await ensure_repository(repository_path)

    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.set_default_automerge(
        owner=repository_path.owner, name=repository_path.name, value=value
    )

    print(
        f'[green]Default automerge value set to "{value}" for repository "{repository_path}".[/green]'
    )


@async_command(app)
async def set_default_qa(repository_path: RepositoryPathArg, value: bool) -> None:
    """Set if the QA status is enabled/skipped for a specific repository."""
    await ensure_repository(repository_path)

    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.set_default_enable_qa(
        owner=repository_path.owner, name=repository_path.name, value=value
    )

    print(
        f'[green]Default QA status value set to "{value}" for repository "{repository_path}".[/green]'
    )


@async_command(app)
async def set_default_checks(repository_path: RepositoryPathArg, value: bool) -> None:
    """Set if the checks status is enabled/skipped for a specific repository."""
    await ensure_repository(repository_path)

    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.set_default_enable_checks(
        owner=repository_path.owner, name=repository_path.name, value=value
    )

    print(
        f'[green]Default checks status value set to "{value}" for repository "{repository_path}".[/green]'
    )
