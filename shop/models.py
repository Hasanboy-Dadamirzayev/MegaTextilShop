from django.db import models
from django.urls import reverse
from accounts.models import User


class Category(models.Model):
    """Mahsulot kategoriyalari"""
    name = models.CharField(max_length=100, verbose_name="Kategoriya nomi")
    slug = models.SlugField(unique=True, verbose_name="URL manzil")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Rasm")
    order = models.IntegerField(default=0, verbose_name="Tartib")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:category_products', args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='products/')
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.category.slug, self.slug])

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0

    @property
    def has_discount(self):
        return self.old_price is not None and self.old_price > self.price

    @property
    def total_stock(self):
        """Barcha variantlardagi umumiy son"""
        return sum(variant.stock for variant in self.variants.all())

    def get_available_colors(self):
        """Mavjud ranglarni qaytarish (stock > 0 bo'lgan)"""
        return self.variants.filter(stock__gt=0).values_list('color', flat=True).distinct()

    def get_available_sizes(self, color=None):
        """Berilgan rang uchun mavjud o'lchamlarni qaytarish"""
        variants = self.variants.filter(stock__gt=0)
        if color:
            variants = variants.filter(color=color)
        return variants.values_list('size', flat=True).distinct()

    def get_variant_stock(self, color, size):
        """Berilgan rang va o'lchamdagi sonni qaytarish"""
        variant = self.variants.filter(color=color, size=size).first()
        return variant.stock if variant else 0


class ProductVariant(models.Model):
    """Mahsulot varianti (rang + o'lcham kombinatsiyasi)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=50, verbose_name="Rang")
    size = models.CharField(max_length=20, verbose_name="O'lcham")
    stock = models.IntegerField(default=0, verbose_name="Soni")
    sku = models.CharField(max_length=100, blank=True, verbose_name="SKU")
    price_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Qo'shimcha narx")

    class Meta:
        verbose_name = "Mahsulot varianti"
        verbose_name_plural = "Mahsulot variantlari"
        # unique_together ni vaqtincha o'chirib qo'ying
        # unique_together = ['product', 'color', 'size']

    def __str__(self):
        return f"{self.product.name} - {self.color} / {self.size} ({self.stock} dona)"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{self.product.id}-{self.color[:3]}-{self.size}"
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Savat"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', verbose_name="Foydalanuvchi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Savat"
        verbose_name_plural = "Savatlar"

    def __str__(self):
        return f"{self.user.phone_number} - Savat"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    """Savatdagi mahsulotlar - o'lcham va rang bilan"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Savat")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items', verbose_name="Mahsulot")
    size = models.CharField(max_length=20, blank=True, null=True, verbose_name="O'lcham")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Rang")
    quantity = models.IntegerField(default=1, verbose_name="Soni")

    class Meta:
        verbose_name = "Savatdagi mahsulot"
        verbose_name_plural = "Savatdagi mahsulotlar"
        unique_together = ['cart', 'product', 'size', 'color']

    def __str__(self):
        parts = [self.product.name]
        if self.size:
            parts.append(f"({self.size})")
        if self.color:
            parts.append(f"[{self.color}]")
        parts.append(f"x {self.quantity}")
        return " ".join(parts)

    @property
    def total_price(self):
        return self.product.price * self.quantity


class Review(models.Model):
    """Mahsulotga baho va sharh"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(1, '1 ★'), (2, '2 ★'), (3, '3 ★'), (4, '4 ★'), (5, '5 ★')])
    comment = models.TextField(verbose_name="Sharh")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True, verbose_name="Tasdiqlangan")

    # Yangi maydonlar - javob uchun
    admin_reply = models.TextField(blank=True, null=True, verbose_name="Admin javobi")
    admin_reply_at = models.DateTimeField(blank=True, null=True, verbose_name="Javob vaqti")
    is_replied = models.BooleanField(default=False, verbose_name="Javob berilgan")

    class Meta:
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"
        ordering = ['-created_at']
        unique_together = ['product', 'user']

    def __str__(self):
        return f"{self.user.phone_number} - {self.product.name} - {self.rating}★"


class Coupon(models.Model):
    """Chegirma kuponlari"""
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Foizli chegirma (%)'),
        ('fixed', 'Belgilangan summa (so\'m)'),
        ('free_shipping', 'Bepul yetkazib berish'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Kupon kodi")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percent',
                                     verbose_name="Chegirma turi")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Chegirma qiymati")

    valid_from = models.DateTimeField(verbose_name="Amal qilish boshlanishi")
    valid_to = models.DateTimeField(verbose_name="Amal qilish tugashi")

    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           verbose_name="Minimal buyurtma summasi")
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                              verbose_name="Maksimal chegirma summasi")
    usage_limit = models.IntegerField(default=1, verbose_name="Ishlatilish chegarasi")
    used_count = models.IntegerField(default=0, verbose_name="Ishlatilgan soni")
    users = models.ManyToManyField(User, blank=True, verbose_name="Foydalanuvchilar")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kupon"
        verbose_name_plural = "Kuponlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()}"

    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (self.is_active and
                self.valid_from <= now <= self.valid_to and
                (self.usage_limit > self.used_count))

    def calculate_discount(self, cart_total):
        if not self.is_valid:
            return 0
        if cart_total < self.min_order_amount:
            return 0
        if self.discount_type == 'percent':
            discount = cart_total * self.discount_value / 100
        elif self.discount_type == 'fixed':
            discount = self.discount_value
        else:
            discount = 0
        if self.max_discount_amount and discount > self.max_discount_amount:
            discount = self.max_discount_amount
        return discount


class UserCoupon(models.Model):
    """Foydalanuvchi ishlatgan kuponlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_coupons')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'coupon']

    def __str__(self):
        return f"{self.user.phone_number} - {self.coupon.code}"


