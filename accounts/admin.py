from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, OTP


class CustomUserAdmin(UserAdmin):
    """Foydalanuvchi admin panel sozlamalari"""

    list_display = ('phone_number', 'full_name', 'is_active', 'is_staff', 'date_joined', 'get_orders_count')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('phone_number', 'full_name')
    ordering = ('-date_joined',)
    actions = ['activate_users', 'deactivate_users']

    # fieldsets - date_joined ni readonly qilib qo'shing
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Shaxsiy ma\'lumotlar'), {'fields': ('full_name',)}),
        (_('Ruxsatlar'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Muhim sanalar'), {'fields': ('last_login',)}),  # date_joined ni olib tashlang
    )

    # date_joined ni readonly qilish
    readonly_fields = ('last_login', 'date_joined')

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
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} ta foydalanuvchi faollashtirildi.')

    activate_users.short_description = "Tanlangan foydalanuvchilarni faollashtirish"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} ta foydalanuvchi bloklandi.')

    deactivate_users.short_description = "Tanlangan foydalanuvchilarni bloklash"


class OTPAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'created_at', 'is_used')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__phone_number', 'code')
    readonly_fields = ('user', 'code', 'created_at', 'is_used')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(User, CustomUserAdmin)
admin.site.register(OTP, OTPAdmin)