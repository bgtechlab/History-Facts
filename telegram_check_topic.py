"""
Telegram Topic Checker (History Facts Bot)
============================================
Telegram par jo bhi text message aaye, use topic माना jaata hai.
- Message me kahin bhi "shorts" shabd ho -> format = shorts
- Warna -> format = long
- Message "auto" ho (ya sirf format keyword ho, koi topic naam na ho) -> topic khali
  chhoड़ dete hain, taaki AI khud topic chun le.

Zaroori env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import re
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
OFFSET_FILE = ".telegram_offset"
GITHUB_OUTPUT = os.getenv("GITHUB_OUTPUT")


def read_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE) as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0
    return 0


def write_offset(v):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(v))


def set_output(topic, video_format):
    if GITHUB_OUTPUT:
        with open(GITHUB_OUTPUT, "a") as f:
            f.write(f"topic={topic}\nvideo_format={video_format}\nhas_request={'true' if video_format else 'false'}\n")
    print(f"topic='{topic}' video_format='{video_format}'")


def reply(text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text}, timeout=15)
    except Exception:
        pass


def main():
    if not BOT_TOKEN or not CHAT_ID:
        set_output("", "")
        return

    offset = read_offset()
    try:
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                             params={"offset": offset + 1, "timeout": 0}, timeout=20)
        data = resp.json()
    except Exception as e:
        print(f"⚠️ getUpdates fail: {e}")
        set_output("", "")
        return

    if not data.get("ok"):
        set_output("", "")
        return

    topic, video_format = "", ""
    max_update_id = offset

    for update in data.get("result", []):
        max_update_id = max(max_update_id, update.get("update_id", 0))
        msg = update.get("message", {})
        if str(msg.get("chat", {}).get("id", "")) != CHAT_ID:
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue

        is_shorts = bool(re.search(r"short", text, re.I))
        video_format = "shorts" if is_shorts else "long"
        cleaned = re.sub(r"\bshorts?\b", "", text, flags=re.I).strip(" -:,")
        topic = "" if cleaned.lower() in ("", "auto", "koi bhi", "any") else cleaned

    write_offset(max_update_id)

    if video_format:
        reply(f"✅ Mil gaya! Format: {video_format}, Topic: {topic or '(AI khud chunega)'}\nVideo banna shuru ho raha hai.")
    else:
        print("ℹ️ Koi naya message nahi mila.")

    set_output(topic, video_format)


if __name__ == "__main__":
    main()
