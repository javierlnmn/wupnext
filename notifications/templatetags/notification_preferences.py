from django import template

from ..forms import NotificationPreferencesForm

register = template.Library()


@register.inclusion_tag('notifications/preferences_matrix.html', takes_context=True)
def notification_preferences_matrix(context):
    user = context['request'].user

    if not user.is_authenticated:
        return {'form': None}

    return {'form': NotificationPreferencesForm(user=user)}
