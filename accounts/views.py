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

            # Foydalanuvchini topish yoki yaratish
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'is_active': False}
            )

            if not created and user.is_active:
                messages.error(request, 'Bu raqam allaqachon ro\'yxatdan o\'tgan')
                return redirect('login')

            # Eski OTP larni o'chirish
            OTP.objects.filter(user=user, created_at__lt=timezone.now() - timedelta(minutes=5)).delete()

            # Yangi OTP yaratish
            otp_code = generate_otp()
            otp = OTP.objects.create(user=user, code=otp_code)

            # Terminalda kodni chiqarish
            print(f"\n{'=' * 50}")
            print(f"📱 {phone_number} uchun OTP kodi: {otp_code}")
            print(f"⏰ Kod 5 daqiqa amal qiladi")
            print(f"{'=' * 50}\n")

            # Sessionga saqlash
            request.session['registration_phone'] = phone_number

            messages.success(request, f'{phone_number} raqamiga kod yuborildi (Terminalda ko\'ring)')
            return redirect('verify_otp')
    else:
        form = PhoneNumberForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_otp_view(request):
    phone_number = request.session.get('registration_phone')
    if not phone_number:
        messages.error(request, 'Avval telefon raqamni kiriting')
        return redirect('register')

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        messages.error(request, 'Foydalanuvchi topilmadi')
        return redirect('register')

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

                # OTP ni ishlatilgan deb belgilash
                otp.is_used = True
                otp.save()

                # Sessionga OTP tasdiqlanganligini saqlash
                request.session['otp_verified'] = True

                messages.success(request, 'Kod tasdiqlandi! Endi parolingizni belgilang.')
                return redirect('set_password')

            except OTP.DoesNotExist:
                messages.error(request, 'Noto\'g\'ri yoki eskirgan kod')
    else:
        form = OTPVerificationForm()

    return render(request, 'accounts/verify_otp.html', {'form': form, 'phone_number': phone_number})


def set_password_view(request):
    # OTP tasdiqlanganligini tekshirish
    if not request.session.get('otp_verified'):
        messages.error(request, 'Avval telefon raqamni tasdiqlang!')
        return redirect('register')

    phone_number = request.session.get('registration_phone')
    if not phone_number:
        return redirect('register')

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']

            # Parolni o'rnatish
            user.set_password(password)
            user.is_active = True
            user.save()

            # Avtomatik login qilish
            login(request, user)

            # Sessionni tozalash
            del request.session['registration_phone']
            del request.session['otp_verified']

            messages.success(request,
                             f"✅ Muvaffaqiyatli ro'yxatdan o'tdingiz! Endi do'kondan xarid qilishingiz mumkin.")
            return redirect('home')
    else:
        form = SetPasswordForm()

    return render(request, 'accounts/set_password.html', {'form': form, 'phone_number': phone_number})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"👋 Xush kelibsiz, {user.phone_number}!")
                    return redirect('home')
                else:
                    messages.error(request, 'Akkauntingiz faollashtirilmagan. Avval ro\'yxatdan o\'ting.')
            else:
                messages.error(request, 'Telefon raqam yoki parol xato')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def home_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'accounts/home.html', {'user': request.user})


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'Tizimdan chiqdingiz')
    return redirect('login')