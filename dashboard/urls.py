from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("orders/feed.json/", views.orders_feed_json, name="orders_feed_json"),
    path("orders/<int:order_id>/status/", views.update_order_status, name="update_order_status"),
]
