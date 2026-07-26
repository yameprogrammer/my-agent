#!/usr/bin/env python3
"""
푸시 전 간단 시크릿 스캔 (실 키 패턴 탐지).
종료 코드 1 이면 커밋/푸시를 중단하세요.

  python scripts/check_no_secrets.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 실 시크릿으로 보이는 고위험 패턴 (테스트 더미 nvapi-writer-key 등은 길이로 완화)
PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI-style secret key"),
    (re.compile(r"sk-proj-[a-zA-Z0-9_-]{20,}"), "OpenAI project key"),
    (re.compile(r"nvapi-[a-zA-Z0-9_-]{20,}"), "NVIDIA API key"),
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}"), "Google API key"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "GitHub PAT"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"), "Private key block"),
    (re.compile(r"eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\."), "JWT-like token"),
]

# 스캔에서 제외 (문서·테스트 더미·이 스크립트)
SKIP_DIR_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "frontend/dist", "frontend/node_modules", ".pytest_cache",
}
SKIP_FILE_NAMES = {
    "check_no_secrets.py",
}
# 테스트/문서 허용 더미 접두 (완전 일치가 아닌 부분 문자열 예외)
ALLOW_SUBSTRINGS = (
    "nvapi-test-key",
    "nvapi-writer-key",
    "test-openai-key",
    "test-google-key",
    "test-anthropic-key",
    "test-secret-key",
    "test-default-key",
    "user-key-dummy",
    "dummy-key",
    "dev-secret-key-do-not-use-in-production",
)


def tracked_or_all_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        rels = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        return [ROOT / p for p in rels]
    except Exception:
        files: list[Path] = []
        for p in ROOT.rglob("*"):
            if not p.is_file():
                continue
            parts = set(p.relative_to(ROOT).parts)
            if parts & SKIP_DIR_PARTS:
                continue
            files.append(p)
        return files


def main() -> int:
    hits: list[str] = []
    for path in tracked_or_all_files():
        if path.name in SKIP_FILE_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for i, line in enumerate(text.splitlines(), 1):
            if any(a in line for a in ALLOW_SUBSTRINGS):
                continue
            for rx, label in PATTERNS:
                if rx.search(line):
                    hits.append(f"{rel}:{i}: possible {label}")
                    break

    if hits:
        print("SECURITY: possible secrets found in tracked files:")
        for h in hits[:50]:
            print("  ", h)
        if len(hits) > 50:
            print(f"  ... and {len(hits) - 50} more")
        print("\nRemove secrets before push. Use .env (gitignored) for real keys.")
        return 1

    print("OK: no high-risk secret patterns in tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
