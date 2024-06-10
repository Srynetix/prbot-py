import time
from typing import Self

import jwt
from pydantic import BaseModel


class GitHubAppTokenData(BaseModel):
    iat: int
    exp: int
    iss: str

    @classmethod
    def from_client_id(cls, client_id: str) -> Self:
        return cls(
            # 60 seconds in the past to allow for clock drift
            iat=int(time.time()) - 60,
            # 10 minutes maximum
            exp=int(time.time()) + 600,
            # App client ID
            iss=client_id,
        )


def generate_github_app_jwt(*, private_key: str, client_id: str) -> str:
    payload = GitHubAppTokenData.from_client_id(client_id).model_dump()
    return jwt.encode(payload, key=private_key, algorithm="RS256")
