from __future__ import annotations
import base64
import os
import time
import uuid
from pathlib import Path
import requests

API_ROOT = "https://botapi.rubika.ir/v3"
TOKEN = os.environ["RUBIKA_BOT_TOKEN"].strip()
REPOSITORY = os.environ["GITHUB_REPOSITORY"]
GH_TOKEN = os.environ["GH_TOKEN"]
ALLOWED_USERS = {x.strip() for x in os.environ.get("RUBIKA_ALLOWED_USERS", "").split(",") if x.strip()}
OFFSET_FILE = Path("state/offset_id.txt")
MAX_CODE_BYTES = 12_000
POLL_SECONDS = 225
session = requests.Session()

def api(method: str, payload: dict) -> dict:
    response = session.post(f"{API_ROOT}/{TOKEN}/{method}", json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Invalid Rubika API response")
    data = body.get("data")
    return data if isinstance(data, dict) else body

def send(chat_id: str, text: str) -> None:
    api("sendMessage", {"chat_id": str(chat_id), "text": text[:3500]})

def dispatch(chat_id: str, code: str) -> None:
    encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
    response = session.post(
        f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/python-worker.yml/dispatches",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {GH_TOKEN}", "X-GitHub-Api-Version": "2022-11-28"},
        json={"ref": "main", "inputs": {"chat_id": str(chat_id), "code_b64": encoded, "request_id": uuid.uuid4().hex[:12]}},
        timeout=20,
    )
    if response.status_code not in (201, 204):
        raise RuntimeError(f"GitHub workflow dispatch failed: HTTP {response.status_code}")

def read_offset():
    try:
        value = OFFSET_FILE.read_text(encoding="utf-8").strip()
        return value or None
    except FileNotFoundError:
        return None

def save_offset(value):
    if value:
        OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
        OFFSET_FILE.write_text(str(value), encoding="utf-8")

def handle_update(update: dict) -> None:
    if update.get("type") not in ("NewMessage", "StartedBot", ""):
        return
    message = update.get("new_message") or {}
    if not isinstance(message, dict) or message.get("sender_type") == "Bot":
        return
    sender_id = str(message.get("author_id") or message.get("sender_id") or update.get("user_id") or "")
    chat_id = str(update.get("chat_id") or "")
    text = str(message.get("text") or "").strip()
    if not chat_id or not text:
        return
    if text in ("/start", "/help", "راهنما"):
        send(chat_id, "ربات اجرای پایتون ☁️\nبرای اجرا بفرست:\n\nپایتون:\nprint('Hello')\n\nهر اجرا روی runner تازه انجام می‌شود؛ فایل و کتابخانه بین اجراها باقی نمی‌ماند.")
        return
    if sender_id not in ALLOWED_USERS:
        send(chat_id, "دسترسی اجرای کد برای این حساب فعال نیست.")
        return
    if not text.startswith("پایتون:"):
        send(chat_id, "دستور نامعتبر است. برای راهنما /help را بفرست.")
        return
    code = text[len("پایتون:"):].lstrip("\r\n ")
    if not code:
        send(chat_id, "کد پایتون خالی است.")
        return
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        send(chat_id, "حجم کد بیش از حد مجاز است (حداکثر ۱۲ کیلوبایت).")
        return
    dispatch(chat_id, code)
    send(chat_id, "کد دریافت شد؛ محیط اجرای جداگانه در GitHub Actions ساخته شد. ⏳")

def main() -> None:
    if not ALLOWED_USERS:
        raise SystemExit("RUBIKA_ALLOWED_USERS is empty; refusing to run.")
    offset_id = read_offset()
    deadline = time.monotonic() + POLL_SECONDS
    print("Rubika poller started")
    while time.monotonic() < deadline:
        payload = {"limit": 20}
        if offset_id:
            payload["offset_id"] = offset_id
        try:
            result = api("getUpdates", payload)
            updates = result.get("updates", [])
            if not isinstance(updates, list):
                raise ValueError("Rubika updates field is not a list")
            for update in updates:
                if isinstance(update, dict):
                    try:
                        handle_update(update)
                    except Exception as error:
                        print(f"Update handling error: {type(error).__name__}: {error}")
            next_offset = result.get("next_offset_id")
            if next_offset:
                offset_id = str(next_offset)
                save_offset(offset_id)
        except (requests.RequestException, ValueError, RuntimeError) as error:
            print(f"Polling error: {type(error).__name__}: {error}")
            time.sleep(5)
            continue
        time.sleep(3)

if __name__ == "__main__":
    main()
