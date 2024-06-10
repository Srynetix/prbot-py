import structlog

from prbot.config.settings import get_global_settings
from prbot.core.models import MergeStrategy, QaStatus
from prbot.modules.github.models import GhReactionType

from .commands import (
    AssignLabels,
    AssignReviewers,
    BaseCommand,
    CommandContext,
    CommandExecutionError,
    CommandOutput,
    Gif,
    Merge,
    Ping,
    SetAutomerge,
    SetChecksEnabled,
    SetLocked,
    SetQa,
    SetStrategy,
    Sync,
    UnassignLabels,
    UnassignReviewers,
)

logger = structlog.get_logger()


class CommandParseError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid command: {message}")


class CommandParser:
    def __init__(self) -> None: ...

    def parse(self, command: str) -> BaseCommand | None:
        try:
            bot_name, command_name, *args = command.split(" ")
        except ValueError:
            # Wrong format, ignore
            return None

        if bot_name != get_global_settings().bot_nickname:
            # Nope
            return None

        if command_name == "qa+":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetQa(QaStatus.Pass)

        elif command_name == "qa-":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetQa(QaStatus.Fail)

        elif command_name == "qa?":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetQa(QaStatus.Waiting)

        elif command_name == "noqa+":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetQa(QaStatus.Skipped)

        elif command_name == "nochecks-":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetChecksEnabled(True)

        elif command_name == "nochecks+":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetChecksEnabled(False)

        elif command_name == "automerge+":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetAutomerge(True)

        elif command_name == "automerge-":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetAutomerge(False)

        elif command_name == "lock+":
            if len(args) > 0:
                return SetLocked(True, comment=" ".join(args))
            else:
                return SetLocked(True, comment=None)

        elif command_name == "lock-":
            if len(args) > 0:
                return SetLocked(False, comment=" ".join(args))
            else:
                return SetLocked(False, comment=None)

        elif command_name == "r+":
            if len(args) == 0:
                raise CommandParseError("Missing reviewers to set")

            return AssignReviewers(args)

        elif command_name == "r-":
            if len(args) == 0:
                raise CommandParseError("Missing reviewers to unset")

            return UnassignReviewers(args)

        elif command_name == "strategy+":
            if len(args) > 1:
                raise CommandParseError("Unexpected arguments for command")

            try:
                strategy_arg = args[0]
                strategy = MergeStrategy(strategy_arg)
                return SetStrategy(strategy)
            except IndexError:
                raise CommandParseError("Missing strategy name")
            except ValueError:
                raise CommandParseError(f"Invalid merge strategy: {strategy_arg}")

        elif command_name == "strategy?":
            if len(args) != 0:
                raise CommandParseError("Unexpected arguments for command")

            return SetStrategy(None)

        elif command_name == "merge":
            if len(args) == 0:
                return Merge(None)

            if len(args) > 1:
                raise CommandParseError("Unexpected arguments for command")

            try:
                strategy = MergeStrategy(args[0])
                return Merge(strategy)
            except ValueError:
                raise CommandParseError(f"Invalid merge strategy: {args[0]}")

        elif command_name == "labels+":
            if len(args) == 0:
                raise CommandParseError("Missing labels to set")

            return AssignLabels(args)

        elif command_name == "labels-":
            if len(args) == 0:
                raise CommandParseError("Missing labels to unset")

            return UnassignLabels(args)

        elif command_name == "ping":
            if len(args) > 0:
                raise CommandParseError("Unexpected arguments for command")

            return Ping()

        elif command_name == "gif":
            if len(args) == 0:
                raise CommandParseError("Missing GIF query")

            return Gif(" ".join(args))

        elif command_name == "sync":
            if len(args) > 0:
                raise CommandParseError("Unexpected arguments for command")

            return Sync()

        else:
            raise CommandParseError(f'Unknown command "{command_name}"')


class CommandProcessor:
    async def process(
        self,
        *,
        owner: str,
        name: str,
        number: int,
        author: str,
        command: str,
        comment_id: int,
    ) -> CommandOutput:
        ctx = CommandContext(
            owner=owner,
            name=name,
            number=number,
            author=author,
            command=command,
            comment_id=comment_id,
        )

        try:
            parsed_command = CommandParser().parse(command)
            if parsed_command:
                logger.info("Command detected", command=parsed_command)
                return await parsed_command.process(ctx)
        except CommandParseError as err:
            await ctx.add_reaction(GhReactionType.Confused)
            await ctx.respond_to_author(str(err))
        except CommandExecutionError as err:
            await ctx.add_reaction(GhReactionType.Confused)
            await ctx.respond_to_author(str(err))

        return CommandOutput(needs_sync=False)
