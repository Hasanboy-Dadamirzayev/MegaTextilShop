import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import User, OTP
from .forms import PhoneNumberForm, OTPVerificationForm, SetPasswordForm, LoginForm


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def register_view(request):
    if request.method == 'POST':
        form = PhoneNumberForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']

            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'is_active': False}
            )

            if not created and user.is_active:
                messages.error(request, 'Bu raqam allaqachon ro\'yxatdan o\'tgan')
                return redirect('accounts:login')

            OTP.objects.filter(user=user, created_at__lt=timezone.now() - timedelta(minutes=5)).delete()

            otp_code = generate_otp()
            otp = OTP.objects.create(user=user, code=otp_code)

            print(f"\n{'='*50}")
            print(f"📱 {phone_number} uchun OTP kodi: {otp_code}")
            print(f"⏰ Kod 5 daqiqa amal qiladi")
            print(f"{'='*50}\n")

            request.session['registration_phone'] = phone_number

            messages.success(request, f'{phone_number} raqamiga kod yuborildi (Terminalda ko\'ring)')
            return redirect('accounts:verify_otp')
    else:
        form = PhoneNumberForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_otp_view(request):
    phone_number = request.session.get('registration_phone')
    if not phone_number:
        messages.error(request, 'Avval telefon raqamni kiriting')
        return redirect('accounts:register')

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        messages.error(request, 'Foydalanuvchi topilmadi')
        return redirect('accounts:register')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']

            try:
                otp = OTP.objects.get(
                    user=user,
                    code=otp_code,
                    is_used=False,
                    created_at__gte=timezone.now() - timedelta(minutes=5)
                )

                otp.is_used = True
                otp.save()

                request.session['otp_verified'] = True

                messages.success(request, 'Kod tasdiqlandi! Endi parolingizni belgilang.')
                return redirect('accounts:set_password')

            except OTP.DoesNotExist:
                messages.error(request, 'Noto\'g\'ri yoki eskirgan kod')
    else:
        form = OTPVerificationForm()

    return render(request, 'accounts/verify_otp.html', {'form': form, 'phone_number': phone_number})


def set_password_view(request):
    if not request.session.get('otp_verified'):
        messages.error(request, 'Avval telefon raqamni tasdiqlang!')
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

            user.set_password(password)
            user.is_active = True
            user.save()

            login(request, user)

            del request.session['registration_phone']
            del request.session['otp_verified']

            messages.success(request, f"✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!")
            return redirect('shop:index')
    else:
        form = SetPasswordForm()

    return render(request, 'accounts/set_password.html', {'form': form, 'phone_number': phone_number})



from shop.views import merge_session_cart_to_user_cart


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

                # Session savatni user savatiga qo'shish
                merge_session_cart_to_user_cart(request, user)

                messages.success(request, f"👋 Xush kelibsiz, {user.phone_number}!")
                return redirect('shop:index')
            else:
                messages.error(request, 'Telefon raqam yoki parol xato')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def home_view(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return redirect('shop:index')


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'Tizimdan chiqdingiz')
    return redirect('shop:index')