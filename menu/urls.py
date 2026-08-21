from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("menu/", views.menu_view, name="menu"),
]
