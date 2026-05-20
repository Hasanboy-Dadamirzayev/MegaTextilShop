import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from .models import User, OTP
from .forms import PhoneNumberForm, OTPVerificationForm, SetPasswordForm, LoginForm


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def register_view(request):
    """1-bosqich: Telefon raqam kiritish"""

    if request.user.is_authenticated:
        return redirect('shop:index')

    if request.method == 'POST':
        form = PhoneNumberForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']

            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number

            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'is_active': False}
            )

            if not created and user.is_active:
                messages.error(request, 'Bu raqam allaqachon ro\'yxatdan o\'tgan')
                return redirect('accounts:login')

            # Sessionga telefon raqamni saqlash
            request.session['registration_phone'] = phone_number

            # Vaqtinchalik token yaratish
            import uuid
            temp_token = str(uuid.uuid4())
            request.session['temp_token'] = temp_token

            # Cache ga vaqtinchalik ma'lumotni saqlash (10 daqiqa)
            cache.set(f'pending_registration_{temp_token}', {
                'phone_number': phone_number,
                'step': 'waiting_for_code'
            }, timeout=600)

            messages.success(request, f'Telefon raqam qabul qilindi. Bot orqali kod oling!')
            return redirect('accounts:get_telegram_code')
    else:
        form = PhoneNumberForm()

    return render(request, 'accounts/register.html', {'form': form})


def get_telegram_code_view(request):
    """2-bosqich: Bot orqali kod olish sahifasi"""

    phone_number = request.session.get('registration_phone')
    temp_token = request.session.get('temp_token')

    if not phone_number or not temp_token:
        messages.error(request, 'Avval telefon raqamni kiriting')
        return redirect('accounts:register')

    context = {
        'bot_username': settings.TELEGRAM_BOT_USERNAME,
        'temp_token': temp_token,
        'phone_number': phone_number
    }
    return render(request, 'accounts/get_telegram_code.html', context)


def verify_telegram_code_view(request, token):
    """3-bosqich: Telegramdan kelgan kodni tekshirish"""

    # Cache dan ma'lumotni olish
    pending_data = cache.get(f'pending_registration_{token}')

    if not pending_data:
        messages.error(request, 'Sessiya tugagan. Qaytadan urinib ko\'ring!')
        return redirect('accounts:register')

    phone_number = pending_data.get('phone_number')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']

            # OTP modeldan kodni tekshirish
            try:
                otp = OTP.objects.filter(
                    code=otp_code,
                    is_used=False,
                    created_at__gte=timezone.now() - timedelta(minutes=5)
                ).first()

                if otp and otp.user.phone_number == phone_number:
                    # Kod to'g'ri
                    otp.is_used = True
                    otp.save()

                    # Cache dan tozalash
                    cache.delete(f'pending_registration_{token}')

                    request.session['registration_phone'] = phone_number
                    request.session['otp_verified'] = True

                    messages.success(request, 'Kod tasdiqlandi! Endi parolingizni belgilang.')
                    return redirect('accounts:set_password')
                else:
                    messages.error(request, 'Noto\'g\'ri yoki eskirgan kod! Botdan yangi kod oling.')

            except Exception as e:
                print(f"Kod tekshirish xatolik: {e}")
                messages.error(request, 'Xatolik yuz berdi. Qaytadan urinib ko\'ring!')
        else:
            messages.error(request, 'Iltimos, 6 xonali kodni kiriting!')
    else:
        form = OTPVerificationForm()

    context = {
        'form': form,
        'phone_number': phone_number,
        'token': token,
        'bot_username': settings.TELEGRAM_BOT_USERNAME,
    }
    return render(request, 'accounts/verify_telegram_code.html', context)


def resend_telegram_code_view(request, token):
    """Kodni qayta yuborish - bot orqali"""

    pending_data = cache.get(f'pending_registration_{token}')
    if not pending_data:
        messages.error(request, 'Sessiya tugagan. Qaytadan urinib ko\'ring!')
        return redirect('accounts:register')

    phone_number = pending_data.get('phone_number')

    messages.info(request, f'Iltimos, Telegram botga qayta murojaat qiling: @{settings.TELEGRAM_BOT_USERNAME}')
    return redirect('accounts:verify_telegram_code', token=token)


def set_password_view(request):
    """4-bosqich: Parol o'rnatish"""

    # Agar allaqachon login qilgan bo'lsa
    if request.user.is_authenticated:
        return redirect('shop:index')

    # OTP tasdiqlanganligini tekshirish
    if not request.session.get('otp_verified'):
        messages.error(request, 'Avval kodni tasdiqlang!')
        return redirect('accounts:register')

    phone_number = request.session.get('registration_phone')
    if not phone_number:
        return redirect('accounts:register')

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return redirect('accounts:register')

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']

            # Parolni o'rnatish
            user.set_password(password)
            user.is_active = True
            user.save()

            # Avtomatik login qilish
            from django.contrib.auth import authenticate, login

            # Foydalanuvchini authenticate qilish
            authenticated_user = authenticate(request, username=phone_number, password=password)

            if authenticated_user is not None:
                login(request, authenticated_user)
                print(f"✅ Foydalanuvchi login qildi: {phone_number}")
            else:
                print(f"❌ Authenticate bo'lmadi: {phone_number}")
                # Agar authenticate ishlamasa, to'g'ridan-to'g'ri login qilish
                login(request, user)

            # Sessionni tozalash
            request.session.flush()

            # Yangi session yaratish va foydalanuvchini qayta login qilish
            from django.contrib.auth import login as auth_login
            auth_login(request, user)

            messages.success(request, f"✅ Muvaffaqiyatli ro'yxatdan o'tdingiz! Xush kelibsiz, {user.phone_number}!")

            # Do'konning bosh sahifasiga yo'naltirish
            return redirect('shop:index')
        else:
            messages.error(request, 'Parollar mos kelmadi yoki parol juda qisqa!')
    else:
        form = SetPasswordForm()

    return render(request, 'accounts/set_password.html', {
        'form': form,
        'phone_number': phone_number
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:index')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None and user.is_active:
                login(request, user)
                messages.success(request, f"👋 Xush kelibsiz, {user.phone_number}!")
                return redirect('shop:index')
            else:
                messages.error(request, 'Telefon raqam yoki parol xato')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'Tizimdan chiqdingiz')
    return redirect('shop:index')