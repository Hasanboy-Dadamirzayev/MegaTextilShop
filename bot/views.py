import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
import requests
import random


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def send_telegram_message(chat_id, text, reply_markup=None):
    """Telegramga xabar yuborish"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Xatolik: {e}")
        return None


@csrf_exempt
def webhook(request):
    """Telegram webhook - xabarlarni qabul qilish"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Callback query (tugma bosilganda)
            if 'callback_query' in data:
                callback = data['callback_query']
                message = callback.get('message', {})
                chat_id = message.get('chat', {}).get('id')
                data_callback = callback.get('data', '')

                if data_callback.startswith('register_'):
                    token = data_callback.replace('register_', '')

                    # Kontakt ulashish tugmasi
                    reply_markup = {
                        'keyboard': [[{'text': '📱 Kontakt ulashish', 'request_contact': True}]],
                        'one_time_keyboard': True,
                        'resize_keyboard': True
                    }

                    message_text = f"""
<b>🤖 SavdoHub Bot</b>

Assalomu alaykum! Ro'yxatdan o'tish uchun quyidagi tugmani bosing va telefoningizni ulashing.

📱 <b>Telefon raqamingizni ulashganingizdan so'ng</b>, sizga tasdiqlash kodi yuboriladi.

<a href="http://127.0.0.1:8000/accounts/verify-telegram-code/{token}/">✅ Saytga qaytish</a>
                    """
                    send_telegram_message(chat_id, message_text, reply_markup)

                return JsonResponse({'ok': True})

            # Oddiy xabar
            if 'message' in data:
                message = data['message']
                chat_id = message.get('chat', {}).get('id')
                text = message.get('text', '')
                contact = message.get('contact', None)

                # /start buyrug'i
                if text == '/start':
                    # Inline tugma yaratish
                    reply_markup = {
                        'inline_keyboard': [
                            [{'text': '✅ Ro\'yxatdan o\'tishni boshlash', 'callback_data': 'register_temp'}]
                        ]
                    }
                    welcome_message = """
<b>🤖 SavdoHub Botiga xush kelibsiz!</b>

Bu bot orqali Mega Textil online do'konida ro'yxatdan o'tishingiz mumkin.

👇 Ro'yxatdan o'tishni boshlash uchun tugmani bosing
                    """
                    send_telegram_message(chat_id, welcome_message, reply_markup)
                    return JsonResponse({'ok': True})

                # Kontakt ulashilganda
                if contact:
                    phone_number = contact.get('phone_number')
                    if not phone_number.startswith('+'):
                        phone_number = '+' + phone_number

                    # OTP kod yaratish
                    otp_code = generate_otp()

                    # Kodni cache ga saqlash (vaqtincha, token bilan)
                    # Foydalanuvchi hali tokeni yo'q, shuning uchun chat_id bilan saqlaymiz
                    cache.set(f'telegram_otp_chat_{chat_id}', {
                        'otp_code': otp_code,
                        'phone_number': phone_number
                    }, timeout=300)

                    # Kodni yuborish
                    message_text = f"""
<b>🔐 SavdoHub - Tasdiqlash kodi</b>

Sizning tasdiqlash kodingiz: <b>{otp_code}</b>

⏰ Kod 5 daqiqa amal qiladi
🔒 Bu kodni hech kim bilan baham ko'rmang

Kodni saytga kiriting va ro'yxatdan o'tishni davom ettiring.
                    """
                    send_telegram_message(chat_id, message_text)

                    return JsonResponse({'ok': True})

            return JsonResponse({'ok': True})

        except Exception as e:
            print(f"Webhook xatolik: {e}")
            return JsonResponse({'ok': False, 'error': str(e)})

    return JsonResponse({'ok': False, 'error': 'Method not allowed'})