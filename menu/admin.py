from django.contrib import admin
from django.utils.html import format_html

from .models import Category, MenuItem, RestaurantLocation, RestaurantTable
from django.utils.html import format_html
from django.utils.http import urlencode

from django.utils.translation import gettext_lazy as _

@admin.register(RestaurantLocation)
class RestaurantLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "latitude", "longitude", "allowed_radius_meters", "is_active", "map_preview")
    list_editable = ("allowed_radius_meters", "is_active")
    readonly_fields = ("map_preview",)

    fieldsets = (
        (_("Asosiy ma'lumotlar"), {
            "fields": ("name", "is_active")
        }),
        (_("GPS va Radiusi"), {
            "fields": ("latitude", "longitude", "allowed_radius_meters"),
            "description": _("Buyurtma beruvchining geolokatsiyasi ushbu belgilangan radius ichida tekshiriladi.")
        }),
        (_("Xaritadagi joylashuv"), {
            "fields": ("map_preview",)
        }),
    )

    def map_preview(self, obj):
        """Google va Yandex Maps havolalari hamda vizual havola chiqarish."""
        if obj.latitude and obj.longitude:
            google_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            yandex_url = f"https://yandex.com/maps/?pt={obj.longitude},{obj.latitude}&z=17&l=map"

            return format_html(
                '<div style="line-height: 1.8;">'
                '📍 <strong>Koordinata:</strong> {}, {}<br>'
                '🔗 <a href="{}" target="_blank" style="color: #4285F4; font-weight: bold; margin-right: 15px;">Google Maps-da ochish ↗</a>'
                '🔗 <a href="{}" target="_blank" style="color: #FC3F1D; font-weight: bold;">Yandex Maps-da ochish ↗</a>'
                '</div>',
                obj.latitude,
                obj.longitude,
                google_url,
                yandex_url,
            )
        return "-"

    map_preview.short_description = _("Xaritada ko'rish")

    # YANGILANDI: "return False" o'rniga "return True" berildi
    def has_add_permission(self, request):
        """Ko'p restoran lokatsiyalarini qo'shishga ruxsat beradi."""
        return True


@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ("number", "seats", "is_active", "qr_link")
    list_filter = ("is_active",)

    # 1. Tahrirlash sahifasida ko'rinadigan maydonlar tartibi:
    fields = ("number", "seats", "is_active", "qr_link")

    # 2. qr_link obyekt bo'lmagani uchun uni read-only (faqat o'qish uchun) qilib ko'rsatamiz:
    readonly_fields = ("qr_link",)

    def qr_link(self, obj):
        if not obj.pk:
            return "-"

        # Domen / URL manzilini shakllantirish
        path = obj.qr_target_path()
        target = f"http://127.0.0.1:8000{path}"  # Production'da o'zingizni domeningiz bilan almashtiring

        params = urlencode({"size": "150x150", "data": target})
        img_src = f"https://api.qrserver.com/v1/create-qr-code/?{params}"

        return format_html(
            '<div style="margin-top: 5px;">'
            '<a href="{}" target="_blank">'
            '<img src="{}" width="150" height="150" style="border: 1px solid #ccc; padding: 5px; background: #fff;" />'
            "</a>"
            '<br><small><a href="{}" target="_blank">{}</a></small>'
            "</div>",
            target,
            img_src,
            target,
            target,
        )

    qr_link.short_description = "QR Code Preview"


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    fields = ("name", "price", "is_available", "is_featured", "image")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available", "is_featured")
    list_filter = ("category", "is_available", "is_featured")
    search_fields = ("name", "name_uz", "name_ru")



