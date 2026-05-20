import requests
from django.conf import settings
from django.core.cache import cache

def send_telegram_message(chat_id, message):
    """Telegram bot orqali xabar yuborish"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        return result.get('ok', False)
    except Exception as e:
        print(f"Telegram xatolik: {e}")
        return False

def send_otp_via_telegram(chat_id, otp_code):
    """OTP kodni Telegram orqali yuborish"""
    message = f"""
<b>🔐 SavdoHub - Tasdiqlash kodi</b>

Hurmatli foydalanuvchi!

Sizning tasdiqlash kodingiz: <b>{otp_code}</b>

⏰ Kod 5 daqiqa amal qiladi
🔒 Bu kodni hech kim bilan baham ko'rmang

Agar bu so'rovni siz yubormagan bo'lsangiz, xabarni e'tiborsiz qoldiring.

---
© SavdoHub | Mega Textil MCHJ
    """
    return send_telegram_message(chat_id, message)

def test_bot_connection():
    """Botning ishlayotganligini tekshirish"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        return response.json().get('ok', False)
    except Exception as e:
        print(f"Test xatolik: {e}")
        return False

def get_otp_from_cache(chat_id):
    """Cache dan OTP kodni olish"""
    data = cache.get(f'telegram_otp_{chat_id}')
    if data:
        return data.get('otp_code'), data.get('phone_number')
    return None, None

def check_telegram_otp(chat_id, otp_code):
    """Telegram OTP kodni tekshirish"""
    data = cache.get(f'telegram_otp_{chat_id}')
    if data and data.get('otp_code') == otp_code:
        # Kod to'g'ri, cache dan o'chirish
        cache.delete(f'telegram_otp_{chat_id}')
        return True, data.get('phone_number')
    return False, None