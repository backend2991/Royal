import json
from decimal import Decimal

import time

from django.http import StreamingHttpResponse

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from menu.models import MenuItem
from .carts import Cart
from .forms import OrderForm
from .models import Order, OrderItem
from .utils import check_geo_fence


# ==========================================
# SAVAT (CART) VIEWS
# ==========================================
@require_POST
def cart_update(request):
    """Savatga mahsulot qo'shish va ayirish uchun AJAX endpoint"""
    cart = Cart(request)
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")  # 'inc' yoki 'dec'

    if not item_id or action not in ["inc", "dec"]:
        return JsonResponse({"ok": False, "error": "Invalid payload"}, status=400)

    menu_item = get_object_or_404(MenuItem, pk=item_id)
    cart.add(item_id=menu_item.id, quantity=1, action=action)

    current_qty = cart.cart.get(str(menu_item.id), {}).get("quantity", 0)

    return JsonResponse({
        "ok": True,
        "item_id": menu_item.id,
        "item_qty": current_qty,
        "total_items": len(cart),
        "total_price": float(cart.get_total_price()),
    })


# ==========================================
# ORDER CHECKOUT & STATUS VIEWS
# ==========================================
def checkout_view(request):
    """Buyurtmani rasmiylashtirish view'si"""
    cart = Cart(request)
    table_id = request.GET.get("table") or request.POST.get("table_id") or request.session.get("table_number")

    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save()  # Saves order and automatically populates table/geo fields

            # Savatdagi mahsulotlarni OrderItem ga o'tkazish from cart_json
            cart_items = form.cleaned_data["cart_json"]
            for item in cart_items:
                menu_item = get_object_or_404(MenuItem, pk=item["id"])
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item["qty"],
                    unit_price=menu_item.price,
                    item_notes=item.get("notes", ""),
                )

            # Buyurtma yaratilgach savatni tozalaymiz
            cart.clear()
            return redirect("orders:status", order_uid=order.order_uid)
    else:
        form = OrderForm(initial={"table_number": table_id})

    return render(request, "orders/order_form.html", {
        "form": form,
        "cart": cart,
        "table_id": table_id,
    })


def order_status_view(request, order_uid):
    """Buyurtma holatini ko'rsatish sahifasi (HTML)"""
    order = get_object_or_404(Order, order_uid=order_uid)
    return render(request, "orders/order_status.html", {"order": order})


@require_GET
def order_status_json(request, order_uid):
    """Buyurtma holatini har necha sekundda tekshirib turish uchun JSON endpoint"""
    order = get_object_or_404(Order, order_uid=order_uid)
    return JsonResponse({
        "status": order.status,
        "status_display": order.get_status_display(),
        "is_completed": order.status in [Order.Status.DELIVERED, Order.Status.CANCELLED],
    })



def order_status_stream(request, order_uid):
    """Buyurtma holatini Server-Sent Events (SSE) orqali real-vaqt rejimida uzatuvchi view"""
    order = get_object_or_404(Order, order_uid=order_uid)

    def event_stream():
        last_status = None
        while True:
            order.refresh_from_db()
            if order.status != last_status:
                last_status = order.status
                data = f'event: status\ndata: {{"status": "{order.status}", "status_display": "{order.get_status_display()}"}}\n\n'
                yield data

            if order.status in [Order.Status.DELIVERED, Order.Status.CANCELLED]:
                break

            time.sleep(3)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response