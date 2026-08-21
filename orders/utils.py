"""Anti-remote-ordering verification helpers.

Two independent signals are checked before an order is allowed through:

1. EXIF timestamp on the uploaded photo — proves the photo itself is fresh
   (captured within PHOTO_MAX_AGE_MINUTES of submission), not an old photo
   pulled from the gallery.
2. Browser Geolocation coordinates submitted alongside the form — proves the
   *device* is physically within GEO_ALLOWED_RADIUS_METERS of the restaurant.

Both are attached to the Order for staff auditing (dashboard shows the photo,
the distance, and whether EXIF was present at all).
"""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional

from django.conf import settings
from django.utils import timezone
from PIL import ExifTags, Image

EXIF_DATETIME_TAGS = {"DateTimeOriginal", "DateTimeDigitized", "DateTime"}


@dataclass
class ExifResult:
    captured_at: Optional[datetime]
    has_exif: bool
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None


def _convert_to_degrees(value):
    """Convert an EXIF GPS coordinate (tuple of IFDRational deg/min/sec) to float degrees."""
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def extract_exif(file_obj) -> ExifResult:
    """Read EXIF capture time (and GPS if present) from an uploaded image.

    `file_obj` is a Django UploadedFile; we read it without persisting any
    state on the file pointer for the caller.
    """
    try:
        file_obj.seek(0)
        image = Image.open(file_obj)
        raw_exif = image._getexif()  # noqa: SLF001 - Pillow's documented low-level accessor
    except Exception:
        raw_exif = None
    finally:
        try:
            file_obj.seek(0)
        except Exception:
            pass

    if not raw_exif:
        return ExifResult(captured_at=None, has_exif=False)

    tagged = {ExifTags.TAGS.get(tag_id, tag_id): value for tag_id, value in raw_exif.items()}

    captured_at = None
    for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        raw_value = tagged.get(tag_name)
        if raw_value:
            try:
                captured_at = datetime.strptime(raw_value, "%Y:%m:%d %H:%M:%S")
                break
            except (ValueError, TypeError):
                continue

    gps_lat = gps_lon = None
    gps_info = tagged.get("GPSInfo")
    if gps_info:
        gps_tagged = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()}
        try:
            lat = _convert_to_degrees(gps_tagged["GPSLatitude"])
            if gps_tagged.get("GPSLatitudeRef") in ("S", "s"):
                lat = -lat
            lon = _convert_to_degrees(gps_tagged["GPSLongitude"])
            if gps_tagged.get("GPSLongitudeRef") in ("W", "w"):
                lon = -lon
            gps_lat, gps_lon = lat, lon
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    return ExifResult(captured_at=captured_at, has_exif=True, gps_latitude=gps_lat, gps_longitude=gps_lon)


def is_photo_fresh(captured_at: Optional[datetime], max_age_minutes: Optional[int] = None) -> bool:
    """True if the EXIF timestamp is within the allowed window of "now".

    A missing/naive datetime is treated as unverifiable -> caller decides
    whether to reject or fall back to server-side upload-time as a proxy.
    """
    if captured_at is None:
        return False
    max_age_minutes = max_age_minutes or getattr(settings, "PHOTO_MAX_AGE_MINUTES", 15)
    if timezone.is_naive(captured_at):
        captured_at = captured_at.replace(tzinfo=dt_timezone.utc)
    now = timezone.now()
    delta = now - captured_at
    # Allow a small positive skew for clock drift between phone and server.
    return -timedelta(minutes=1) <= delta <= timedelta(minutes=max_age_minutes)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two lat/lon points."""
    r = 6371000  # Earth radius, meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def is_within_restaurant_radius(lat: float, lon: float) -> tuple[bool, float]:
    """Check browser-reported coordinates against the configured restaurant
    location (DB row if present, else settings fallback). Returns (ok, distance_m)."""
    try:
        from menu.models import RestaurantLocation
        location = RestaurantLocation.objects.filter(is_active=True).first()
    except Exception:
        location = None

    if location:
        target_lat, target_lon, radius = float(location.latitude), float(location.longitude), location.allowed_radius_meters
    else:
        target_lat = getattr(settings, "RESTAURANT_LATITUDE", 41.311081)
        target_lon = getattr(settings, "RESTAURANT_LONGITUDE", 69.240562)
        radius = getattr(settings, "GEO_ALLOWED_RADIUS_METERS", 500)

    distance = haversine_distance_m(lat, lon, target_lat, target_lon)
    return distance <= radius, distance


def check_geo_fence(user_lat, user_lon):
    """
    Wrapper function for views.
    Returns (is_valid, distance_in_meters, (lat, lon))
    """
    if user_lat is None or user_lon is None:
        return False, 0.0, (None, None)

    try:
        lat = float(user_lat)
        lon = float(user_lon)
    except (ValueError, TypeError):
        return False, 0.0, (None, None)

    is_valid, distance = is_within_restaurant_radius(lat, lon)
    return is_valid, round(distance, 2), (lat, lon)