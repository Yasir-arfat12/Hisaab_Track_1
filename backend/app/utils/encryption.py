import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _derive_fernet_key(secret: str | None = None) -> bytes:
    raw_secret = secret if secret is not None else settings.SECRET_KEY.get_secret_value()
    digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plaintext: str, secret: str | None = None) -> str:
    """Encrypt an OAuth token at rest using Fernet."""
    fernet = Fernet(_derive_fernet_key(secret))
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str, secret: str | None = None) -> str:
    """Decrypt a stored Fernet-encrypted OAuth token."""
    fernet = Fernet(_derive_fernet_key(secret))
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
