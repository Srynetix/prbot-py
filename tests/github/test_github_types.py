import json
from pathlib import Path
from typing import Any, Type, cast

import pytest
from pydantic import BaseModel

from prbot.modules.github.webhooks.models import (
    GhCheckSuiteEvent,
    GhIssueCommentEvent,
    GhPingEvent,
    GhPullRequestEvent,
    GhReviewEvent,
)

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "webhooks"


class WebhookPathFactory:
    def fetch(self, name: str) -> dict[str, Any]:
        with open(FIXTURES_PATH / name, mode="r") as fd:
            return cast(dict[str, Any], json.load(fd))


@pytest.fixture
def webhook_factory() -> WebhookPathFactory:
    return WebhookPathFactory()


@pytest.mark.parametrize(
    "model_class,filename",
    [
        (GhPingEvent, "ping_event.json"),
        (GhCheckSuiteEvent, "check_suite_completed.json"),
        (GhIssueCommentEvent, "issue_comment_created.json"),
        (GhPullRequestEvent, "pull_request_labeled.json"),
        (GhPullRequestEvent, "pull_request_opened.json"),
        (GhReviewEvent, "pull_request_review_submitted.json"),
    ],
)
def test_parse(
    model_class: Type[BaseModel], filename: str, webhook_factory: WebhookPathFactory
) -> None:
    model_class.model_validate(webhook_factory.fetch(filename))
