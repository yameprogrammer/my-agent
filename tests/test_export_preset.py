from app.services.compiler import apply_export_preset
from app.services.usage_log import estimate_tokens, prompt_hash


def test_kakao_preset_collapses_blank_lines():
    raw = "첫 줄\n\n\n\n둘째 줄  \n"
    out = apply_export_preset(raw, "kakao")
    assert "\n\n\n" not in out
    assert "첫 줄" in out and "둘째 줄" in out


def test_estimate_tokens_and_hash():
    assert estimate_tokens("") == 0
    assert estimate_tokens("가나다라") >= 1
    h = prompt_hash("secret prompt")
    assert len(h) == 16
    assert prompt_hash("secret prompt") == h
