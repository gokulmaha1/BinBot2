import base64
import os
from cryptography.fernet import Fernet
from app.core.config import get_settings

settings = get_settings()


def get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.encode()
    if len(key) < 32:
        key = key.ljust(32, b"0")[:32]
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_value(value: str) -> str:
    fernet = get_fernet()
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    fernet = get_fernet()
    return fernet.decrypt(encrypted_value.encode()).decode()
