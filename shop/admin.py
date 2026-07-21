from django.contrib import admin
from django.utils import timezone
from .models import (
    Category, Product, ProductVariant, Review, Coupon, UserCoupon,
    Wishlist, Order, OrderItem, Cart, CartItem, TelegramUser
)


class ProductVariantInline(admin.TabularInline):
    """Mahsulot variantlari (rang + o'lcham)"""
    model = ProductVariant
    extra = 3
    fields = ['color', 'size', 'stock', 'sku', 'price_extra']
    show_change_link = True


class OrderItemInline(admin.TabularInline):
    """Buyurtma mahsulotlari"""
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'size', 'color', 'quantity', 'price', 'can_review']
    can_delete = False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_editable = ['order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'total_stock', 'is_available', 'is_featured', 'is_new']
    list_filter = ['category', 'is_available', 'is_featured', 'is_new']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'is_available', 'is_featured', 'is_new']
    inlines = [ProductVariantInline]

    def total_stock(self, obj):
        return obj.total_stock

    total_stock.short_description = 'Umumiy son'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'color', 'size', 'stock', 'sku']
    list_filter = ['product', 'color', 'size']
    search_fields = ['product__name', 'color', 'size', 'sku']
    list_editable = ['stock']
    list_select_related = ['product']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'comment_preview', 'is_approved', 'is_replied', 'created_at']
    list_filter = ['rating', 'is_approved', 'is_replied', 'created_at']
    search_fields = ['product__name', 'user__phone_number', 'comment', 'admin_reply']
    list_editable = ['is_approved']
    readonly_fields = ['created_at', 'updated_at', 'admin_reply_at']

    fieldsets = (
        ('Sharh ma\'lumotlari', {
            'fields': ('product', 'user', 'rating', 'comment', 'is_approved')
        }),
        ('Admin javobi', {
            'fields': ('admin_reply', 'admin_reply_at', 'is_replied'),
            'classes': ('wide',),
        }),
        ('Vaqt ma\'lumotlari', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment

    comment_preview.short_description = 'Sharh'

    def save_model(self, request, obj, form, change):
        if obj.admin_reply and not obj.admin_reply_at:
            obj.admin_reply_at = timezone.now()
            obj.is_replied = True
        elif not obj.admin_reply:
            obj.admin_reply_at = None
            obj.is_replied = False
        super().save_model(request, obj, form, change)

    actions = ['approve_reviews', 'reject_reviews', 'mark_as_replied']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} ta sharh tasdiqlandi.")

    approve_reviews.short_description = "Tanlangan sharhlarni tasdiqlash"

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} ta sharh rad etildi.")

    reject_reviews.short_description = "Tanlangan sharhlarni rad etish"

    def mark_as_replied(self, request, queryset):
        queryset.update(is_replied=True, admin_reply_at=timezone.now())
        self.message_user(request, f"{queryset.count()} ta sharhga javob berilgan deb belgilandi.")

    mark_as_replied.short_description = "Javob berilgan deb belgilash"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active', 'used_count',
                    'usage_limit']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code']
    list_editable = ['is_active']
    fieldsets = (
        ('Kupon ma\'lumotlari', {
            'fields': ('code', 'discount_type', 'discount_value', 'is_active')
        }),
        ('Amal qilish vaqti', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Cheklovlar', {
            'fields': ('min_order_amount', 'max_discount_amount', 'usage_limit', 'users')
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.code = obj.code.upper()
        super().save_model(request, obj, form, change)


@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    list_display = ['user', 'coupon', 'used_at', 'order']
    list_filter = ['used_at']
    search_fields = ['user__phone_number', 'coupon__code']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__phone_number', 'product__name']


from django.contrib import admin
from django.utils import timezone
from .models import Order, OrderItem, TelegramUser, TelegramUser


class OrderItemInline(admin.TabularInline):
    """Buyurtma mahsulotlari"""
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'size', 'color', 'quantity', 'price', 'can_review']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'phone', 'user__phone_number']
    list_editable = ['status']
    readonly_fields = ['created_at']
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            try:
                old_obj = Order.objects.get(pk=obj.pk)
                old_status = old_obj.status
            except Order.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        # Holat o'zgarganda xabar yuborish
        if old_status and old_status != obj.status:
            try:
                # Importni funksiya ichida qilish - cycli importni oldini olish
                from bot.bot import send_telegram_message
                from .models import TelegramUser

                # O'zbekiston vaqtini olish
                uzb_time = timezone.localtime(timezone.now())
                formatted_time = uzb_time.strftime('%d.%m.%Y %H:%M')

                status_data = {
                    'pending': ('⏳ Kutilmoqda', 'Buyurtmangiz qabul qilindi va tekshirilmoqda.'),
                    'confirmed': ('✅ Tasdiqlandi', 'Buyurtmangiz tasdiqlandi. Tez orada yetkazib beriladi.'),
                    'shipped': ('🚚 Yuborildi', 'Buyurtmangiz yetkazib berishga topshirildi.'),
                    'delivered': (
                    '📦 Yetkazildi', 'Buyurtmangiz manzilingizga yetkazildi! Mahsulotni baholashni unutmang.'),
                    'cancelled': ('❌ Bekor qilindi', 'Buyurtmangiz bekor qilindi.')
                }

                status_text, description = status_data.get(obj.status, ('Holat o\'zgardi', ''))

                telegram_user = TelegramUser.objects.filter(user=obj.user, is_active=True).first()
                if telegram_user and telegram_user.chat_id:
                    message = f"""
<b>{status_text}</b>

🆔 Buyurtma raqami: <b>#{obj.id}</b>
📦 {description}
📅 Sana: {formatted_time}

<a href="http://127.0.0.1:8000/my-orders/">🔗 Buyurtmalarim sahifasiga o'tish</a>
                    """
                    send_telegram_message(telegram_user.chat_id, message)
                    print(f"✅ Xabar yuborildi: {obj.user.phone_number} - {obj.status}")
            except Exception as e:
                print(f"Xabar yuborish xatolik: {e}")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'size', 'color', 'quantity', 'price', 'can_review', 'reviewed_at']
    list_filter = ['can_review', 'order__status']
    search_fields = ['product__name', 'order__id']
    readonly_fields = ['can_review', 'reviewed_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_items', 'total_price', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'size', 'color', 'quantity', 'total_price']
    search_fields = ['product__name']


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'chat_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__phone_number', 'chat_id']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']