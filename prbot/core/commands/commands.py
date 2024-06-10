from abc import ABC, abstractmethod

import structlog

from prbot.core.message import generate_message_footer
from prbot.core.models import MergeStrategy, QaStatus
from prbot.core.sync.processor import SyncProcessor
from prbot.core.sync.sync_state import PullRequestSyncStateBuilder
from prbot.injection import (
    inject_instance,
)
from prbot.modules.database.repository import PullRequestDatabase, UnknownPullRequest
from prbot.modules.gif.client import GifClient
from prbot.modules.github.client import GitHubClient
from prbot.modules.github.models import GhReactionType

logger = structlog.get_logger()


class CommandExecutionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Command execution error: {message}")


class CommandOutput:
    needs_sync: bool

    def __init__(self, *, needs_sync: bool) -> None:
        self.needs_sync = needs_sync


class CommandContext:
    api: GitHubClient
    pull_request_db: PullRequestDatabase
    sync_state_builder: PullRequestSyncStateBuilder
    gif: GifClient

    owner: str
    name: str
    number: int
    author: str

    # Command and comment ID can be optional, if this is an external reaction
    command: str | None
    comment_id: int | None

    def __init__(
        self,
        *,
        owner: str,
        name: str,
        number: int,
        author: str,
        comment_id: int | None,
        command: str | None,
    ) -> None:
        self.api = inject_instance(GitHubClient)
        self.gif = inject_instance(GifClient)
        self.pull_request_db = inject_instance(PullRequestDatabase)
        self.sync_state_builder = inject_instance(PullRequestSyncStateBuilder)
        self.owner = owner
        self.name = name
        self.number = number
        self.author = author
        self.comment_id = comment_id
        self.command = command

    async def add_reaction(self, reaction: GhReactionType) -> None:
        if self.comment_id is not None:
            await self.api.reactions().add(
                owner=self.owner,
                name=self.name,
                comment_id=self.comment_id,
                reaction=reaction,
            )

    async def respond_to_author(self, comment: str) -> None:
        final_comment = f"{comment}\n{generate_message_footer()}"
        if self.command is not None:
            final_comment = f"> {self.command}\n\n{final_comment}"

        await self.api.issues().create_comment(
            owner=self.owner, name=self.name, number=self.number, message=final_comment
        )


class BaseCommand(ABC):
    @abstractmethod
    async def process(self, ctx: CommandContext) -> CommandOutput: ...


class SetQa(BaseCommand):
    status: QaStatus

    def __init__(self, status: QaStatus) -> None:
        self.status = status

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.status == command.status

    async def process(self, ctx: CommandContext) -> CommandOutput:
        logger.info("Running SetQa command", status=self.status, author=ctx.author)

        try:
            await ctx.pull_request_db.set_qa_status(
                owner=ctx.owner, name=ctx.name, number=ctx.number, qa_status=self.status
            )
        except UnknownPullRequest as err:
            raise CommandExecutionError(str(err))

        await ctx.add_reaction(GhReactionType.Eyes)
        await ctx.respond_to_author(
            "QA status is marked as **{status}** by **{author}**.".format(
                status=self.status.value, author=ctx.author
            ),
        )
        return CommandOutput(needs_sync=True)


class SetChecksEnabled(BaseCommand):
    status: bool

    def __init__(self, status: bool) -> None:
        self.status = status

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.status == command.status

    async def process(self, ctx: CommandContext) -> CommandOutput:
        try:
            await ctx.pull_request_db.set_checks_enabled(
                owner=ctx.owner, name=ctx.name, number=ctx.number, value=self.status
            )
        except UnknownPullRequest as err:
            raise CommandExecutionError(str(err))

        await ctx.add_reaction(GhReactionType.Eyes)

        if self.status:
            await ctx.respond_to_author(f"Checks were enabled by **{ctx.author}**.")
        else:
            await ctx.respond_to_author(f"Checks were disabled by **{ctx.author}**.")
        return CommandOutput(needs_sync=True)


class SetAutomerge(BaseCommand):
    value: bool

    def __init__(self, value: bool) -> None:
        self.value = value

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.value == command.value

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.pull_request_db.set_automerge(
            owner=ctx.owner, name=ctx.name, number=ctx.number, automerge=self.value
        )

        await ctx.add_reaction(GhReactionType.Eyes)

        if self.value:
            await ctx.respond_to_author(
                "Pull request automerge is enabled.",
            )
        else:
            await ctx.respond_to_author(
                "Pull request automerge is disabled.",
            )

        return CommandOutput(needs_sync=True)


class SetLocked(BaseCommand):
    value: bool
    comment: str | None

    def __init__(self, value: bool, *, comment: str | None) -> None:
        self.value = value
        self.comment = comment

    def __eq__(self, command: object) -> bool:
        return (
            isinstance(command, type(self))
            and self.value == command.value
            and self.comment == command.comment
        )

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.pull_request_db.set_locked(
            owner=ctx.owner, name=ctx.name, number=ctx.number, locked=self.value
        )

        await ctx.add_reaction(GhReactionType.Eyes)

        if self.value:
            if self.comment:
                await ctx.respond_to_author(
                    f"Pull request is now locked: {self.comment}.",
                )
            else:
                await ctx.respond_to_author("Pull request is now locked.")
        else:
            await ctx.respond_to_author("Pull request is now unlocked.")

        return CommandOutput(needs_sync=True)


