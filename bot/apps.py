from django.apps import AppConfig
import os


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'

    def ready(self):
        """Django ishga tushganda botni ishga tushirish"""
        # Faqat asosiy threadda va runserver da ishga tushsin
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            import threading
            import time

            def start_bot_delayed():
                time.sleep(2)  # Django to'liq ishga tushguncha kutish
                try:
                    from .bot import run_bot_async
                    run_bot_async()
                except Exception as e:
                    print(f"Bot ishga tushmadi: {e}")

            thread = threading.Thread(target=start_bot_delayed, daemon=True)
            thread.start()