from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# Non-translated URLs: Telegram webhook, health check, admin site.
urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("telegram/", include("accounts.telegram_urls")),
    path("i18n/", include("django.conf.urls.i18n")),  # powers the language switcher form
]

# Translated / language-prefixed URLs (/en/..., /ru/..., /uz/...).
# prefix_default_language=False keeps English at the root (/menu/) which is
# what QR codes will point to, while /ru/menu/ and /uz/menu/ also work.
urlpatterns += i18n_patterns(
    path("", include("menu.urls")),
    path("orders/", include("orders.urls")),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
