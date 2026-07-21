from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order


@receiver(post_save, sender=Order)
def order_status_changed_notification(sender, instance, created, **kwargs):
    """Buyurtma holati o'zgarganda xabarnoma yuborish"""
    if not created:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            if old_order.status != instance.status:
                # Importni funksiya ichida qilish - cycli importni oldini olish
                from bot.bot import send_telegram_message
                from .models import TelegramUser

                status_data = {
                    'pending': ('⏳ Kutilmoqda', 'Buyurtmangiz qabul qilindi va tekshirilmoqda.'),
                    'confirmed': ('✅ Tasdiqlandi', 'Buyurtmangiz tasdiqlandi. Tez orada yetkazib beriladi.'),
                    'shipped': ('🚚 Yuborildi', 'Buyurtmangiz yetkazib berishga topshirildi.'),
                    'delivered': (
                    '📦 Yetkazildi', 'Buyurtmangiz manzilingizga yetkazildi! Mahsulotni baholashni unutmang.'),
                    'cancelled': ('❌ Bekor qilindi', 'Buyurtmangiz bekor qilindi.')
                }

                status_text, description = status_data.get(instance.status, ('Holat o\'zgardi', ''))

                telegram_user = TelegramUser.objects.filter(user=instance.user, is_active=True).first()
                if telegram_user and telegram_user.chat_id:
                    message = f"""
<b>{status_text}</b>

🆔 Buyurtma raqami: <b>#{instance.id}</b>
📦 {description}

<a href="http://127.0.0.1:8000/my-orders/">🔗 Buyurtmalarim sahifasiga o'tish</a>
                    """
                    send_telegram_message(telegram_user.chat_id, message)
                    print(f"✅ Xabar yuborildi: {instance.user.phone_number} - {instance.status}")
        except Order.DoesNotExist:
            pass
        except Exception as e:
            print(f"Xabar yuborish xatolik: {e}")