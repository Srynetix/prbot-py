import datetime

import httpx
import pytest

from prbot.injection import inject_instance
from prbot.modules.github.client import GitHubClient
from prbot.modules.github.core import AuthenticationTypeApp
from prbot.modules.github.models import GhLabelsResponse, GhRepository, GhUser
from tests.conftest import get_fake_github_http_client
from tests.utils.http import (
    HttpExpectation,
)

pytestmark = pytest.mark.anyio


def dummy_private_key() -> str:
    return (
        "-----BEGIN PRIVATE KEY-----\n"
        "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\n"
        "WfckA/vb0vOMDbaoHX7Ue/eOnDMydQ==\n"
        "-----END PRIVATE KEY-----"
    )


async def test_retry() -> None:
    fake_github = get_fake_github_http_client()
    client = inject_instance(GitHubClient)

    fake_github.expect(
        HttpExpectation()
        .with_times(2)
        .with_input(method="GET", url="/repos/foo/bar")
        .with_output_status(500)
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.repositories().get(owner="foo", name="bar")


async def test_pagniation() -> None:
    fake_github = get_fake_github_http_client()
    client = inject_instance(GitHubClient)

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/foo/bar/issues/1/labels")
        .with_input_params(per_page=100, page=1)
        .with_output_status(200)
        .with_output_models([GhLabelsResponse(name=f"LabelP1L{x}") for x in range(100)])
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/foo/bar/issues/1/labels")
        .with_input_params(per_page=100, page=2)
        .with_output_status(200)
        .with_output_models([GhLabelsResponse(name=f"LabelP2L{x}") for x in range(50)])
    )

    labels = await client.issues().labels(owner="foo", name="bar", number=1)
    assert len(labels) == 150


async def test_app_authentication() -> None:
    fake_github = get_fake_github_http_client()
    client = inject_instance(GitHubClient)
    client.core().set_app_authentication(
        client_id="foobar", private_key=dummy_private_key()
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/foo/bar/installation")
        .with_output_status(200)
        .with_output_json({"id": 123456})
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="POST", url="/app/installations/123456/access_tokens")
        .with_output_status(200)
        .with_output_json(
            {
                "token": "foobar",
                "expires_at": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(minutes=60)
                ).isoformat(),
            }
        )
    )

    await client.setup_client_for_repository(owner="foo", name="bar")

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/foo/bar")
        .with_output_status(200)
        .with_output_model(
            GhRepository(owner=GhUser(login="foo"), name="bar", full_name="foo/bar")
        )
    )

    # Make a simple call
    await client.repositories().get(owner="foo", name="bar")


async def test_app_authentication_expiration() -> None:
    fake_github = get_fake_github_http_client()
    client = inject_instance(GitHubClient)
    client.core().set_app_authentication(
        client_id="foobar", private_key=dummy_private_key()
    )

    # Force installation mode
    client.core().set_installation_authentication(
        app=AuthenticationTypeApp(client_id="foobar", private_key=dummy_private_key()),
        installation_id=123456,
        token="foobar",
        expiration=datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(minutes=60),
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="POST", url="/app/installations/123456/access_tokens")
        .with_output_status(200)
        .with_output_json(
            {
                "token": "foobar",
                "expires_at": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(minutes=60)
                ).isoformat(),
            }
        )
    )

    await client.setup_client_for_repository(owner="foo", name="bar")

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/foo/bar")
        .with_output_status(200)
        .with_output_model(
            GhRepository(owner=GhUser(login="foo"), name="bar", full_name="foo/bar")
        )
    )

    # Make a simple call
    await client.repositories().get(owner="foo", name="bar")
