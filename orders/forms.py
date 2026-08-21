import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from menu.models import RestaurantTable

from . import utils
from .models import Order


class OrderForm(forms.ModelForm):
    """Customer-facing order form.

    Fields per spec: Full Name, Phone Number, auto-detected Table Number
    (hidden input), and the Live Photo captured via the HTML5 Camera API.
    Cart contents (menu item ids/quantities) travel as a hidden JSON field
    built client-side by the menu page's "Add to order" buttons.
    """

    table_number = forms.IntegerField(widget=forms.HiddenInput())
    browser_latitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    browser_longitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    cart_json = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Order
        fields = ["full_name", "phone_number", "verification_photo", "notes"]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "w-full rounded-lg border px-4 py-3 dark:bg-gray-800 dark:border-gray-600",
                "placeholder": _("e.g. Aziz Karimov"),
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "w-full rounded-lg border px-4 py-3 dark:bg-gray-800 dark:border-gray-600",
                "placeholder": "+998 90 123 45 67",
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full rounded-lg border px-4 py-3 dark:bg-gray-800 dark:border-gray-600",
                "rows": 2,
            }),
            "verification_photo": forms.FileInput(attrs={
                "class": "hidden",
                "id": "id_verification_photo",
                "accept": "image/*",
                "capture": "environment",
            }),
        }

    def clean_table_number(self):
        number = self.cleaned_data["table_number"]
        if not RestaurantTable.objects.filter(number=number, is_active=True).exists():
            raise ValidationError(_("This table could not be verified. Please re-scan the QR code."))
        return number

    def clean_cart_json(self):
        raw = self.cleaned_data["cart_json"]
        try:
            items = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            raise ValidationError(_("Your order could not be read. Please rebuild it from the menu."))
        if not items or not isinstance(items, list):
            raise ValidationError(_("Your order is empty. Please add at least one item."))
        return items

    def clean(self):
        cleaned_data = super().clean()
        photo = cleaned_data.get("verification_photo")
        lat = cleaned_data.get("browser_latitude")
        lon = cleaned_data.get("browser_longitude")

        # --- 1. EXIF freshness check ------------------------------------
        if photo:
            exif = utils.extract_exif(photo)
            self._exif_result = exif
            if exif.has_exif and exif.captured_at:
                if not utils.is_photo_fresh(exif.captured_at):
                    raise ValidationError(
                        _("This photo was taken more than %(minutes)d minutes ago. "
                          "Please take a new photo right now to confirm you're at the restaurant.")
                        % {"minutes": 5}
                    )
            else:
                # No EXIF timestamp at all (common for browser camera capture,
                # which often strips EXIF, or screenshots/gallery re-saves).
                # We don't hard-block on this alone — geolocation below is the
                # primary signal in that case — but we flag it for staff review.
                self.exif_missing = True
        else:
            self._exif_result = None

        # --- 2. Geolocation radius check ---------------------------------
        if lat is not None and lon is not None:
            ok, distance = utils.is_within_restaurant_radius(float(lat), float(lon))
            cleaned_data["_geo_distance_m"] = distance
            cleaned_data["_geo_ok"] = ok
            if not ok:
                raise ValidationError(
                    _("You appear to be %(distance)d meters from the restaurant. "
                      "Orders can only be placed while inside the venue.")
                    % {"distance": int(distance)}
                )
        else:
            # No location = cannot verify presence at all. Combined with a
            # missing/failed EXIF timestamp this blocks the order outright.
            if getattr(self, "exif_missing", False) or not photo:
                raise ValidationError(
                    _("We couldn't verify your location. Please allow camera and "
                      "location access and try again.")
                )
            cleaned_data["_geo_ok"] = False
            cleaned_data["_geo_distance_m"] = None

        return cleaned_data

    def save(self, commit=True):
        order = super().save(commit=False)
        order.table = RestaurantTable.objects.get(number=self.cleaned_data["table_number"])
        exif = getattr(self, "_exif_result", None)
        if exif and exif.captured_at:
            captured = exif.captured_at
            if timezone.is_naive(captured):
                captured = timezone.make_aware(captured, timezone.utc)
            order.photo_captured_at = captured
        order.browser_latitude = self.cleaned_data.get("browser_latitude")
        order.browser_longitude = self.cleaned_data.get("browser_longitude")
        order.distance_from_restaurant_m = self.cleaned_data.get("_geo_distance_m")
        order.geo_verified = bool(self.cleaned_data.get("_geo_ok"))
        if commit:
            order.save()
        return order



class OrderCreateForm(forms.ModelForm):
    user_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    user_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Order
        # customer_name o'rniga modeldagi haqiqiy maydon nomini kiriting (masalan: full_name)
        fields = [
            "full_name",  # Modelda qanday bo'lsa shunday yozing (masalan, full_name yoki name)
            "phone_number",
            "table",
            "verification_photo",
            "user_latitude",
            "user_longitude",
        ]
