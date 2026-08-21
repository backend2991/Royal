from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from orders.models import Order


@login_required
def dashboard_home(request):
    active_orders = (
        Order.objects.exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
        .select_related("table")
        .prefetch_related("items__menu_item")
    )
    completed_today = Order.objects.filter(
        status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED],
        created_at__date=timezone.now().date(),
    ).count()

    return render(request, "dashboard/dashboard.html", {
        "active_orders": active_orders,
        "status_choices": Order.Status.choices,
        "completed_today": completed_today,
    })


@login_required
@require_GET
def orders_feed_json(request):
    """Polled every few seconds by the dashboard JS to detect new orders
    (triggers the audio alert) and refresh statuses without a full reload."""
    since_id = request.GET.get("since_id", 0)
    orders = (
        Order.objects.exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
        .select_related("table")
        .prefetch_related("items__menu_item")
        .order_by("-id")
    )
    data = []
    for order in orders:
        data.append({
            "id": order.id,
            "order_uid": str(order.order_uid),
            "table_number": order.table.number,
            "full_name": order.full_name,
            "phone_number": order.phone_number,
            "status": order.status,
            "status_display": order.get_status_display(),
            "geo_verified": order.geo_verified,
            "distance_m": order.distance_from_restaurant_m,
            "photo_url": order.verification_photo.url if order.verification_photo else None,
            "created_at": order.created_at.isoformat(),
            "total_amount": str(order.total_amount),
            "items": [
                {"name": i.menu_item.name, "qty": i.quantity, "notes": i.item_notes}
                for i in order.items.all()
            ],
        })
    new_count = sum(1 for o in orders if o.id > int(since_id or 0))
    return JsonResponse({"orders": data, "new_count": new_count, "max_id": orders[0].id if orders else 0})


@login_required
@require_POST
def update_order_status(request, order_id):
    """Handles the Accept / In Kitchen / Ready / Completed / Cancel buttons."""
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get("status")
    valid_statuses = {choice.value for choice in Order.Status}
    if new_status not in valid_statuses:
        return JsonResponse({"ok": False, "error": "invalid status"}, status=400)

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return JsonResponse({"ok": True, "status": order.status, "status_display": order.get_status_display()})
