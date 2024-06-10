import pytest

from prbot.core.commands.commands import (
    AssignLabels,
    AssignReviewers,
    BaseCommand,
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
from prbot.core.commands.processor import (
    CommandParseError,
    CommandParser,
)
from prbot.core.models import MergeStrategy, QaStatus

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "text,cmd",
    [
        ("", None),
        ("bot", None),
        ("foo qa+", None),
        ("bot qa+", SetQa(QaStatus.Pass)),
        ("bot qa-", SetQa(QaStatus.Fail)),
        ("bot qa?", SetQa(QaStatus.Waiting)),
        ("bot noqa+", SetQa(QaStatus.Skipped)),
        ("bot nochecks-", SetChecksEnabled(True)),
        ("bot nochecks+", SetChecksEnabled(False)),
        ("bot automerge+", SetAutomerge(True)),
        ("bot automerge-", SetAutomerge(False)),
        ("bot lock+", SetLocked(True, comment=None)),
        ("bot lock+ foo bar", SetLocked(True, comment="foo bar")),
        ("bot lock-", SetLocked(False, comment=None)),
        ("bot lock- foo bar", SetLocked(False, comment="foo bar")),
        ("bot r+ foo bar", AssignReviewers(["foo", "bar"])),
        ("bot r- foo bar", UnassignReviewers(["foo", "bar"])),
        ("bot strategy+ merge", SetStrategy(MergeStrategy.Merge)),
        ("bot strategy?", SetStrategy(None)),
        ("bot merge", Merge(None)),
        ("bot merge squash", Merge(MergeStrategy.Squash)),
        ("bot labels+ foo bar", AssignLabels(["foo", "bar"])),
        ("bot labels- foo bar", UnassignLabels(["foo", "bar"])),
        ("bot gif foo bar", Gif("foo bar")),
        ("bot ping", Ping()),
        ("bot sync", Sync()),
    ],
)
async def test_parse(text: str, cmd: BaseCommand | None) -> None:
    parser = CommandParser()
    assert parser.parse(text) == cmd


@pytest.mark.parametrize(
    "text",
    [
        "bot qa",
        "bot qa? foo",
        "bot qa- foo",
        "bot qa+ foo",
        "bot noqa+ foo",
        "bot noqa",
        "bot gif",
        "bot nochecks+ foo",
        "bot nochecks- foo",
        "bot nochecks",
        "bot automerge+ foo",
        "bot automerge- foo",
        "bot strategy+",
        "bot strategy+ foo",
        "bot strategy+ foo bar",
        "bot strategy? foo",
        "bot r+",
        "bot r-",
        "bot labels+",
        "bot labels-",
        "bot merge foo",
        "bot merge foo bar",
        "bot ping foo",
        "bot sync foo",
    ],
)
async def test_parse_error(text: str) -> None:
    parser = CommandParser()
    with pytest.raises(CommandParseError):
        parser.parse(text)
