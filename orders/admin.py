from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("menu_item", "quantity", "unit_price", "item_notes")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "full_name", "phone_number", "status", "geo_verified", "photo_preview", "created_at")
    list_filter = ("status", "geo_verified", "table")
    search_fields = ("full_name", "phone_number", "order_uid")
    readonly_fields = (
        "order_uid", "photo_preview", "photo_captured_at", "browser_latitude",
        "browser_longitude", "distance_from_restaurant_m", "geo_verified", "created_at", "updated_at",
    )
    inlines = [OrderItemInline]

    def photo_preview(self, obj):
        if obj.verification_photo:
            return format_html('<img src="{}" style="max-height:120px;border-radius:8px;" />', obj.verification_photo.url)
        return "—"

    photo_preview.short_description = "Verification photo"
