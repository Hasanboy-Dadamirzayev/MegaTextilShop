from django import forms
from .models import Order

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


