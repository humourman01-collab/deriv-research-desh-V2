import requests

from config import settings


def send(text):
    if not (settings.telegram_token and settings.telegram_chat_id):
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"

    chunks = [
        text[i : i + 3800]
        for i in range(0, len(text), 3800)
    ]

    for chunk in chunks:
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }

        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()

    return True
