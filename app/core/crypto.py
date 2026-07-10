import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_fernet() -> Optional[Fernet]:
    if not settings.API_KEY_ENCRYPTION_SECRET:
        return None
    try:
        # Secret should be a url-safe base64-encoded 32-byte key
        return Fernet(settings.API_KEY_ENCRYPTION_SECRET.encode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to initialize Fernet with provided secret: {e}")
        return None

def encrypt_api_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return api_key
    f = get_fernet()
    if not f:
        return api_key  # Fallback to plaintext if secret is not configured
    try:
        return f.encrypt(api_key.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        return api_key

def decrypt_api_key(encrypted_key: Optional[str]) -> Optional[str]:
    if not encrypted_key:
        return encrypted_key
    f = get_fernet()
    if not f:
        return encrypted_key
    
    try:
        return f.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        # Likely plaintext
        return encrypted_key
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        return encrypted_key
