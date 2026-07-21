from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = 'shop'



from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        import shop.signals  # signals faylini import qilish