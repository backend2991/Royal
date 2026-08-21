from django.urls import path

from . import views_telegram

urlpatterns = [
    path("webhook/<str:secret>/", views_telegram.telegram_webhook, name="telegram_webhook"),
]
