from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Dictionary dan key bo'yicha qiymat olish"""
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)