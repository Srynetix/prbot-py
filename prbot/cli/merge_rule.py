from rich import print

from prbot.cli.common import (
    RepositoryPathArg,
    RuleBranchArg,
    async_command,
    build_typer,
    ensure_repository,
)
from prbot.core.models import MergeRule, MergeStrategy, RuleBranchType
from prbot.injection import inject_instance
from prbot.modules.database.repository import MergeRuleDatabase, RepositoryDatabase

app = build_typer()


@async_command(app)
async def add(
    repository_path: RepositoryPathArg,
    base_branch: RuleBranchArg,
    head_branch: RuleBranchArg,
    strategy: MergeStrategy,
) -> None:
    """Add a new merge rule."""
    repository = await ensure_repository(repository_path)
    merge_rule_db = inject_instance(MergeRuleDatabase)

    # Check for the specific rule '*' -> '*'.
    if (
        base_branch.type == RuleBranchType.Wildcard
        and head_branch.type == RuleBranchType.Wildcard
    ):
        repository_db = inject_instance(RepositoryDatabase)
        await repository_db.set_default_strategy(
            owner=repository_path.owner, name=repository_path.name, strategy=strategy
        )

        print(
            f'[green]Default strategy set to "{strategy}" for repository "{repository_path}".[/green]'
        )
        return

    await merge_rule_db.create(
        MergeRule(
            repository_path=repository.path(),
            base_branch=base_branch,
            head_branch=head_branch,
            strategy=strategy,
        )
    )


@async_command(app)
async def remove(
    repository_path: RepositoryPathArg,
    base_branch: RuleBranchArg,
    head_branch: RuleBranchArg,
) -> None:
    """Remove a specific merge rule."""
    repository = await ensure_repository(repository_path)

    merge_rule_db = inject_instance(MergeRuleDatabase)
    found = await merge_rule_db.delete(
        owner=repository.owner,
        name=repository.name,
        base_branch=base_branch,
        head_branch=head_branch,
    )
    if found:
        print("[green]Merge rule deleted.[/green]")
    else:
        print("[yellow]Merge rule not found.[/yellow]")


@async_command(app)
async def list(repository_path: RepositoryPathArg) -> None:
    """List known merge rules."""
    repository = await ensure_repository(repository_path)

    # Show main rule
    print(
        f"- (Default) [blue]* (head)[/blue] -> [blue]* (base): [green]{repository.default_strategy}"
    )

    merge_rule_db = inject_instance(MergeRuleDatabase)
    rules = await merge_rule_db.filter(
        owner=repository_path.owner, name=repository_path.name
    )

    for rule in rules:
        print(
            f"- [blue]{rule.head_branch.get_name()} (head)[/blue] -> [blue]{rule.base_branch.get_name()} (base)[/blue]: [green]{rule.strategy}[/green]"
        )
