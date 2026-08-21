"""Thin wrapper around the Telegram Bot API (plain HTTPS calls via requests —
no long-running polling process needed since we operate purely via webhook,
which fits Django's request/response model)."""
import logging
import re
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _api_url(method: str) -> str:
    return f"{settings.TELEGRAM_API_BASE}/{method}"


def send_message(chat_id, text: str, reply_markup: Optional[dict] = None) -> bool:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = requests.post(_api_url("sendMessage"), json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Telegram sendMessage failed for chat_id=%s", chat_id)
        return False


def request_contact_keyboard(button_text: str) -> dict:
    """Reply keyboard with a single 'share my phone number' button. Telegram
    fills in the real phone number tied to the user's account server-side —
    the user cannot type an arbitrary number into this flow."""
    return {
        "keyboard": [[{"text": button_text, "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def remove_keyboard() -> dict:
    return {"remove_keyboard": True}


def build_deep_link(token: str) -> str:
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"


def normalize_phone(raw: str) -> str:
    """Strip everything but leading + and digits, for robust comparison
    between what the customer typed at registration and what Telegram's
    contact-share reports (which sometimes differ in spacing/leading zeros)."""
    if not raw:
        return ""
    cleaned = re.sub(r"[^\d+]", "", raw)
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned.lstrip("0")
    return cleaned


def set_webhook(public_url: str) -> dict:
    """Call once (e.g. from a management command or manually) to point
    Telegram at /telegram/webhook/<secret>/."""
    resp = requests.post(_api_url("setWebhook"), json={"url": public_url}, timeout=10)
    return resp.json()