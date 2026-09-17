import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def get_fernet() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(plain_text: str | None) -> str | None:
    if not plain_text:
        return None
    f = get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_value(cipher_text: str | None) -> str | None:
    if not cipher_text:
        return None
    try:
        f = get_fernet()
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return None
