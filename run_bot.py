import os
import sys
import time
import requests

# Set up Django environment
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from accounts.views_telegram import _handle_start, _handle_contact_share
from accounts.telegram_bot import send_message, remove_keyboard

def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or token == "change-me":
        print("Error: TELEGRAM_BOT_TOKEN is not configured in settings.py or .env file.")
        return

    print(f"Starting Telegram Bot polling for @{settings.TELEGRAM_BOT_USERNAME}...")
    
    # 1. Delete Webhook (otherwise polling won't work)
    api_url = f"https://api.telegram.org/bot{token}"
    try:
        resp = requests.post(f"{api_url}/deleteWebhook")
        resp.raise_for_status()
        print("Successfully deleted existing Telegram webhook (polling mode activated).")
    except Exception as e:
        print(f"Warning: Failed to delete webhook: {e}")

    offset = 0
    while True:
        try:
            url = f"{api_url}/getUpdates?offset={offset}&timeout=10"
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"Error calling getUpdates: {resp.status_code} - {resp.text}")
                time.sleep(3)
                continue
            
            data = resp.json()
            if not data.get("ok"):
                print(f"Telegram API Error: {data.get('description')}")
                time.sleep(3)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                contact = message.get("contact")

                print(f"Received message from chat_id={chat_id}: text='{text}', contact={bool(contact)}")

                if text.startswith("/start"):
                    _handle_start(chat_id, text)
                elif contact:
                    _handle_contact_share(chat_id, contact, telegram_user_id=message["from"]["id"])
                else:
                    send_message(
                        chat_id,
                        "Please open the verification link sent by the restaurant admin "
                        "registration page, or tap the button to share your phone number.",
                    )
        except KeyboardInterrupt:
            print("\nStopping bot polling...")
            break
        except Exception as e:
            print(f"Error in polling loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
