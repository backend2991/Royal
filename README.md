# Restaurant Digital Menu & Ordering System (Django MVT)

A monolithic Django app: QR-code table ordering, camera + geolocation
"anti-remote-ordering" verification, Telegram-based admin verification,
EN/RU/UZ i18n, dark/light mode, and a live admin dashboard.

## Apps

| App        | Responsibility                                                        |
|------------|-------------------------------------------------------------------------|
| `menu`     | Categories, menu items, tables, restaurant GPS location, `/menu/?table=N` |
| `orders`   | Order model, EXIF + geolocation verification, checkout, status tracking (AJAX/SSE) |
| `accounts` | Custom `AdminUser`, registration, Telegram Bot webhook & verification flow |
| `dashboard`| Staff-facing live order board with polling + audio alerts               |

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME,
# TELEGRAM_WEBHOOK_SECRET, RESTAURANT_LATITUDE/LONGITUDE

python manage.py migrate
python manage.py createsuperuser   # for /django-admin/ access to seed menu data
python manage.py compilemessages   # requires the `gettext` system package
python manage.py runserver
```

Seed at least one `RestaurantTable` (e.g. number=5) and a `RestaurantLocation`
row via `/django-admin/`, then visit `/menu/?table=5`.

## Telegram bot setup

1. Create a bot with **@BotFather**, grab the token → `TELEGRAM_BOT_TOKEN`,
   set `TELEGRAM_BOT_USERNAME` to its `@username` (without `@`).
2. Expose your dev server over HTTPS (e.g. `ngrok http 8000`).
3. Point Telegram at your webhook once:

```python
python manage.py shell -c "
from accounts.telegram_bot import set_webhook
from django.conf import settings
print(set_webhook(f'https://YOUR_NGROK_DOMAIN/telegram/webhook/{settings.TELEGRAM_WEBHOOK_SECRET}/'))
"
```

4. Register an admin at `/accounts/register/` → open the Telegram deep link
   → tap "Share my phone number" → account activates automatically
   (`AdminUser.is_active` flips to `True` only if the shared contact's phone
   number exactly matches what was submitted at registration).

## Geo-verification notes

- **EXIF check** (`orders/utils.py::is_photo_fresh`): rejects photos whose
  `DateTimeOriginal` EXIF tag is older than `PHOTO_MAX_AGE_MINUTES` (default 5).
  Note many mobile browsers strip EXIF from `getUserMedia`/canvas-captured
  images — in that case the system falls back to the **geolocation** check
  as the primary presence signal (see `OrderForm.clean()`).
- **Geolocation check**: browser `navigator.geolocation` coordinates are
  compared via the haversine formula against `RestaurantLocation` (DB) or
  the `RESTAURANT_LATITUDE`/`LONGITUDE`/`GEO_ALLOWED_RADIUS_METERS` env vars.
- Both signals, plus the photo itself, are stored on `Order` for staff
  auditing in the dashboard/admin.

## i18n

`.po` files for `ru` and `uz` are in `locale/`. Run
`django-admin compilemessages` (needs the `gettext` package installed on
your OS — `apt install gettext` / `brew install gettext`) to generate the
`.mo` files Django actually loads. The language switcher in the navbar
posts to Django's built-in `set_language` view.

## Dashboard audio alert

Drop an MP3 at `static/audio/new_order.mp3` (referenced by
`templates/dashboard/dashboard.html`) — no royalty-free file is bundled here.

## Production checklist (not included, by design of this scaffold)

- Switch `DEBUG=False`, set a real `DJANGO_SECRET_KEY`, configure `ALLOWED_HOSTS`.
- Serve static/media via whitenoise/nginx + S3-compatible storage.
- Run behind gunicorn/uvicorn + nginx; SSE (`orders/views.py::order_status_stream`)
  needs a WSGI/ASGI server that supports long-lived connections (works with
  `gunicorn --worker-class gevent` or an ASGI server; plain sync WSGI workers
  will block per connection — fine for small deployments, not for scale).
- Add rate-limiting to `/orders/checkout/` and the Telegram webhook.
- Consider Redis/Channels if you want true push instead of polling/SSE-over-WSGI.
