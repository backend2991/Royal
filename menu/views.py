from django.shortcuts import render
from django.utils import translation

from .models import Category, RestaurantTable


def menu_view(request):
    """Entry point for QR codes: /menu/?table=5

    No login/registration is required. The table number is captured from the
    query string and stashed in the session so it survives navigation to the
    order form and status page without needing to be re-scanned.
    """
    table_number = request.GET.get("table")
    table = None
    if table_number:
        request.session["table_number"] = table_number
        table = RestaurantTable.objects.filter(number=table_number, is_active=True).first()

    lang = translation.get_language()
    categories = (
        Category.objects.filter(is_active=True)
        .prefetch_related("items")
        .order_by("order", "name")
    )

    context = {
        "categories": categories,
        "lang": lang,
        "table": table,
        "table_number": table_number or request.session.get("table_number"),
    }
    return render(request, "menu/menu.html", context)
