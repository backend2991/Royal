import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from menu.models import MenuItem, RestaurantTable


def verification_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"verification_photos/{instance.order_uid}.{ext}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        IN_KITCHEN = "in_kitchen", _("In Kitchen")
        READY = "ready", _("Ready")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")

    order_uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    table = models.ForeignKey(RestaurantTable, on_delete=models.PROTECT, related_name="orders")

    full_name = models.CharField(max_length=150, verbose_name=_("Full name"))
    phone_number = models.CharField(max_length=20, verbose_name=_("Phone number"))

    # --- Geo / anti-remote-ordering verification ---
    verification_photo = models.ImageField(upload_to=verification_photo_path, verbose_name=_("Live photo"))
    photo_captured_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp extracted from EXIF DateTimeOriginal, if present.",
    )
    browser_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    browser_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distance_from_restaurant_m = models.FloatField(null=True, blank=True)
    geo_verified = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True, verbose_name=_("Special instructions"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order #{self.id} — Table {self.table.number} ({self.get_status_display()})"

    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())

    STATUS_FLOW = [Status.PENDING, Status.ACCEPTED, Status.IN_KITCHEN, Status.READY, Status.DELIVERED]

    def next_status(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return None
        if idx + 1 < len(self.STATUS_FLOW):
            return self.STATUS_FLOW[idx + 1]
        return None


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    item_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