class TelegramUser(models.Model):
    """Telegram foydalanuvchilari - chat_id avtomatik saqlanadi"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram_user')
    chat_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram foydalanuvchi"
        verbose_name_plural = "Telegram foydalanuvchilar"

    def __str__(self):
        return f"{self.user.phone_number} - {self.chat_id}"

class Wishlist(models.Model):
    """Yoqtirilgan mahsulotlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists', verbose_name="Foydalanuvchi")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlists', verbose_name="Mahsulot")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqt")

    class Meta:
        verbose_name = "Yoqtirilgan mahsulot"
        verbose_name_plural = "Yoqtirilgan mahsulotlar"
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.phone_number} - {self.product.name}"


from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('shipped', 'Yuborilgan'),
        ('delivered', 'Yetkazilgan'),
        ('cancelled', 'Bekor qilingan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    full_name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.user.phone_number}"

    @property
    def is_delivered(self):
        return self.status == 'delivered'


# SIGNAL: Buyurtma holati 'delivered' ga o'zgarganda avtomatik can_review ni True qilish
@receiver(pre_save, sender=Order)
def enable_review_on_delivered(sender, instance, **kwargs):
    """Buyurtma holati 'delivered' ga o'zgarganda, order_item can_review ni True qilish"""
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            # Agar holat 'delivered' ga o'zgarayotgan bo'lsa
            if old_order.status != 'delivered' and instance.status == 'delivered':
                # Signal keyin ishlashi uchun post_save da ishlaymiz
                pass
        except Order.DoesNotExist:
            pass


@receiver(post_save, sender=Order)
def enable_review_on_delivered_post(sender, instance, created, **kwargs):
    """Buyurtma saqlangandan keyin, agar holat 'delivered' bo'lsa, can_review ni True qilish"""
    if instance.status == 'delivered':
        # Buyurtmadagi barcha mahsulotlar uchun can_review ni True qilish
        updated_count = instance.items.filter(can_review=False).update(
            can_review=True,
            reviewed_at=None
        )
        if updated_count > 0:
            print(f"✅ Buyurtma #{instance.id} yetkazilgan: {updated_count} ta mahsulot uchun sharh yozish ochildi")




class OrderItem(models.Model):
    """Buyurtmadagi mahsulotlar - o'lcham va rang bilan"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    can_review = models.BooleanField(default=False)  # BU MAYDonNI QO'SHING
    reviewed_at = models.DateTimeField(blank=True, null=True)  # BU MAYDonNI QO'SHING

    def __str__(self):
        parts = [self.product.name]
        if self.size:
            parts.append(f"({self.size})")
        if self.color:
            parts.append(f"[{self.color}]")
        parts.append(f"x {self.quantity}")
        return " ".join(parts)


    @property
    def total_price(self):
        return self.price * self.quantity


class SessionCart(models.Model):
    session_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session: {self.session_key}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class SessionCartItem(models.Model):
    session_cart = models.ForeignKey(SessionCart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, blank=True, null=True, verbose_name="O'lcham")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Rang")
    quantity = models.IntegerField(default=1)

    def __str__(self):
        parts = [self.product.name]
        if self.size:
            parts.append(f"({self.size})")
        if self.color:
            parts.append(f"[{self.color}]")
        parts.append(f"x {self.quantity}")
        return " ".join(parts)

    @property
    def total_price(self):
        return self.product.price * self.quantity