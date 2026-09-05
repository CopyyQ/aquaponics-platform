import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
fernet = Fernet(settings.fernet_key.encode())


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token không hợp lệ hoặc đã hết hạn") from exc


def generate_device_secret() -> str:
    return secrets.token_urlsafe(48)


def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()


def decrypt_secret(secret_encrypted: str) -> str:
    return fernet.decrypt(secret_encrypted.encode()).decode()


def build_hmac_signature(secret: str, timestamp: str, raw_body: bytes) -> str:
    signed_data = timestamp.encode() + b"." + raw_body
    digest = hmac.new(secret.encode(), signed_data, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def verify_hmac_signature(secret: str, timestamp: str, raw_body: bytes, signature: str) -> bool:
    expected = build_hmac_signature(secret, timestamp, raw_body)
    return hmac.compare_digest(expected, signature)
