from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminUser, TelegramVerificationToken


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    list_display = ("username", "phone_number", "first_name", "last_name", "is_active", "is_staff", "telegram_chat_id")
    fieldsets = UserAdmin.fieldsets + (
        ("Telegram verification", {"fields": ("phone_number", "telegram_chat_id")}),
    )


@admin.register(TelegramVerificationToken)
class TelegramVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "phone_number", "is_used", "pending_chat_id", "created_at", "expires_at")
    readonly_fields = ("token", "created_at")
