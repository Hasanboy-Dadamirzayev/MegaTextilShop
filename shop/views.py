import json
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import models
from django.conf import settings
from .forms import OrderForm, ReviewForm
from .models import Category, Product, ProductVariant, Cart, CartItem, Order, OrderItem, SessionCart, SessionCartItem, Wishlist, Review, Coupon, UserCoupon


def get_or_create_session_cart(request):
    """Session orqali savatni olish yoki yaratish"""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    session_cart, created = SessionCart.objects.get_or_create(session_key=session_key)
    return session_cart


def merge_session_cart_to_user_cart(request, user):
    """Foydalanuvchi login qilganda session savatni user savatiga qo'shish"""
    session_key = request.session.session_key
    if session_key:
        try:
            session_cart = SessionCart.objects.get(session_key=session_key)
            user_cart, created = Cart.objects.get_or_create(user=user)

            for session_item in session_cart.items.all():
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=session_item.product,
                    defaults={'quantity': session_item.quantity}
                )
                if not created:
                    cart_item.quantity += session_item.quantity
                    cart_item.save()

            session_cart.items.all().delete()
            session_cart.delete()

        except SessionCart.DoesNotExist:
            pass


def get_cart_total_items(request):
    """Savatdagi mahsulotlar sonini qaytarish"""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        return cart.total_items if cart else 0
    else:
        session_cart = get_or_create_session_cart(request)
        return session_cart.total_items


def get_wishlist_count(request):
    """Yoqtirilgan mahsulotlar sonini qaytarish"""
    if request.user.is_authenticated:
        return Wishlist.objects.filter(user=request.user).count()
    return 0


def wishlist_add_view(request):
    """Mahsulotni yoqtirilganlarga qo'shish - AJAX"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Yoqtirilgan mahsulotlarga qo\'shish uchun tizimga kiring!',
            'redirect': 'accounts:login'
        })

    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')

        product = get_object_or_404(Product, id=product_id, is_available=True)

        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if created:
            message = f'{product.name} yoqtirilganlarga qo\'shildi'
            is_added = True
        else:
            wishlist_item.delete()
            message = f'{product.name} yoqtirilganlardan o\'chirildi'
            is_added = False

        total_wishlist = Wishlist.objects.filter(user=request.user).count()

        return JsonResponse({
            'success': True,
            'message': message,
            'is_added': is_added,
            'total_wishlist': total_wishlist
        })

    return JsonResponse({'success': False, 'message': 'Xatolik yuz berdi'})


def wishlist_view(request):
    """Yoqtirilgan mahsulotlar sahifasi"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Yoqtirilgan mahsulotlaringizni ko\'rish uchun tizimga kiring!')
        return redirect('accounts:login')

    wishlist_items = Wishlist.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'wishlist_items': wishlist_items,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/wishlist.html', context)


def wishlist_remove_view(request, product_id):
    """Yoqtirilgan mahsulotni o'chirish"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    wishlist_item = get_object_or_404(Wishlist, user=request.user, product_id=product_id)
    wishlist_item.delete()
    messages.success(request, 'Mahsulot yoqtirilganlardan o\'chirildi')
    return redirect('shop:wishlist')


def get_wishlist_status(request):
    """Mahsulotning yoqtirilganlar ro'yxatida borligini tekshirish (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'is_wishlisted': False})

    product_id = request.GET.get('product_id')
    if product_id:
        is_wishlisted = Wishlist.objects.filter(user=request.user, product_id=product_id).exists()
        return JsonResponse({'success': True, 'is_wishlisted': is_wishlisted})

    return JsonResponse({'success': False, 'is_wishlisted': False})


