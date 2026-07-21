from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Dictionary dan key bo'yicha qiymat olish"""
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Dictionary dan key bo'yicha qiymat olish"""
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)


@register.filter
def sum_attribute(queryset, attribute):
    """QuerySet dan berilgan attribute bo'yicha yig'indi hisoblash"""
    if not queryset:
        return 0
    total = 0
    for obj in queryset:
        total += getattr(obj, attribute, 0)
    return total