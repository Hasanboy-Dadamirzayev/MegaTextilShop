from django.contrib import admin
from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .models import Coupon, UserCoupon

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_available', 'is_featured', 'is_new']
    list_filter = ['category', 'is_available', 'is_featured', 'is_new']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock', 'is_available', 'is_featured', 'is_new']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'phone', 'user__phone_number']
    list_editable = ['status']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_items', 'total_price', 'created_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'total_price']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']


from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'comment', 'created_at', 'is_approved']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__phone_number', 'comment']
    list_editable = ['is_approved']
    readonly_fields = ['created_at', 'updated_at']


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