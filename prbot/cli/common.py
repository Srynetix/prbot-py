import asyncio
import functools
import re
from typing import Annotated, Any, Callable, Coroutine

import typer
from rich import print
from tortoise import Tortoise

from prbot.config.log import setup_logging
from prbot.config.sentry import setup_sentry
from prbot.core.models import (
    ExternalAccount,
    PullRequest,
    PullRequestPath,
    Repository,
    RepositoryPath,
    RuleBranch,
    RuleBranchFactory,
)
from prbot.injection import inject_instance, setup
from prbot.modules.database.repository import (
    ExternalAccountDatabase,
    PullRequestDatabase,
    RepositoryDatabase,
)
from prbot.modules.database.settings import get_orm_configuration
from prbot.modules.gif.client import GifClient
from prbot.modules.github.client import GitHubClient
from prbot.modules.lock import LockClient


def parse_regex(value: str) -> re.Pattern[str]:
    try:
        return re.compile(value)
    except Exception as err:
        raise ValueError(str(err)) from err


RepositoryPathArg = Annotated[
    RepositoryPath, typer.Argument(parser=RepositoryPath.from_str)
]
PullRequestPathArg = Annotated[
    PullRequestPath, typer.Argument(parser=PullRequestPath.from_str)
]
RuleBranchArg = Annotated[RuleBranch, typer.Argument(parser=RuleBranchFactory.from_str)]
RegexPattern = Annotated[re.Pattern[str], typer.Argument(parser=parse_regex)]


def build_typer() -> typer.Typer:
    return typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


def setup_runtime(coro: Coroutine[None, Any, Any]) -> None:
    async def wrapper() -> None:
        try:
            # Setup sentry integration
            setup_sentry()

            # Setup logging
            setup_logging()

            # Setup dependency injection container
            setup.setup_injections()

            # Setup database
            await Tortoise.init(get_orm_configuration())

            # Run original coroutine
            await coro

        finally:
            try:
                # Close database connections on exit/on error
                await Tortoise.close_connections()

                # Close GitHub client
                gh_client = inject_instance(GitHubClient)
                await gh_client.aclose()

                # Close Gif client
                gif_client = inject_instance(GifClient)
                await gif_client.aclose()

                # Close lock client
                lock_client = inject_instance(LockClient)
                await lock_client.aclose()

            except Exception as e:
                print(
                    f"[yellow]Warning: Something happened on cleanup: {e}. Ignoring...[/yellow]"
                )

    asyncio.run(wrapper())


def use_runtime(f: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        setup_runtime(f(*args, **kwargs))

    return wrapper


def async_command(app: typer.Typer) -> Callable[..., Any]:
    def inner(f: Callable[..., Any]) -> Callable[..., Any]:
        return app.command()(use_runtime(f))

    return inner


async def ensure_repository(path: RepositoryPath) -> Repository:
    repository_db = inject_instance(RepositoryDatabase)
    repository = await repository_db.get(owner=path.owner, name=path.name)
    if repository is None:
        print(f"[red]Unknown repository: {path}[/red]")
        raise typer.Exit(code=1)

    return repository


async def ensure_pull_request(path: PullRequestPath) -> PullRequest:
    pull_request_db = inject_instance(PullRequestDatabase)
    pull_request = await pull_request_db.get(
        owner=path.owner, name=path.name, number=path.number
    )
    if pull_request is None:
        print(f"[red]Unknown pull request: {path}[/red]")
        raise typer.Exit(code=1)

    return pull_request


async def ensure_external_account(username: str) -> ExternalAccount:
    external_account_db = inject_instance(ExternalAccountDatabase)
    account = await external_account_db.get(username=username)
    if account is None:
        print(f"[red]Unknown external account: {username}[/red]")
        raise typer.Exit(code=1)

    return account