def index_view(request):
    """Bosh sahifa"""
    featured_products = Product.objects.filter(is_available=True, is_featured=True)[:8]
    new_products = Product.objects.filter(is_available=True, is_new=True)[:8]
    categories = Category.objects.all()[:6]

    context = {
        'featured_products': featured_products,
        'new_products': new_products,
        'categories': categories,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/index.html', context)

def categories_view(request):
    """Barcha kategoriyalar sahifasi"""
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/categories.html', context)

def product_list_view(request):
    """Mahsulotlar ro'yxati - barcha filterlar bilan"""
    products = Product.objects.filter(is_available=True)
    categories = Category.objects.all()

    # ========== 1. Kategoriya bo'yicha filter ==========
    category_slug = request.GET.get('category')
    current_category = None
    if category_slug and category_slug != '':
        try:
            current_category = Category.objects.get(slug=category_slug)
            products = products.filter(category=current_category)
        except Category.DoesNotExist:
            pass

    # ========== 2. Narx bo'yicha filter ==========
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price and min_price != '':
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price and max_price != '':
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # ========== 3. Qidiruv (nom bo'yicha) ==========
    search_query = request.GET.get('q')
    if search_query and search_query != '':
        products = products.filter(name__icontains=search_query)

    # ========== 4. Tartiblash ==========
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'name_asc':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')

    # Foydalanuvchining yoqtirgan mahsulotlari ID larini olish
    wishlisted_ids = []
    if request.user.is_authenticated:
        wishlisted_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'products': products,
        'categories': categories,
        'current_category': current_category,
        'search_query': search_query,
        'sort': sort,
        'min_price': min_price,
        'max_price': max_price,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
        'wishlisted_ids': wishlisted_ids,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail_view(request, category_slug, product_slug):
    """Mahsulot detali - variantlar bilan"""
    product = get_object_or_404(Product, slug=product_slug, category__slug=category_slug, is_available=True)
    related_products = Product.objects.filter(category=product.category, is_available=True).exclude(id=product.id)[:4]

    # Sharhlar - faqat tasdiqlanganlari
    reviews = Review.objects.filter(product=product, is_approved=True).order_by('-created_at')

    # O'rtacha reyting
    avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()

    # Reyting taqsimoti
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()

    cart_quantity = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item = cart.items.filter(product=product).first()
            if cart_item:
                cart_quantity = cart_item.quantity

    # Foydalanuvchi sharh yozganmi
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()

    # Wishlist status
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()

    # Mavjud ranglar
    available_colors = product.get_available_colors()

    # Mavjud o'lchamlar (barcha)
    available_sizes = product.get_available_sizes()

    # ========== MUHIM: Foydalanuvchi sharh yozish imkoniyatini tekshirish ==========
    can_review = False
    if request.user.is_authenticated and not user_review:
        # To'g'ridan-to'g'ri OrderItem dan tekshirish
        order_items = OrderItem.objects.filter(
            order__user=request.user,
            order__status='delivered',
            product=product,
            can_review=True
        )
        if order_items.exists():
            can_review = True

    context = {
        'product': product,
        'related_products': related_products,
        'cart_quantity': cart_quantity,
        'cart_total_items': get_cart_total_items(request),
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'rating_distribution': rating_distribution,
        'user_review': user_review,
        'is_wishlisted': is_wishlisted,
        'wishlist_count': get_wishlist_count(request),
        'available_colors': available_colors,
        'available_sizes': available_sizes,
        'can_review': can_review,
    }
    return render(request, 'shop/product_detail.html', context)


from .models import TelegramUser


# Telegram xabarnoma yuborish uchun yordamchi funksiya
def send_telegram_notification(user, title, message, link=None):
    """Foydalanuvchiga Telegram xabarnoma yuborish"""
    try:
        from bot.bot import send_telegram_message
        from .models import TelegramUser

        telegram_user = TelegramUser.objects.filter(user=user, is_active=True).first()
        if telegram_user and telegram_user.chat_id:
            full_message = f"""
<b>{title}</b>

{message}

📅 Sana: {timezone.now().strftime('%d.%m.%Y %H:%M')}
            """
            if link:
                full_message += f"\n\n<a href=\"{link}\">🔗 Batafsil ma'lumot</a>"

            send_telegram_message(telegram_user.chat_id, full_message)
            return True
    except Exception as e:
        print(f"Xabarnoma yuborish xatolik: {e}")
    return False

def send_bulk_telegram_notification(users, title, message, link=None):
    """Bir nechta foydalanuvchilarga xabarnoma yuborish"""
    sent_count = 0
    for user in users:
        if send_telegram_notification(user, title, message, link):
            sent_count += 1
    return sent_count

def category_products_view(request, category_slug):
    """Kategoriya bo'yicha mahsulotlar"""
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category, is_available=True)

    # property ga qiymat belgilash o'rniga, context ga qo'shimcha ma'lumot yuborish
    product_list = []
    for product in products:
        product_list.append({
            'product': product,
            'total_stock': product.total_stock,
            'variants': product.variants.all()
        })

    context = {
        'category': category,
        'product_list': product_list,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/category_products.html', context)


def cart_add_view(request):
    """Savatga qo'shish - AJAX (rang va o'lcham bilan)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        size = data.get('size', '')
        color = data.get('color', '')
        quantity = int(data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id, is_available=True)

        # Rang va o'lchamni tekshirish
        if not color:
            return JsonResponse({
                'success': False,
                'message': 'Iltimos, rang tanlang!'
            })

        if not size:
            return JsonResponse({
                'success': False,
                'message': 'Iltimos, o\'lcham tanlang!'
            })

        # Variantdagi sonni tekshirish
        variant_stock = product.get_variant_stock(color, size)
        if variant_stock < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Kechirasiz, {color} rang, {size} o\'lchamda faqat {variant_stock} dona qoldi!'
            })

        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                color=color,
                defaults={'quantity': quantity}
            )
            if not created:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > variant_stock:
                    return JsonResponse({
                        'success': False,
                        'message': f'Kechirasiz, {color} rang, {size} o\'lchamda faqat {variant_stock} dona qoldi!'
                    })
                cart_item.quantity = new_quantity
                cart_item.save()
            total_items = cart.total_items
        else:
            session_cart = get_or_create_session_cart(request)
            session_item, created = SessionCartItem.objects.get_or_create(
                session_cart=session_cart,
                product=product,
                size=size,
                color=color,
                defaults={'quantity': quantity}
            )
            if not created:
                session_item.quantity += quantity
                session_item.save()
            total_items = session_cart.total_items

        return JsonResponse({
            'success': True,
            'total_items': total_items,
            'message': f'{product.name} ({color}, {size}) savatga qo\'shildi'
        })

    return JsonResponse({'success': False, 'message': 'Xatolik yuz berdi'})


def telegram_settings_view(request):
    """Foydalanuvchi Telegram chat ID sini sozlash"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Sozlamalarni ko\'rish uchun tizimga kiring!')
        return redirect('accounts:login')

    telegram_data, created = TelegramUser.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        chat_id = request.POST.get('chat_id', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if chat_id:
            # Chat ID ni tekshirish (test xabar yuborish)
            from bot.bot import send_telegram_message
            test_message = f"""
<b>✅ XABARNOMA SOZLAMALARI SOZLANDI!</b>

👤 Foydalanuvchi: {request.user.phone_number}
🆔 Chat ID: {chat_id}

Endi sizga quyidagi xabarlar keladi:
• 🛍 Buyurtma berilganda
• 🔄 Buyurtma holati o'zgarganda  
• 📦 Buyurtma yetkazilganda
• ⭐ Yangi sharhlar (adminlar uchun)

<b>Xabarnomalardan to'liq foydalanish uchun ushbu sozlamani faollashtiring!</b>
            """
            result = send_telegram_message(chat_id, test_message)

            if result and result.get('ok'):
                telegram_data.chat_id = chat_id
                telegram_data.is_active = is_active
                telegram_data.save()
                messages.success(request, "✅ Telegram xabarnoma sozlamalari muvaffaqiyatli saqlandi!")
            else:
                messages.error(request,
                               "❌ Chat ID noto'g'ri! Iltimos, botdan to'g'ri ID ni oling.\n\nBotga o'ting va /start buyrug'ini yuboring.")
        else:
            telegram_data.is_active = is_active
            telegram_data.save()
            messages.success(request, "✅ Sozlamalar saqlandi!")

        return redirect('shop:telegram_settings')

    context = {
        'chat_id': telegram_data.chat_id,
        'is_active': telegram_data.is_active,
        'bot_username': settings.TELEGRAM_BOT_USERNAME,
    }
    return render(request, 'shop/telegram_settings.html', context)

def get_sizes_api(request):
    """Rangga mos o'lchamlarni qaytarish API"""
    product_id = request.GET.get('product_id')
    color = request.GET.get('color')

    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.filter(color=color, stock__gt=0)

    sizes = [{'size': v.size, 'stock': v.stock} for v in variants]

    return JsonResponse({'sizes': sizes})


def cart_view(request):
    """Savat sahifasi"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Savatni ko\'rish uchun tizimga kiring!')
        return redirect('accounts:login')

    cart, created = Cart.objects.get_or_create(user=request.user)

    # Kupon chegirmasini hisoblash
    discount = 0
    coupon_code = None
    coupon_id = None

    if 'coupon_id' in request.session:
        try:
            coupon_id = request.session.get('coupon_id')
            coupon = Coupon.objects.get(id=coupon_id, is_active=True)

            # Kupon hali ham amal qilishini tekshirish
            now = timezone.now()
            if coupon.valid_from <= now <= coupon.valid_to:
                discount = coupon.calculate_discount(cart.total_price)
                coupon_code = coupon.code
                # Sessionni yangilash
                request.session['coupon_code'] = coupon_code
                request.session['coupon_discount'] = float(discount)
            else:
                # Kupon muddati tugagan bo'lsa, sessiondan o'chirish
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
                if 'coupon_discount' in request.session:
                    del request.session['coupon_discount']
                if 'coupon_id' in request.session:
                    del request.session['coupon_id']
        except Coupon.DoesNotExist:
            # Kupon topilmasa, sessiondan o'chirish
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
            if 'coupon_discount' in request.session:
                del request.session['coupon_discount']
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
    elif 'coupon_code' in request.session:
        coupon_code = request.session.get('coupon_code')
        discount = float(request.session.get('coupon_discount', 0))

    final_total = cart.total_price - discount

    context = {
        'cart': cart,
        'cart_total_items': cart.total_items,
        'wishlist_count': get_wishlist_count(request),
        'discount': discount,
        'final_total': final_total,
        'coupon_code': coupon_code,
    }
    return render(request, 'shop/cart.html', context)


def cart_remove_view(request, item_id):
    """Savatdan o'chirish"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Mahsulotni o\'chirish uchun tizimga kiring!')
        return redirect('accounts:login')

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Mahsulot savatdan o\'chirildi')
    return redirect('shop:cart')


