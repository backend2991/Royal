from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/update/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("<uuid:order_uid>/status/", views.order_status_view, name="status"),
    path("<uuid:order_uid>/status.json/", views.order_status_json, name="status_json"),
    path("<uuid:order_uid>/status/stream/", views.order_status_stream, name="status_stream"),
]
