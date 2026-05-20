import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from .forms import OrderForm
from .models import Category, Product, Cart, CartItem, Order, OrderItem, SessionCart, SessionCartItem, Wishlist


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
    """Mahsulot detali"""
    product = get_object_or_404(Product, slug=product_slug, category__slug=category_slug, is_available=True)
    related_products = Product.objects.filter(category=product.category, is_available=True).exclude(id=product.id)[:4]

    cart_quantity = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item = cart.items.filter(product=product).first()
            if cart_item:
                cart_quantity = cart_item.quantity
    else:
        session_cart = get_or_create_session_cart(request)
        session_item = session_cart.items.filter(product=product).first()
        if session_item:
            cart_quantity = session_item.quantity

    # Mahsulot yoqtirilganmi tekshirish
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()

    context = {
        'product': product,
        'related_products': related_products,
        'cart_quantity': cart_quantity,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
        'is_wishlisted': is_wishlisted,
    }
    return render(request, 'shop/product_detail.html', context)


def category_products_view(request, category_slug):
    """Kategoriya bo'yicha mahsulotlar"""
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category, is_available=True)

    context = {
        'category': category,
        'products': products,
        'cart_total_items': get_cart_total_items(request),
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/category_products.html', context)


def cart_add_view(request):
    """Savatga qo'shish - AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id, is_available=True)

        if quantity > product.stock and product.stock > 0:
            return JsonResponse({
                'success': False,
                'message': f'Kechirasiz, omborda faqat {product.stock} dona qoldi'
            })

        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not created:
                if cart_item.quantity + quantity > product.stock and product.stock > 0:
                    return JsonResponse({
                        'success': False,
                        'message': f'Kechirasiz, omborda faqat {product.stock} dona qoldi'
                    })
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
            total_items = cart.total_items
        else:
            session_cart = get_or_create_session_cart(request)
            session_item, created = SessionCartItem.objects.get_or_create(session_cart=session_cart, product=product)
            if not created:
                if session_item.quantity + quantity > product.stock and product.stock > 0:
                    return JsonResponse({
                        'success': False,
                        'message': f'Kechirasiz, omborda faqat {product.stock} dona qoldi'
                    })
                session_item.quantity += quantity
            else:
                session_item.quantity = quantity
            session_item.save()
            total_items = session_cart.total_items

        return JsonResponse({
            'success': True,
            'total_items': total_items,
            'message': f'{product.name} savatga qo\'shildi'
        })

    return JsonResponse({'success': False, 'message': 'Xatolik yuz berdi'})


def cart_view(request):
    """Savat sahifasi"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Savatni ko\'rish uchun tizimga kiring!')
        return redirect('accounts:login')

    cart, created = Cart.objects.get_or_create(user=request.user)
    context = {
        'cart': cart,
        'cart_total_items': cart.total_items,
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/cart.html', context)


def cart_remove_view(request, item_id):
    """Savatdan o'chirish - login tekshiruvi"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Mahsulotni o\'chirish uchun tizimga kiring!')
        return redirect('accounts:login')

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Mahsulot savatdan o\'chirildi')
    return redirect('shop:cart')


def cart_update_view(request, item_id):
    """Savatdagi mahsulot sonini o'zgartirish - login tekshiruvi"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Tizimga kiring!'})

    if request.method == 'POST':
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))

        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if quantity > cart_item.product.stock and cart_item.product.stock > 0:
            return JsonResponse({
                'success': False,
                'message': f'Kechirasiz, omborda faqat {cart_item.product.stock} dona qoldi'
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

    return JsonResponse({'success': False})


def checkout_view(request):
    """Buyurtma berish sahifasi - login tekshiruvi"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Buyurtma berish uchun tizimga kiring!')
        return redirect('accounts:login')

    cart = Cart.objects.filter(user=request.user).first()
    if not cart or cart.total_items == 0:
        messages.warning(request, 'Savatda hech qanday mahsulot yo\'q')
        return redirect('shop:cart')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = cart.total_price
            order.save()

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )

                product = item.product
                product.stock -= item.quantity
                product.save()

            cart.items.all().delete()

            messages.success(request, f'Buyurtma qabul qilindi! Buyurtma raqami: #{order.id}')
            return redirect('shop:order_success', order_id=order.id)
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
    }
    return render(request, 'shop/checkout.html', context)


def order_success_view(request, order_id):
    """Buyurtma muvaffaqiyatli sahifasi - login tekshiruvi"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
        'wishlist_count': get_wishlist_count(request),
    }
    return render(request, 'shop/order_success.html', context)


def my_orders_view(request):
    """Foydalanuvchi buyurtmalari - login tekshiruvi"""
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