def cart_update_view(request, item_id):
    """Savatdagi mahsulot sonini o'zgartirish"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Tizimga kiring!'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))

            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

            # Mahsulotning variantini tekshirish
            if cart_item.size and cart_item.color:
                variant = ProductVariant.objects.filter(
                    product=cart_item.product,
                    size=cart_item.size,
                    color=cart_item.color
                ).first()
                max_stock = variant.stock if variant else 0
            elif cart_item.size:
                variant = ProductVariant.objects.filter(
                    product=cart_item.product,
                    size=cart_item.size
                ).first()
                max_stock = variant.stock if variant else 0
            elif cart_item.color:
                variant = ProductVariant.objects.filter(
                    product=cart_item.product,
                    color=cart_item.color
                ).first()
                max_stock = variant.stock if variant else 0
            else:
                max_stock = cart_item.product.total_stock

            # Maksimal sondan oshib ketmasligini tekshirish
            if quantity > max_stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Kechirasiz, omborda faqat {max_stock} dona qoldi!'
                })

            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()

            cart = Cart.objects.get(user=request.user)
            return JsonResponse({
                'success': True,
                'total_price': float(cart_item.total_price) if quantity > 0 else 0,
                'cart_total': float(cart.total_price),
                'total_items': cart.total_items
            })
        except Exception as e:
            print(f"Xatolik: {e}")
            return JsonResponse({'success': False, 'message': 'Xatolik yuz berdi!'})

    return JsonResponse({'success': False, 'message': 'Xatolik yuz berdi!'})


# ========== KUPON VIEWS ==========

def apply_coupon_view(request):
    """Kuponi qo'llash (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Tizimga kiring!'})

    if request.method == 'POST':
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').upper().strip()

        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)

            # Kuponning amal qilish muddatini tekshirish
            now = timezone.now()
            if not (coupon.valid_from <= now <= coupon.valid_to):
                return JsonResponse({'success': False, 'message': 'Kuponning amal qilish muddati tugagan!'})

            # Ishlatilish chegarasini tekshirish
            if coupon.usage_limit <= coupon.used_count:
                return JsonResponse({'success': False, 'message': 'Kupon ishlatilish chegarasiga yetgan!'})

            # Foydalanuvchi allaqachon ishlatganmi?
            if UserCoupon.objects.filter(user=request.user, coupon=coupon).exists():
                return JsonResponse({'success': False, 'message': 'Siz bu kupondan allaqachon foydalandingiz!'})

            # Savatni olish
            cart = Cart.objects.filter(user=request.user).first()
            if not cart or cart.total_items == 0:
                return JsonResponse({'success': False, 'message': 'Savat bo\'sh!'})

            # Minimal buyurtma summasini tekshirish
            if cart.total_price < coupon.min_order_amount:
                return JsonResponse({
                    'success': False,
                    'message': f'Kupondan foydalanish uchun minimal buyurtma summasi {coupon.min_order_amount:,.0f} so\'m bo\'lishi kerak!'
                })

            # Chegirmani hisoblash
            discount = coupon.calculate_discount(cart.total_price)

            # Sessionga kupon ma'lumotlarini saqlash
            request.session['coupon_code'] = coupon_code
            request.session['coupon_discount'] = float(discount)
            request.session['coupon_id'] = coupon.id

            return JsonResponse({
                'success': True,
                'message': f'Kupon qo\'llandi! {discount:,.0f} so\'m chegirma',
                'discount': float(discount),
                'cart_total': float(cart.total_price),
                'new_total': float(cart.total_price - discount),
                'coupon_code': coupon_code
            })

        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Kupon topilmadi!'})

    return JsonResponse({'success': False, 'message': 'Xatolik yuz berdi!'})


