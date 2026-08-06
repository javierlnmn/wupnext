from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from notifications.base import BaseNotification
from notifications.models import Channel
from notifications.registry import register


@register
class PasswordResetNotification(BaseNotification):
    event = 'account_password_reset'
    label = 'Password recovery'
    description = 'Link to choose a new password, sent when one is requested.'
    channels = (Channel.EMAIL,)
    optional = False

    def is_applicable_for(self, user, context):
        return True

    def dedup_key(self, user, context):
        return ''  # Bypass dedup log. TODO: Turn dedup into actual log

    def _get_reset_path(self, user):
        return reverse(
            'accounts:password_reset_confirm',
            kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            },
        )

    def context(self, user):
        if not settings.SITE_URL:
            raise ImproperlyConfigured(
                'SITE_URL must be set: a password reset email needs it for the link.'
            )

        return {
            'reset_path': self._get_reset_path(user),
            'valid_hours': settings.PASSWORD_RESET_TIMEOUT // 3600,
        }
