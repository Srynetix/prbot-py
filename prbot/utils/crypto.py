from cryptography.hazmat.backends import default_backend as crypto_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import BaseModel


class KeyPair(BaseModel):
    private_key: str
    public_key: str


def generate_key_pair() -> KeyPair:
    rsa_key = rsa.generate_private_key(
        backend=crypto_backend(), public_exponent=65537, key_size=4096
    )

    private_key = rsa_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )

    public_key = rsa_key.public_key().public_bytes(
        encoding=Encoding.PEM, format=PublicFormat.PKCS1
    )

    return KeyPair(
        private_key=private_key.decode("utf-8"), public_key=public_key.decode("utf-8")
    )