def remove_coupon_view(request):
    """Kuponi olib tashlash"""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    if 'coupon_discount' in request.session:
        del request.session['coupon_discount']
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
    return JsonResponse({'success': True, 'message': 'Kupon olib tashlandi!', 'redirect': True})


def checkout_view(request):
    """Buyurtma berish sahifasi"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Buyurtma berish uchun tizimga kiring!')
        return redirect('accounts:login')

    cart = Cart.objects.filter(user=request.user).first()
    if not cart or cart.total_items == 0:
        messages.warning(request, 'Savatda hech qanday mahsulot yo\'q')
        return redirect('shop:cart')

    # Kupon chegirmasini hisoblash
    discount = 0
    coupon = None
    coupon_code = None

    if 'coupon_id' in request.session:
        try:
            coupon_id = request.session.get('coupon_id')
            coupon = Coupon.objects.get(id=coupon_id, is_active=True)

            now = timezone.now()
            if coupon.valid_from <= now <= coupon.valid_to:
                discount = coupon.calculate_discount(cart.total_price)
                coupon_code = coupon.code
            else:
                if 'coupon_id' in request.session:
                    del request.session['coupon_id']
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
                if 'coupon_discount' in request.session:
                    del request.session['coupon_discount']
        except Coupon.DoesNotExist:
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
            if 'coupon_discount' in request.session:
                del request.session['coupon_discount']
    elif 'coupon_code' in request.session:
        coupon_code = request.session.get('coupon_code')
        discount = float(request.session.get('coupon_discount', 0))

    final_total = cart.total_price - discount
    if final_total < 0:
        final_total = 0

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = final_total
            order.save()

            if coupon:
                UserCoupon.objects.create(
                    user=request.user,
                    coupon=coupon,
                    order=order
                )
                coupon.used_count += 1
                coupon.save()

                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
                if 'coupon_discount' in request.session:
                    del request.session['coupon_discount']
                if 'coupon_id' in request.session:
                    del request.session['coupon_id']

            # Buyurtma mahsulotlarini saqlash va variantdan sonni kamaytirish
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    price=item.product.price
                )

                # Variantdan sonni kamaytirish
                if item.size and item.color:
                    variant = ProductVariant.objects.filter(
                        product=item.product,
                        size=item.size,
                        color=item.color
                    ).first()
                    if variant:
                        variant.stock -= item.quantity
                        variant.save()
                elif item.size:
                    variant = ProductVariant.objects.filter(
                        product=item.product,
                        size=item.size
                    ).first()
                    if variant:
                        variant.stock -= item.quantity
                        variant.save()
                elif item.color:
                    variant = ProductVariant.objects.filter(
                        product=item.product,
                        color=item.color
                    ).first()
                    if variant:
                        variant.stock -= item.quantity
                        variant.save()

            # Savatni tozalash
            cart.items.all().delete()

            # ========== TELEGRAM XABARNOMA YUBORISH ==========
            try:
                from bot.bot import send_telegram_message
                from .models import TelegramUser

                # O'zbekiston vaqtini olish
                uzb_time = timezone.localtime(timezone.now())
                formatted_time = uzb_time.strftime('%d.%m.%Y %H:%M')

                # Foydalanuvchiga xabar yuborish
                user_telegram = TelegramUser.objects.filter(user=request.user, is_active=True).first()
                if user_telegram and user_telegram.chat_id:
                    order_message = f"""
