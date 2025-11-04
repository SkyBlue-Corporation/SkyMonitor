import requests
import os

def send_telegram_alert(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Token ou chat_id Telegram manquant.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("📨 Alerte Telegram envoyée.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur Telegram: {e}")
