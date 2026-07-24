from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet():
    key = getattr(settings, "CONTENT_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "CONTENT_ENCRYPTION_KEY is required before content can be encrypted or read."
        )
    try:
        return Fernet(key.encode("ascii") if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "CONTENT_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def encrypt_text(plaintext):
    if not isinstance(plaintext, str):
        raise TypeError("Content must be text.")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_text(ciphertext):
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, AttributeError) as exc:
        raise ImproperlyConfigured(
            "Encrypted content cannot be decrypted with the configured key."
        ) from exc

