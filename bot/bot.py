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
from shop.models import TelegramUser, Order


def get_current_time():
    """O'zbekiston vaqtini qaytarish"""
    return timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def send_telegram_message(chat_id, text):
    """Telegramga xabar yuborish"""
    if not chat_id:
        return None

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
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
        'text': "👇 Xabarnoma olish uchun telefon raqamingizni ulashing:",
        'reply_markup': reply_markup
    }
    try:
        return requests.post(url, json=payload, timeout=10).json()
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
    """Xabarni qayta ishlash - chat_id ni avtomatik saqlash"""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    contact = message.get('contact', None)

    print(f"📩 Xabar keldi: chat_id={chat_id}, text={text}")

    # /start buyrug'i
    if text == '/start':
        welcome_message = """
<b>🤖 SavdoHub Botiga xush kelibsiz!</b>

📢 <b>Xabarnoma olish uchun:</b>
1. Quyidagi tugmani bosing
2. Telefon raqamingizni ulashing
3. Buyurtma holati haqida xabar olishni boshlang

👇 <b>"Telefon raqamni ulashish"</b> tugmasini bosing
        """
        send_telegram_message(chat_id, welcome_message)
        send_contact_button(chat_id)
        return

    # Kontakt ulashilganda - chat_id ni foydalanuvchiga bog'lash
    if contact:
        phone_number = contact.get('phone_number')
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number

        print(f"📞 Kontakt olindi: {phone_number}, chat_id: {chat_id}")

        try:
            user = User.objects.get(phone_number=phone_number)

            telegram_user, created = TelegramUser.objects.get_or_create(
                user=user,
                defaults={'chat_id': str(chat_id), 'is_active': True}
            )

            if not created:
                telegram_user.chat_id = str(chat_id)
                telegram_user.is_active = True
                telegram_user.save()

            print(f"✅ Chat ID saqlandi: {user.phone_number} -> {chat_id}")

            success_message = f"""
<b>✅ Xabarnoma muvaffaqiyatli sozlandi!</b>

👤 Foydalanuvchi: {user.phone_number}
📢 Endi sizga buyurtma holati haqida xabarlar keladi!
            """
            send_telegram_message(chat_id, success_message)

            if not user.is_active:
                OTP.objects.filter(user=user, created_at__lt=timezone.now() - timezone.timedelta(minutes=5)).delete()
                otp_code = generate_otp()
                OTP.objects.create(user=user, code=otp_code, telegram_chat_id=str(chat_id))
                send_telegram_message(chat_id, f"🔐 Tasdiqlash kodingiz: {otp_code}")

        except User.DoesNotExist:
            error_message = """
❌ <b>Foydalanuvchi topilmadi!</b>

Iltimos, avval saytda ro'yxatdan o'ting:
<a href="http://127.0.0.1:8000/accounts/register/">📝 Ro'yxatdan o'tish</a>

Ro'yxatdan o'tgandan keyin qaytib /start bosing.
            """
            send_telegram_message(chat_id, error_message)

        return


# ========== XABARNOMA YUBORISH FUNKSIYALARI ==========

def send_notification_to_user(user, title, message, link=None):
    """Foydalanuvchiga Telegram xabarnoma yuborish"""
    try:
        telegram_user = TelegramUser.objects.filter(user=user, is_active=True).first()
        if telegram_user and telegram_user.chat_id:
            # O'zbekiston vaqtini olish
            current_time = get_current_time()

            full_message = f"""
<b>{title}</b>

{message}

📅 Sana: {current_time}
            """
            if link:
                full_message += f"\n\n<a href=\"{link}\">🔗 Batafsil ma'lumot</a>"

            return send_telegram_message(telegram_user.chat_id, full_message)
    except Exception as e:
        print(f"Xabarnoma yuborish xatolik: {e}")
    return None


def send_order_notification(order):
    """Buyurtma holati o'zgarganida xabarnoma"""
    status_data = {
        'pending': {
            'emoji': '⏳',
            'title': 'Buyurtma qabul qilindi',
            'message': f"Buyurtmangiz #{order.id} qabul qilindi va tekshirilmoqda."
        },
        'confirmed': {
            'emoji': '✅',
            'title': 'Buyurtma tasdiqlandi',
            'message': f"Buyurtmangiz #{order.id} tasdiqlandi. Tez orada yetkazib beriladi."
        },
        'shipped': {
            'emoji': '🚚',
            'title': 'Buyurtma yuborildi',
            'message': f"Buyurtmangiz #{order.id} yetkazib berishga topshirildi."
        },
        'delivered': {
            'emoji': '📦',
            'title': 'Buyurtma yetkazildi!',
            'message': f"Buyurtmangiz #{order.id} manzilingizga yetkazildi. Mahsulotni baholashni unutmang!"
        },
        'cancelled': {
            'emoji': '❌',
            'title': 'Buyurtma bekor qilindi',
            'message': f"Buyurtmangiz #{order.id} bekor qilindi."
        }
    }

    data = status_data.get(order.status, {
        'emoji': '🔄',
        'title': 'Buyurtma holati o\'zgardi',
        'message': f"Buyurtmangiz #{order.id} holati: {order.get_status_display()}"
    })

    return send_notification_to_user(
        order.user,
        f"{data['emoji']} {data['title']}",
        data['message'],
        "/my-orders/"
    )


def start_bot():
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


if __name__ == '__main__':
    start_bot()