class AssignReviewers(BaseCommand):
    reviewers: list[str]

    def __init__(self, reviewers: list[str]) -> None:
        self.reviewers = reviewers

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.reviewers == command.reviewers

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.add_reaction(GhReactionType.Eyes)
        await ctx.api.pull_requests().add_reviewers(
            owner=ctx.owner, name=ctx.name, number=ctx.number, reviewers=self.reviewers
        )

        return CommandOutput(needs_sync=True)


class UnassignReviewers(BaseCommand):
    reviewers: list[str]

    def __init__(self, reviewers: list[str]) -> None:
        self.reviewers = reviewers

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.reviewers == command.reviewers

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.add_reaction(GhReactionType.Eyes)
        await ctx.api.pull_requests().remove_reviewers(
            owner=ctx.owner, name=ctx.name, number=ctx.number, reviewers=self.reviewers
        )

        return CommandOutput(needs_sync=True)


class SetStrategy(BaseCommand):
    strategy: MergeStrategy | None

    def __init__(self, strategy: MergeStrategy | None) -> None:
        self.strategy = strategy

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.strategy == command.strategy

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.add_reaction(GhReactionType.Eyes)
        await ctx.pull_request_db.set_merge_strategy(
            owner=ctx.owner, name=ctx.name, number=ctx.number, strategy=self.strategy
        )

        return CommandOutput(needs_sync=True)


class Merge(BaseCommand):
    strategy: MergeStrategy | None

    def __init__(self, strategy: MergeStrategy | None) -> None:
        self.strategy = strategy

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.strategy == command.strategy

    async def process(self, ctx: CommandContext) -> CommandOutput:
        state = await ctx.sync_state_builder.build(
            owner=ctx.owner, name=ctx.name, number=ctx.number
        )

        try:
            await ctx.api.pull_requests().merge(
                owner=ctx.owner,
                name=ctx.name,
                number=ctx.number,
                strategy=state.merge_strategy,
                commit_title=f"{state.title} (#{state.number})",
                commit_message="",
            )
            await ctx.add_reaction(GhReactionType.PlusOne)
        except Exception as err:
            await ctx.add_reaction(GhReactionType.Confused)
            await ctx.respond_to_author(
                f"Error: Could not merge pull request.\n\n{str(err)}"
            )

        return CommandOutput(needs_sync=True)


class AssignLabels(BaseCommand):
    labels: list[str]

    def __init__(self, labels: list[str]) -> None:
        self.labels = labels

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.labels == command.labels

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.add_reaction(GhReactionType.Eyes)
        await ctx.api.issues().add_labels(
            owner=ctx.owner, name=ctx.name, number=ctx.number, labels=self.labels
        )
        return CommandOutput(needs_sync=False)


class UnassignLabels(BaseCommand):
    labels: list[str]

    def __init__(self, labels: list[str]) -> None:
        self.labels = labels

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.labels == command.labels

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.add_reaction(GhReactionType.Eyes)
        existing_labels = await ctx.api.issues().labels(
            owner=ctx.owner,
            name=ctx.name,
            number=ctx.number,
        )

        new_labels = [label for label in existing_labels if label not in self.labels]
        await ctx.api.issues().replace_labels(
            owner=ctx.owner, name=ctx.name, number=ctx.number, labels=new_labels
        )
        return CommandOutput(needs_sync=False)


class Ping(BaseCommand):
    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self))

    async def process(self, ctx: CommandContext) -> CommandOutput:
        await ctx.add_reaction(GhReactionType.Eyes)
        await ctx.respond_to_author("Pong!")
        return CommandOutput(needs_sync=False)


class Gif(BaseCommand):
    search: str

    def __init__(self, search: str) -> None:
        self.search = search

    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self)) and self.search == command.search

    async def process(self, ctx: CommandContext) -> CommandOutput:
        gif = await ctx.gif.query_first_match(self.search)
        await ctx.add_reaction(GhReactionType.Eyes)

        if gif is None:
            await ctx.respond_to_author(
                "No GIF found for your query... :cry:",
            )
        else:
            await ctx.respond_to_author(f"![gif]({gif})")
        return CommandOutput(needs_sync=False)


class Sync(BaseCommand):
    def __eq__(self, command: object) -> bool:
        return isinstance(command, type(self))

    async def process(self, ctx: CommandContext) -> CommandOutput:
        logger.info("Running Sync command", author=ctx.author)

        # Manual sync
        sync_processor = inject_instance(SyncProcessor)
        await sync_processor.process(
            owner=ctx.owner, name=ctx.name, number=ctx.number, force_creation=True
        )

        await ctx.add_reaction(GhReactionType.Eyes)
        return CommandOutput(needs_sync=False)
