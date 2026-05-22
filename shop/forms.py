from django import forms
from .models import Order
from .models import Order, Review

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'address', 'phone', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ism familiyangiz'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'To\'liq manzilingiz (uy, ko\'cha, shahar)',
                'rows': 3
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+998 XX XXX XX XX'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Qo\'shimcha ma\'lumot (istalgan)',
                'rows': 2
            }),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}, choices=[
                (5, '5 ★ - Ajoyib'),
                (4, '4 ★ - Yaxshi'),
                (3, '3 ★ - O\'rtacha'),
                (2, '2 ★ - Yomon'),
                (1, '1 ★ - Juda yomon'),
            ]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Mahsulot haqida fikringizni yozing...'
            }),
        }
        labels = {
            'rating': 'Baholang',
            'comment': 'Sharhingiz',
        }

class CouponForm(forms.Form):
    """Kupon kodini kiritish formasi"""
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kupon kodini kiriting',
            'id': 'coupon_code'
        })
    )