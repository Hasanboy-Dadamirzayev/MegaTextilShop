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
    stock = models.IntegerField(default=0)
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
    """Savatdagi mahsulotlar"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Savat")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items', verbose_name="Mahsulot")
    quantity = models.IntegerField(default=1, verbose_name="Soni")

    class Meta:
        verbose_name = "Savatdagi mahsulot"
        verbose_name_plural = "Savatdagi mahsulotlar"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity


class Wishlist(models.Model):
    """Yoqtirilgan mahsulotlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists', verbose_name="Foydalanuvchi")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlists', verbose_name="Mahsulot")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqt")

    class Meta:
        verbose_name = "Yoqtirilgan mahsulot"
        verbose_name_plural = "Yoqtirilgan mahsulotlar"
        unique_together = ['user', 'product']  # Bir foydalanuvchi bir mahsulotni bir marta yoqtirishi mumkin

    def __str__(self):
        return f"{self.user.phone_number} - {self.product.name}"


class Order(models.Model):
    """Buyurtma"""
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('shipped', 'Yuborilgan'),
        ('delivered', 'Yetkazilgan'),
        ('cancelled', 'Bekor qilingan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name="Foydalanuvchi")
    full_name = models.CharField(max_length=200, verbose_name="To'liq ism")
    address = models.TextField(verbose_name="Manzil")
    phone = models.CharField(max_length=20, verbose_name="Telefon")
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Umumiy summa")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holat")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.user.phone_number}"

    @property
    def status_badge_color(self):
        colors = {
            'pending': 'warning',
            'confirmed': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')


class OrderItem(models.Model):
    """Buyurtmadagi mahsulotlar"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Buyurtma")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    quantity = models.IntegerField(verbose_name="Soni")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Narx")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity


# shop/models.py ga qo'shing (SessionCart modeli)

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
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity