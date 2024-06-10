import datetime
import hashlib
import hmac

import jwt


def create_access_token(*, username: str, private_key: str) -> str:
    data_to_encode = {
        "iss": username,
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(data_to_encode, private_key, algorithm="RS256")


def compute_hash(key: str, message: bytes) -> str:
    hmac_value = hmac.new(
        key=key.encode("utf-8"), msg=message, digestmod=hashlib.sha256
    )
    return hmac_value.hexdigest()
