"""
프론트 parseFilenameFromDisposition 과 동등한 파일명 파싱 단위 검증.
(브라우저 없이 Content-Disposition UTF-8 규약 회귀 방지)
"""
from urllib.parse import quote, unquote
import re


def parse_filename_from_disposition(disposition: str, fallback: str = "download") -> str:
    if not disposition:
        return fallback
    m = re.search(r"filename\*\s*=\s*UTF-8''([^;]+)", disposition, re.I)
    if m:
        return unquote(m.group(1).strip().strip("'\""))
    m = re.search(r'filename\s*=\s*((["\']).*?\2|[^;\n]*)', disposition, re.I)
    if m:
        return m.group(1).strip().strip("'\"") or fallback
    return fallback


def test_parse_filename_utf8_star():
    title = "우주 저편의 서재.txt"
    disp = f"attachment; filename*=UTF-8''{quote(title)}"
    assert parse_filename_from_disposition(disp) == title


def test_parse_filename_plain():
    disp = 'attachment; filename="novel.txt"'
    assert parse_filename_from_disposition(disp) == "novel.txt"


def test_parse_filename_fallback():
    assert parse_filename_from_disposition(None, "fallback.bin") == "fallback.bin"
