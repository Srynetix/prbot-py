from rich import print

from prbot.core.models import (
    RepositoryRule,
    RuleActionFactory,
    RuleConditionFactory,
)
from prbot.injection import inject_instance
from prbot.modules.database.repository import (
    RepositoryRuleDatabase,
)

from .common import RepositoryPathArg, async_command, build_typer, ensure_repository

app = build_typer()


@async_command(app)
async def add(
    repository_path: RepositoryPathArg, rule_name: str, conditions: str, actions: str
) -> None:
    """Add a new repository rule."""
    repository = await ensure_repository(repository_path)
    rule_db = inject_instance(RepositoryRuleDatabase)
    await rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name=rule_name,
            conditions=RuleConditionFactory.from_str_many(conditions),
            actions=RuleActionFactory.from_str_many(actions),
        )
    )


@async_command(app)
async def delete(repository_path: RepositoryPathArg, rule_name: str) -> None:
    """Delete a specific repository rule."""
    repository = await ensure_repository(repository_path)

    rule_db = inject_instance(RepositoryRuleDatabase)
    await rule_db.delete(
        owner=repository.owner, name=repository.name, rule_name=rule_name
    )


@async_command(app)
async def list(repository_path: RepositoryPathArg) -> None:
    """List all known repositories."""
    await ensure_repository(repository_path)

    rule_db = inject_instance(RepositoryRuleDatabase)
    rules = await rule_db.list(owner=repository_path.owner, name=repository_path.name)
    if len(rules) == 0:
        print("[yellow]No rule found.[/yellow]")
        return

    for rule in rules:
        print(rule)
