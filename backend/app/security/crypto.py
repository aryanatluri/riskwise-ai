"""Encryption at rest for client secrets (BYOK LLM keys, Jira tokens, Slack webhooks)."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class SecretsNotConfigured(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        raise SecretsNotConfigured("ENCRYPTION_KEY is not set; cannot store client secrets.")
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # wrong key or tampered value
        raise SecretsNotConfigured("Stored secret cannot be decrypted with ENCRYPTION_KEY.") from exc


def last4(value: str) -> str:
    return value[-4:] if len(value) >= 4 else "****"
