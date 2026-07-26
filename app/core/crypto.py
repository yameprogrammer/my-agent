import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionNotConfiguredError(RuntimeError):
    """API 키 암호화 시크릿이 없어 평문 저장을 거부할 때 사용."""


def get_fernet() -> Optional[Fernet]:
    if not settings.API_KEY_ENCRYPTION_SECRET:
        return None
    try:
        # Secret should be a url-safe base64-encoded 32-byte key
        return Fernet(settings.API_KEY_ENCRYPTION_SECRET.encode("utf-8"))
    except Exception as e:
        logger.error("Failed to initialize Fernet with provided secret: %s", e)
        return None


def encrypt_api_key(api_key: Optional[str]) -> Optional[str]:
    """
    API 키를 Fernet 으로 암호화한다.

    - 시크릿이 없으면 development 에서만 평문 폴백(+경고).
    - production 에서는 시크릿 없이 키 저장을 거부한다.
    """
    if not api_key:
        return api_key
    f = get_fernet()
    if not f:
        if settings.ENVIRONMENT == "production":
            raise EncryptionNotConfiguredError(
                "API_KEY_ENCRYPTION_SECRET is required in production to store API keys. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        logger.warning(
            "API_KEY_ENCRYPTION_SECRET is not set; storing API key in plaintext (development only)."
        )
        return api_key
    try:
        return f.encrypt(api_key.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error("Failed to encrypt API key: %s", e)
        if settings.ENVIRONMENT == "production":
            raise EncryptionNotConfiguredError(f"Failed to encrypt API key: {e}") from e
        return api_key


def decrypt_api_key(encrypted_key: Optional[str]) -> Optional[str]:
    if not encrypted_key:
        return encrypted_key
    f = get_fernet()
    if not f:
        return encrypted_key

    try:
        return f.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Likely plaintext (legacy rows before encryption was enabled)
        return encrypted_key
    except Exception as e:
        logger.error("Failed to decrypt API key: %s", e)
        return encrypted_key
