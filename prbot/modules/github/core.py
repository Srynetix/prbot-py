import datetime
import enum
from typing import Any, Callable, Type, TypeVar

import structlog
from httpx import Response
from pydantic import BaseModel

from prbot.modules.github.crypto import generate_github_app_jwt
from prbot.modules.github.models import GhInstallationAccessTokenResponse
from prbot.modules.http.client import HttpClient

GetAllRootT = TypeVar("GetAllRootT", bound=BaseModel)
GetAllModelT = TypeVar("GetAllModelT", bound=BaseModel)

logger = structlog.get_logger()


class AuthenticationTypeEnum(enum.StrEnum):
    Anonymous = "anonymous"
    User = "user"
    App = "app"
    Installation = "installation"


class AuthenticationTypeAnonymous(BaseModel):
    type: AuthenticationTypeEnum = AuthenticationTypeEnum.Anonymous


class AuthenticationTypeApp(BaseModel):
    type: AuthenticationTypeEnum = AuthenticationTypeEnum.App
    client_id: str
    private_key: str


class AuthenticationTypeInstallation(BaseModel):
    type: AuthenticationTypeEnum = AuthenticationTypeEnum.Installation
    app: AuthenticationTypeApp
    installation_id: int
    token: str
    expiration: datetime.datetime


class AuthenticationTypeUser(BaseModel):
    type: AuthenticationTypeEnum = AuthenticationTypeEnum.User
    token: str


AuthenticationType = (
    AuthenticationTypeApp
    | AuthenticationTypeAnonymous
    | AuthenticationTypeUser
    | AuthenticationTypeInstallation
)


class GitHubClientError(Exception):
    pass


class GitHubClientNotAuthenticated(GitHubClientError):
    def __init__(self) -> None:
        super().__init__("Client is not authenticated")


class GitHubCore:
    MAX_BACKOFF_TRIES = 2
    MAX_PER_PAGE = 100

    client: HttpClient
    authentication_type: AuthenticationType

    def __init__(self, client: HttpClient) -> None:
        self.client = client
        self.authentication_type = AuthenticationTypeAnonymous()

    async def aclose(self) -> None:
        await self.client.aclose()

    def set_user_authentication(self, *, personal_token: str) -> None:
        logger.debug("Authentication set to user mode")
        self.authentication_type = AuthenticationTypeUser(token=personal_token)

    def set_app_authentication(self, *, client_id: str, private_key: str) -> None:
        logger.debug("Authentication set to app mode", client_id=client_id)
        self.authentication_type = AuthenticationTypeApp(
            client_id=client_id, private_key=private_key
        )

    def set_installation_authentication(
        self,
        *,
        app: AuthenticationTypeApp,
        installation_id: int,
        token: str,
        expiration: datetime.datetime,
    ) -> None:
        logger.debug(
            "Authentication set to installation mode",
            client_id=app.client_id,
            installation_id=installation_id,
            expiration=expiration,
        )
        self.authentication_type = AuthenticationTypeInstallation(
            app=app, installation_id=installation_id, token=token, expiration=expiration
        )

    def downgrade_installation_authentication(self) -> None:
        if isinstance(self.authentication_type, AuthenticationTypeInstallation):
            self.set_app_authentication(
                client_id=self.authentication_type.app.client_id,
                private_key=self.authentication_type.app.private_key,
            )
        else:
            logger.error("Could not downgrade installation authentication.")

    async def upgrade_app_authentication(self, *, installation_id: int) -> None:
        if isinstance(self.authentication_type, AuthenticationTypeApp):
            logger.debug(
                "Generating installation access token", installation_id=installation_id
            )
            response = await self.request(
                method="POST",
                path=f"/app/installations/{installation_id}/access_tokens",
            )
            data = GhInstallationAccessTokenResponse.model_validate(response.json())

            self.set_installation_authentication(
                app=self.authentication_type,
                installation_id=installation_id,
                token=data.token,
                expiration=data.expires_at,
            )

        else:
            logger.error("Could not upgrade app authentication.")

    async def request(self, *, method: str, path: str, **kwargs: Any) -> Response:
        if isinstance(self.authentication_type, AuthenticationTypeAnonymous):
            raise GitHubClientNotAuthenticated()
        elif isinstance(self.authentication_type, AuthenticationTypeApp):
            token = generate_github_app_jwt(
                private_key=self.authentication_type.private_key,
                client_id=self.authentication_type.client_id,
            )
            self.client.set_authentication_token(token)
        elif isinstance(self.authentication_type, AuthenticationTypeUser):
            self.client.set_authentication_token(self.authentication_type.token)
        elif isinstance(self.authentication_type, AuthenticationTypeInstallation):
            margin_seconds = 60
            now = datetime.datetime.now(datetime.timezone.utc)
            if self.authentication_type.expiration < now - datetime.timedelta(
                seconds=margin_seconds
            ):
                # Expired, time to regenerate another.
                logger.warn(
                    "Installation token expired",
                    installation_id=self.authentication_type.installation_id,
                    expiration=self.authentication_type.expiration,
                )
                installation_id = self.authentication_type.installation_id
                self.downgrade_installation_authentication()
                await self.upgrade_app_authentication(installation_id=installation_id)

            self.client.set_authentication_token(self.authentication_type.token)

        return await self.client._retry_request(method=method, path=path, **kwargs)

    async def get_all(
        self,
        *,
        model_type: Type[GetAllModelT],
        path: str,
        root_type: Type[GetAllRootT] | None = None,
        extract_fn: Callable[[GetAllRootT], list[GetAllModelT]] | None = None,
    ) -> list[GetAllModelT]:
        result = []
        current_page = 1

        while True:
            response = await self.request(
                method="GET",
                path=path,
                params={"per_page": self.MAX_PER_PAGE, "page": current_page},
            )

            if root_type and extract_fn:
                # Parse incoming data from root structure
                root_value = root_type.model_validate(response.json())
                data = extract_fn(root_value)

            elif model_type:
                # Parse incoming data
                data = [
                    model_type.model_validate(element) for element in response.json()
                ]

            if len(data) == 0:
                # We fetch everything.
                break

            elif len(data) == self.MAX_PER_PAGE:
                # It's possible we have more things to query.
                result.extend(data)
                current_page += 1

            else:
                # We have less than MAX_PER_PAGE items, so we should be good
                result.extend(data)
                break

        return result
