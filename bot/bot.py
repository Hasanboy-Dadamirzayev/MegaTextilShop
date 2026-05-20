import time
import threading
import requests
from django.conf import settings
from django.utils import timezone
import random
import os
import django

# Django environment ni sozlash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User, OTP


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def send_telegram_message(chat_id, text):
    """Telegramga xabar yuborish"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        if result.get('ok'):
            print(f"✅ Xabar yuborildi: {chat_id}")
        else:
            print(f"❌ Xabar yuborilmadi: {result}")
        return result
    except Exception as e:
        print(f"Xatolik: {e}")
        return None


def send_contact_button(chat_id):
    """Kontakt jo'natish tugmasini yuborish"""
    reply_markup = {
        'keyboard': [[{'text': '📱 Telefon raqamni ulashish', 'request_contact': True}]],
        'one_time_keyboard': True,
        'resize_keyboard': True
    }

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': "👇 Ro'yxatdan o'tish uchun quyidagi tugmani bosing va telefon raqamingizni ulashing:",
        'reply_markup': reply_markup
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Xatolik: {e}")
        return None


def get_updates(offset=None):
    """Telegramdan yangi xabarlarni olish"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset

    try:
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        if data.get('ok'):
            return data.get('result', [])
        else:
            print(f"GetUpdates xatolik: {data}")
            return []
    except Exception as e:
        print(f"Get updates xatolik: {e}")
        return []


def process_message(message):
    """Xabarni qayta ishlash"""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    contact = message.get('contact', None)

    print(f"📩 Xabar keldi: chat_id={chat_id}, text={text}")

    # /start buyrug'i
    if text == '/start':
        welcome_message = """
<b>🤖 SavdoHub Botiga xush kelibsiz!</b>

Ro'yxatdan o'tish uchun quyidagi tugmani bosing va telefon raqamingizni ulashing.

👇 <b>Telefon raqamni ulashish</b> tugmasini bosing
        """
        send_contact_button(chat_id)
        return

    # Kontakt ulashilganda
    if contact:
        phone_number = contact.get('phone_number')
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number

        print(f"📞 Kontakt olindi: {phone_number}")

        # Foydalanuvchini topish yoki yaratish
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'is_active': False}
        )

        # Eski OTP larni o'chirish
        OTP.objects.filter(user=user, created_at__lt=timezone.now() - timezone.timedelta(minutes=5)).delete()

        # Yangi OTP kod yaratish
        otp_code = generate_otp()

        # OTP ni bazaga saqlash
        OTP.objects.create(
            user=user,
            code=otp_code,
            telegram_chat_id=str(chat_id)
        )

        print(f"🔐 OTP kodi yaratildi: {phone_number} -> {otp_code}")

        # Kodni yuborish
        message_text = f"""
<b>🔐 SavdoHub - Tasdiqlash kodi</b>

Sizning tasdiqlash kodingiz: <b>{otp_code}</b>

⏰ Kod 5 daqiqa amal qiladi
🔒 Bu kodni hech kim bilan baham ko'rmang

Kodni saytga kiriting va ro'yxatdan o'tishni davom ettiring.
        """
        send_telegram_message(chat_id, message_text)
        return


def start_bot():
    """Botni ishga tushirish"""
    print("🚀 Telegram bot ishga tushmoqda...")
    print(f"📌 Bot username: @{settings.TELEGRAM_BOT_USERNAME}")
    print(f"📌 Bot token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")

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
            print(f"Bot xatolik: {e}")
            time.sleep(5)


def run_bot_async():
    """Botni alohida threadda ishga tushirish"""
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    return bot_thread