#!/usr/bin/env python3
"""
IMP-21: /health 실패 시 텔레그램 관리자 알림 (cron 용).

환경변수:
  HEALTH_URL (default http://127.0.0.1:8080/health)
  TELEGRAM_BOT_TOKEN
  ADMIN_TELEGRAM_CHAT_ID
  HEALTH_STATE_FILE (optional, 연속 실패 중복 알림 억제)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HEALTH_URL = os.getenv("HEALTH_URL", "http://127.0.0.1:8080/health")
TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.getenv("ADMIN_TELEGRAM_CHAT_ID") or "").strip()
STATE_FILE = Path(
    os.getenv("HEALTH_STATE_FILE")
    or Path(__file__).resolve().parent.parent / "logs" / "health_state.json"
)


def fetch_health() -> tuple[bool, str]:
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status != 200:
                return False, f"HTTP {resp.status}: {body[:200]}"
            return True, body[:300]
    except Exception as e:
        return False, str(e)


def send_telegram(text: str) -> None:
    if not TOKEN or not CHAT_ID:
        print("Telegram not configured; print-only:", text, file=sys.stderr)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except urllib.error.URLError as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)


def load_state() -> dict:
    try:
        if STATE_FILE.is_file():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"last_ok": True, "fail_streak": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def main() -> int:
    ok, detail = fetch_health()
    state = load_state()
    if ok:
        if not state.get("last_ok", True):
            send_telegram(f"✅ novel-agent health recovered\n{HEALTH_URL}")
        save_state({"last_ok": True, "fail_streak": 0})
        print("OK", detail[:120])
        return 0

    streak = int(state.get("fail_streak") or 0) + 1
    save_state({"last_ok": False, "fail_streak": streak})
    # 첫 실패 + 이후 6회마다 (대략 30분 if */5 cron)
    if streak == 1 or streak % 6 == 0:
        send_telegram(
            f"🚨 novel-agent /health FAILED (streak={streak})\n"
            f"URL: {HEALTH_URL}\n"
            f"Detail: {detail[:400]}"
        )
    print("FAIL", detail, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
