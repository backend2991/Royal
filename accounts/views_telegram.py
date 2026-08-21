import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import telegram_bot
from .models import TelegramVerificationToken

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def telegram_webhook(request, secret):
    """Receives all updates from Telegram for this bot.

    URL includes a shared secret (settings.TELEGRAM_WEBHOOK_SECRET) so that
    only requests actually coming from Telegram (which we configured with
    this exact URL via setWebhook) are accepted — anyone guessing
    /telegram/webhook/ without the secret gets rejected.
    """
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        return HttpResponseForbidden("invalid secret")

    try:
        update = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    message = update.get("message")
    if not message:
        return JsonResponse({"ok": True})  # ignore edited_message, callback_query, etc.

    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    contact = message.get("contact")

    if text.startswith("/start"):
        _handle_start(chat_id, text)
    elif contact:
        _handle_contact_share(chat_id, contact, telegram_user_id=message["from"]["id"])
    else:
        telegram_bot.send_message(
            chat_id,
            "Please open the verification link sent by the restaurant admin "
            "registration page, or tap the button to share your phone number.",
        )

    return JsonResponse({"ok": True})


def _handle_start(chat_id: int, text: str):
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        telegram_bot.send_message(chat_id, "Welcome! This bot verifies restaurant admin accounts. "
                                             "Please use the link provided during registration.")
        return

    token_str = parts[1].strip()
    token = TelegramVerificationToken.objects.filter(token=token_str).first()

    if not token or not token.is_valid():
        telegram_bot.send_message(
            chat_id,
            "⚠️ This verification link is invalid or has expired. "
            "Please restart registration on the website.",
        )
        return

    # Record which chat is *attempting* this token. Nothing is activated yet —
    # activation only happens once the shared contact's phone number is
    # checked against token.phone_number in _handle_contact_share below.
    token.pending_chat_id = chat_id
    token.save(update_fields=["pending_chat_id"])

    telegram_bot.send_message(
        chat_id,
        f"Hello {token.admin_user.first_name or ''}! To confirm this is really "
        f"your phone number, please tap the button below to share your contact.",
        reply_markup=telegram_bot.request_contact_keyboard("📱 Share my phone number"),
    )


def _handle_contact_share(chat_id: int, contact: dict, telegram_user_id: int):
    # Security check #1: the contact card must belong to the person chatting
    # with the bot, not one they forwarded from someone else.
    if contact.get("user_id") != telegram_user_id:
        telegram_bot.send_message(
            chat_id,
            "⚠️ Please share YOUR OWN contact card, not someone else's.",
            reply_markup=telegram_bot.remove_keyboard(),
        )
        return

    token = TelegramVerificationToken.objects.filter(
        pending_chat_id=chat_id, is_used=False
    ).order_by("-created_at").first()

    if not token or not token.is_valid():
        telegram_bot.send_message(
            chat_id,
            "⚠️ No active verification request found for this chat, or it has expired. "
            "Please restart registration on the website.",
            reply_markup=telegram_bot.remove_keyboard(),
        )
        return

    shared_phone = telegram_bot.normalize_phone(contact.get("phone_number", ""))
    expected_phone = telegram_bot.normalize_phone(token.phone_number)

    # Security check #2 (the core constraint): the phone number Telegram
    # reports for THIS chat must exactly match what was submitted at
    # registration. If a different Telegram user opens the same /start link
    # and shares *their* contact, the numbers won't match and activation
    # is rejected — the admin_user stays is_active=False.
    if shared_phone != expected_phone:
        telegram_bot.send_message(
            chat_id,
            "❌ Verification failed: this Telegram account's phone number "
            "does not match the one submitted during registration. "
            "Activation was NOT granted.",
            reply_markup=telegram_bot.remove_keyboard(),
        )
        logger.warning(
            "Telegram verification phone mismatch: token=%s expected=%s got=%s chat_id=%s",
            token.token, expected_phone, shared_phone, chat_id,
        )
        return

    # Match confirmed -> activate the account.
    user = token.admin_user
    user.is_active = True
    user.telegram_chat_id = chat_id
    user.save(update_fields=["is_active", "telegram_chat_id"])

    token.is_used = True
    token.save(update_fields=["is_used"])

    telegram_bot.send_message(
        chat_id,
        "✅ Your phone number is verified and your admin account is now active. "
        "You can log in on the restaurant dashboard.",
        reply_markup=telegram_bot.remove_keyboard(),
    )