<b>✅ BUYURTMA QABUL QILINDI!</b>

🆔 Buyurtma raqami: <b>#{order.id}</b>
💰 Umumiy summa: <b>{order.total_amount:,.0f} so'm</b>
📅 Sana: {formatted_time}

📦 Buyurtmangiz holatini "Buyurtmalarim" bo'limidan kuzatishingiz mumkin.

<a href="http://127.0.0.1:8000/my-orders/">🔗 Buyurtmalarim sahifasiga o'tish</a>
                    """
                    send_telegram_message(user_telegram.chat_id, order_message)
                    print(f"✅ Xabar yuborildi: {request.user.phone_number}")

                # Adminlarga xabar yuborish
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    admin_telegram = TelegramUser.objects.filter(user=admin, is_active=True).first()
                    if admin_telegram and admin_telegram.chat_id:
                        admin_message = f"""
<b>🆕 YANGI BUYURTMA!</b>

👤 Mijoz: {request.user.phone_number}
🆔 Buyurtma: #{order.id}
💰 Summa: {order.total_amount:,.0f} so'm
📦 Mahsulotlar: {cart.total_items} dona
📅 Sana: {formatted_time}

<a href="http://127.0.0.1:8000/admin/shop/order/{order.id}/change/">🔗 Admin panelda ko'rish</a>
                        """
                        send_telegram_message(admin_telegram.chat_id, admin_message)
                        print(f"✅ Admin xabar yuborildi: {admin.phone_number}")

            except Exception as e:
                print(f"Telegram xabarnoma yuborishda xatolik: {e}")

            messages.success(request, f'✅ Buyurtma qabul qilindi! Buyurtma raqami: #{order.id}')
            return redirect('shop:order_success', order_id=order.id)
        else:
            messages.error(request, 'Xatolik yuz berdi. Iltimos, ma\'lumotlarni to\'g\'ri kiriting!')
    else:
        initial_data = {}
        if request.user.full_name:
            initial_data['full_name'] = request.user.full_name
        if request.user.phone_number:
            initial_data['phone'] = request.user.phone_number
        form = OrderForm(initial=initial_data)

    context = {
        'cart': cart,
        'form': form,
        'cart_total_items': cart.total_items,
        'wishlist_count': get_wishlist_count(request),
        'discount': discount,
        'final_total': final_total,
        'coupon_code': coupon_code,
    }
    return render(request, 'shop/checkout.html', context)


def order_success_view(request, order_id):
    """Buyurtma muvaffaqiyatli sahifasi"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Agar buyurtma yetkazilgan bo'lsa, sharh yozish imkoniyatini yoqish
    if order.status == 'delivered':
        for item in order.items.all():
            if not item.can_review:
                item.can_review = True
                item.save()

        # ========== TELEGRAM XABARNOMA (Yetkazilganligi haqida) ==========
        try:
            from bot.bot import send_telegram_message
            from .models import TelegramNotification

            user_telegram = TelegramNotification.objects.filter(user=request.user, is_active=True).first()
            if user_telegram:
                # Mahsulotlar ro'yxatini tayyorlash
                products_list = ""
                for item in order.items.all():
                    products_list += f"• {item.product.name} x {item.quantity} dona\n"

                delivered_message = f"""
<b>📦 BUYURTMANGIZ YETKAZILDI!</b>

🆔 Buyurtma raqami: <b>#{order.id}</b>
💰 Umumiy summa: <b>{order.total_amount:,.0f} so'm</b>
📅 Yetkazilgan sana: {timezone.now().strftime('%d.%m.%Y %H:%M')}

<b>📋 Mahsulotlar:</b>
{products_list}

⭐ <b>Mahsulotni baholash va sharh qoldirish imkoniyati ochildi!</b>

<a href="http://127.0.0.1:8000/my-orders/">🔗 Buyurtmalarim sahifasiga o'tish</a>
                """
                send_telegram_message(user_telegram.chat_id, delivered_message)
                print(f"✅ Telegram xabar yuborildi: {user_telegram.chat_id}")
        except Exception as e:
            print(f"Telegram xabar yuborishda xatolik: {e}")

    context = {
        'order': order,
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/order_success.html', context)


def my_orders_view(request):
    """Foydalanuvchi buyurtmalari"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Buyurtmalaringizni ko\'rish uchun tizimga kiring!')
        return redirect('accounts:login')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/my_orders.html', context)


# ========== REVIEWS VIEWS ==========

@login_required
def add_review_view(request, product_id):
    """Sharh qo'shish - faqat sotib olgan va yetkazilgan mahsulotlar uchun"""
    product = get_object_or_404(Product, id=product_id, is_available=True)

    # Foydalanuvchi bu mahsulotni sotib olganmi va yetkazilganmi tekshirish
    can_write_review = False
    order_item = None

    # Foydalanuvchining yetkazilgan buyurtmalarini tekshirish
    orders = Order.objects.filter(user=request.user, status='delivered')
    for order in orders:
        order_item = order.items.filter(product=product, can_review=True).first()
        if order_item:
            can_write_review = True
            break

    if not can_write_review:
        messages.error(request,
                       'Siz bu mahsulotni sotib olmagansiz yoki yetkazib berilmagan! Faqat sotib olingan va yetkazilgan mahsulotlarga sharh yozishingiz mumkin.')
        return redirect('shop:product_detail', category_slug=product.category.slug, product_slug=product.slug)

    # Foydalanuvchi allaqachon sharh yozganmi?
    existing_review = Review.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.error(request, 'Siz bu mahsulotga allaqachon sharh yozgansiz!')
        return redirect('shop:product_detail', category_slug=product.category.slug, product_slug=product.slug)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating and comment:
            review = Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment
            )
            # Sharh yozilganligini belgilash
            if order_item:
                order_item.can_review = False
                order_item.reviewed_at = timezone.now()
                order_item.save()

            messages.success(request, 'Sharhingiz qabul qilindi! Rahmat!')
        else:
            if not rating:
                messages.error(request, 'Iltimos, mahsulotni baholang!')
            elif not comment:
                messages.error(request, 'Iltimos, sharhingizni yozing!')

    return redirect('shop:product_detail', category_slug=product.category.slug, product_slug=product.slug)


@login_required
def edit_review_view(request, review_id):
    """Sharhni tahrirlash"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating and comment:
            review.rating = int(rating)
            review.comment = comment
            review.save()
            messages.success(request, 'Sharhingiz muvaffaqiyatli yangilandi!')
        else:
            messages.error(request, 'Iltimos, barcha maydonlarni to\'ldiring!')

        return redirect('shop:product_detail', category_slug=product.category.slug, product_slug=product.slug)

    context = {
        'review': review,
        'product': product,
    }
    return render(request, 'shop/edit_review.html', context)


@login_required
def delete_review_view(request, review_id):
    """Sharhni o'chirish"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product
    review.delete()
    messages.success(request, 'Sharhingiz muvaffaqiyatli o\'chirildi!')
    return redirect('shop:product_detail', category_slug=product.category.slug, product_slug=product.slug)


def product_reviews_view(request, product_id):
    """Mahsulotning barcha sharhlari (AJAX)"""
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product, is_approved=True).order_by('-created_at')

    data = {
        'reviews': [
            {
                'user': review.user.phone_number,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%d.%m.%Y %H:%M'),
            }
            for review in reviews
        ],
        'avg_rating': reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0,
        'total_reviews': reviews.count()
    }
    return JsonResponse(data)