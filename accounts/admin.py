from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, OTP


class CustomUserAdmin(UserAdmin):
    """Foydalanuvchi admin panel sozlamalari"""

    # Ro'yxatda ko'rinadigan maydonlar
    list_display = ('phone_number', 'full_name', 'is_active', 'is_staff', 'date_joined', 'get_orders_count')

    # Filtrlar
    list_filter = ('is_active', 'is_staff', 'date_joined')

    # Qidiruv maydonlari
    search_fields = ('phone_number', 'full_name')

    # Tartiblash
    ordering = ('-date_joined',)

    # Har bir qatordagi harakatlar
    actions = ['activate_users', 'deactivate_users']

    # Maydonlar guruhi
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Shaxsiy ma\'lumotlar'), {'fields': ('full_name',)}),
        (_('Ruxsatlar'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Muhim sanalar'), {'fields': ('last_login', 'date_joined')}),
    )

    # Yangi foydalanuvchi qo'shish formasi
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'full_name', 'is_active', 'is_staff'),
        }),
    )

    def get_orders_count(self, obj):
        """Foydalanuvchining buyurtmalar soni"""
        return obj.orders.count()

    get_orders_count.short_description = 'Buyurtmalar soni'
    get_orders_count.admin_order_field = 'orders__count'

    def activate_users(self, request, queryset):
        """Tanlangan foydalanuvchilarni faollashtirish"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} ta foydalanuvchi faollashtirildi.')

    activate_users.short_description = "Tanlangan foydalanuvchilarni faollashtirish"

    def deactivate_users(self, request, queryset):
        """Tanlangan foydalanuvchilarni bloklash"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} ta foydalanuvchi bloklandi.')

    deactivate_users.short_description = "Tanlangan foydalanuvchilarni bloklash"


class OTPAdmin(admin.ModelAdmin):
    """OTP kodlar admin panel sozlamalari"""

    list_display = ('id', 'user', 'code', 'created_at', 'is_used')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__phone_number', 'code')
    readonly_fields = ('user', 'code', 'created_at', 'is_used')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Admin panelga ro'yxatdan o'tkazish
admin.site.register(User, CustomUserAdmin)
admin.site.register(OTP, OTPAdmin)