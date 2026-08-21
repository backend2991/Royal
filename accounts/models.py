import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AdminUser(AbstractUser):
    """Staff/admin account. Registration creates the row with is_active=False;
    it only flips to True once the Telegram verification challenge (see
    TelegramVerificationToken) confirms control of the exact phone number
    submitted at registration."""

    phone_number = models.CharField(max_length=20, unique=True, verbose_name=_("Phone number"))
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    is_active = models.BooleanField(
        default=True,
        help_text=_("Designates whether this admin can log in. Flipped to True by Telegram verification."),
    )

    REQUIRED_FIELDS = ["email", "phone_number"]  # username still required by AbstractUser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.phone_number})"


def default_token_expiry():
    return timezone.now() + timedelta(minutes=15)


class TelegramVerificationToken(models.Model):
    """One-time token bridging a registration attempt to a Telegram chat.

    Flow:
      1. Register -> token created, phone_number snapshotted from the form.
      2. User opens t.me/<bot>?start=<token> -> webhook records telegram_chat_id
         (`pending`, not yet verified) and asks the user to share their contact.
      3. User taps "Share phone number" -> webhook compares the *shared*
         contact's phone number against `phone_number` on this token.
         Only on an exact match is the linked AdminUser activated.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    admin_user = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name="verification_tokens")
    phone_number = models.CharField(max_length=20)

    # Set once the user hits /start in Telegram, before contact is confirmed.
    pending_chat_id = models.BigIntegerField(null=True, blank=True)

    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_token_expiry)

    class Meta:
        verbose_name = _("Telegram verification token")
        verbose_name_plural = _("Telegram verification tokens")

    def __str__(self):
        return f"Token for {self.admin_user} ({'used' if self.is_used else 'pending'})"

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired()
