"""
보안 하드닝 단위 테스트 (DB 불필요).
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import (
    encrypt_api_key,
    decrypt_api_key,
    EncryptionNotConfiguredError,
)
from app.core import config as config_module
from app.services.migration import strip_secret_fields


def test_strip_secret_fields_removes_keys():
    payload = {
        "title": "t",
        "api_key_override": "secret",
        "plotter_api_key": "p",
        "writer_api_key": "w",
        "judge_api_key": "j",
        "editor_api_key": "e",
        "reviewer_api_key": "r",
        "llm_model": "m",
    }
    cleaned = strip_secret_fields(payload)
    assert cleaned["title"] == "t"
    assert cleaned["llm_model"] == "m"
    assert cleaned["api_key_override"] is None
    assert cleaned["writer_api_key"] is None


def test_encrypt_roundtrip_with_secret(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(config_module.settings, "API_KEY_ENCRYPTION_SECRET", key)
    monkeypatch.setattr(config_module.settings, "ENVIRONMENT", "development")

    plain = "nvapi-test-key"
    enc = encrypt_api_key(plain)
    assert enc != plain
    assert decrypt_api_key(enc) == plain


def test_encrypt_production_without_secret_raises(monkeypatch):
    monkeypatch.setattr(config_module.settings, "API_KEY_ENCRYPTION_SECRET", None)
    monkeypatch.setattr(config_module.settings, "ENVIRONMENT", "production")

    with pytest.raises(EncryptionNotConfiguredError):
        encrypt_api_key("some-user-key")


def test_encrypt_development_without_secret_plaintext_fallback(monkeypatch):
    monkeypatch.setattr(config_module.settings, "API_KEY_ENCRYPTION_SECRET", None)
    monkeypatch.setattr(config_module.settings, "ENVIRONMENT", "development")

    plain = "dev-only-key"
    assert encrypt_api_key(plain) == plain
