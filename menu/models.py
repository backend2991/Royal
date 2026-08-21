from django.db import models
from django.utils.translation import gettext_lazy as _


class RestaurantTable(models.Model):
    """A physical table. Each table gets its own QR code pointing at
    /menu/?table=<number>, so ordering requires no customer account."""

    number = models.PositiveIntegerField(unique=True, verbose_name=_("Table number"))
    seats = models.PositiveSmallIntegerField(default=4, verbose_name=_("Seats"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        ordering = ["number"]
        verbose_name = _("Restaurant table")
        verbose_name_plural = _("Restaurant tables")

    def __str__(self):
        return f"Table {self.number}"

    def qr_target_path(self) -> str:
        """Relative path to encode in this table's QR code."""
        return f"/menu/?table={self.number}"


class RestaurantLocation(models.Model):
    """Singleton-ish model holding the true GPS coordinates of the venue,
    used to validate customers' browser-reported location on order submission.
    Falls back to settings.RESTAURANT_LATITUDE/LONGITUDE if no row exists."""

    name = models.CharField(max_length=120, default="Main branch")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    allowed_radius_meters = models.PositiveIntegerField(default=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Restaurant location")
        verbose_name_plural = _("Restaurant locations")

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    name_uz = models.CharField(max_length=100, blank=True, verbose_name=_("Name (UZ)"))
    name_ru = models.CharField(max_length=100, blank=True, verbose_name=_("Name (RU)"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display order"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name

    def localized_name(self, lang_code: str) -> str:
        return {"uz": self.name_uz, "ru": self.name_ru}.get(lang_code) or self.name


class MenuItem(models.Model):
    category = models.ForeignKey(Category, related_name="items", on_delete=models.CASCADE, verbose_name=_("Category"))
    name = models.CharField(max_length=150, verbose_name=_("Name"))
    name_uz = models.CharField(max_length=150, blank=True, verbose_name=_("Name (UZ)"))
    name_ru = models.CharField(max_length=150, blank=True, verbose_name=_("Name (RU)"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    description_uz = models.TextField(blank=True, verbose_name=_("Description (UZ)"))
    description_ru = models.TextField(blank=True, verbose_name=_("Description (RU)"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"))
    image = models.ImageField(upload_to="menu_items/", blank=True, null=True, verbose_name=_("Photo"))
    is_available = models.BooleanField(default=True, verbose_name=_("Available"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Featured"))

    class Meta:
        ordering = ["category__order", "name"]
        verbose_name = _("Menu item")
        verbose_name_plural = _("Menu items")

    def __str__(self):
        return f"{self.name} ({self.price})"

    def localized_name(self, lang_code: str) -> str:
        return {"uz": self.name_uz, "ru": self.name_ru}.get(lang_code) or self.name

    def localized_description(self, lang_code: str) -> str:
        return {"uz": self.description_uz, "ru": self.description_ru}.get(lang_code) or self.description
