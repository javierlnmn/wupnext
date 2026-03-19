from django import template

from common.utils import get_timer_format

register = template.Library()


@register.filter
def duration_format(seconds):
    return get_timer_format(seconds)
