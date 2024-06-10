from typing import Annotated

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from prbot.core.models import ExternalAccount
from prbot.injection import inject_instance
from prbot.modules.database.repository import ExternalAccountDatabase

logger = structlog.get_logger(__name__)


class TokenData(BaseModel):
    username: str


class TokenAuthentication:
    async def authenticate(
        self, credentials: HTTPAuthorizationCredentials
    ) -> ExternalAccount:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # First, extract the username from the JWT without checking its signature.
        # It will be checked after fetching the appropriate public key.
        try:
            unsafe_payload = jwt.decode(
                credentials.credentials, options={"verify_signature": False}
            )
        except jwt.InvalidTokenError:
            logger.error("Could not decode token", exc_info=True)
            raise credentials_exception

        username = unsafe_payload.get("iss")
        if username is None:
            logger.error("Missing 'iss' claim from token")
            raise credentials_exception

        # Validate username
        external_account_db = inject_instance(ExternalAccountDatabase)
        external_account = await external_account_db.get(username=username)
        if not external_account:
            logger.error("Unknown external account", username=username)
            raise credentials_exception

        public_key = external_account.public_key

        # Validate token
        try:
            jwt.decode(credentials.credentials, public_key, algorithms=["RS256"])
        except jwt.InvalidTokenError:
            logger.error("Invalid token", exc_info=True)
            raise credentials_exception

        token_data = TokenData(username=username)
        user = await get_user(token_data.username)
        if user is None:
            logger.error("Could not fetch known user from database.")
            raise credentials_exception

        return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
) -> ExternalAccount:
    return await TokenAuthentication().authenticate(credentials)


async def get_user(username: str) -> ExternalAccount | None:
    external_account_db = inject_instance(ExternalAccountDatabase)
    return await external_account_db.get(username=username)
