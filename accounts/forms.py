from django import forms
from django.contrib.auth.forms import AuthenticationForm


class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998 XX XXX XX XX',
            'id': 'phone_number'
        })
    )

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-code-input',
            'placeholder': '000000',
            'id': 'otp_code'
        })
    )


class SetPasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolingizni kiriting (kamida 6 belgi)'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolni takrorlang'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Parollar bir-biriga mos kelmadi!")

        if password and len(password) < 6:
            raise forms.ValidationError("Parol kamida 6 belgidan iborat bo'lishi kerak!")

        return cleaned_data


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998 XX XXX XX XX'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolingiz'
        })
    )