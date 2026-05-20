from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('get-telegram-code/', views.get_telegram_code_view, name='get_telegram_code'),
    path('verify-telegram-code/<str:token>/', views.verify_telegram_code_view, name='verify_telegram_code'),
    path('resend-telegram-code/<str:token>/', views.resend_telegram_code_view, name='resend_telegram_code'),
    path('set-password/', views.set_password_view, name='set_password'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]