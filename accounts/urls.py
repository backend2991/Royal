from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("pending/", views.pending_activation_view, name="pending_activation"),
    path("pending/<uuid:token>/status.json/", views.activation_status_json, name="activation_status_json"),
    path("login/", views.AdminLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
]
