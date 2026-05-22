import time
import threading
import requests
from django.conf import settings
from django.utils import timezone
import random

from accounts.models import User, OTP

def generate_otp():
    return f"{random.randint(100000, 999999)}"

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Xatolik: {e}")
        return None

def send_contact_button(chat_id):
    reply_markup = {
        'keyboard': [[{'text': '📱 Telefon raqamni ulashish', 'request_contact': True}]],
        'one_time_keyboard': True,
        'resize_keyboard': True
    }
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': "👇 Ro'yxatdan o'tish uchun tugmani bosing va telefon raqamingizni ulashing:",
        'reply_markup': reply_markup
    }
    try:
        return requests.post(url, json=payload, timeout=10).json()
    except Exception as e:
        print(f"Xatolik: {e}")
        return None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json().get('result', [])
    except Exception as e:
        print(f"Get updates xatolik: {e}")
        return []

def process_message(message):
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    contact = message.get('contact', None)

    if text == '/start':
        send_contact_button(chat_id)
        return

    if contact:
        phone_number = contact.get('phone_number')
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'is_active': False}
        )

        OTP.objects.filter(user=user, created_at__lt=timezone.now() - timezone.timedelta(minutes=5)).delete()
        otp_code = generate_otp()
        OTP.objects.create(user=user, code=otp_code, telegram_chat_id=str(chat_id))

        send_telegram_message(chat_id, f"🔐 Tasdiqlash kodingiz: {otp_code}")

def start_bot():
    print("🚀 Telegram bot ishga tushdi")
    last_update_id = 0
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            for update in updates:
                last_update_id = update.get('update_id')
                if 'message' in update:
                    process_message(update['message'])
            time.sleep(1)
        except Exception as e:
            print(f"Xatolik: {e}")
            time.sleep(5)

def run_bot_async():
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    return bot_thread