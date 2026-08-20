from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.urls import reverse

from ..exceptions import MissingRecipient
from ..models import Channel
from ..registry import NOTIFICATIONS
from .base import BaseNotificationChannel

# Namespaces the signature so a token minted here cannot be replayed against
# anything else signed in this project. The view unsigns with the same salt.
UNSUBSCRIBE_SALT = 'notifications.unsubscribe'


def has_resend_api_key():
    return bool(settings.ANYMAIL.get('RESEND_API_KEY'))


class EmailChannel(BaseNotificationChannel):
    key = Channel.EMAIL

    def is_available(self):
        if settings.EMAIL_BACKEND != settings.LIVE_EMAIL_BACKEND:
            return True

        return has_resend_api_key()

    def _get_unsubscribe_token(self, event, user):
        notification = NOTIFICATIONS.get(event)

        if notification is None or not notification.optional:
            return None

        if user is None or user.pk is None or not settings.SITE_URL:
            return None

        return signing.dumps(
            {'user': user.pk, 'event': event, 'channel': self.key},
            salt=UNSUBSCRIBE_SALT,
        )

    def _build_unsubscribe_url(self, url_name, token):
        path = reverse(url_name, kwargs={'token': token})

        return f'{settings.SITE_URL}{path}'

    def _get_unsubscribe_url(self, event, user):
        token = self._get_unsubscribe_token(event, user)

        if token is None:
            return None

        return self._build_unsubscribe_url('notifications:unsubscribe', token)

    def _get_unsubscribe_headers(self, event, user):
        token = self._get_unsubscribe_token(event, user)

        if token is None:
            return None

        url = self._build_unsubscribe_url('notifications:unsubscribe-one-click', token)

        return {
            'List-Unsubscribe': f'<{url}>',
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
        }

    def _get_preferences_url(self):
        if not settings.SITE_URL:
            return None

        path = reverse('tasks:board')

        return f'{settings.SITE_URL}{path}?preferences=notifications'

    def render(self, event, context):
        ctx = {
            'site_url': settings.SITE_URL,
            'preferences_url': self._get_preferences_url(),
            'unsubscribe_url': self._get_unsubscribe_url(event, context.get('user')),
            **context,
        }
        subject = render_to_string(
            f'notifications/{event}/email_subject.txt', ctx
        ).strip()
        body = render_to_string(f'notifications/{event}/email_body.txt', ctx)

        try:
            html = render_to_string(f'notifications/{event}/email_body.html', ctx)
        except TemplateDoesNotExist:
            html = None

        return subject, body, html

    def build_message(self, subject, body, html, to, headers=None):
        message = EmailMultiAlternatives(
            subject=subject, body=body, to=to, headers=headers
        )
        if html:
            message.attach_alternative(html, 'text/html')
        return message

    def deliver(self, *, user, event, context):
        recipient = user.email
        if not recipient:
            raise MissingRecipient(f'No email address for {user}')

        subject, body, html = self.render(event, {**context, 'user': user})
        self.build_message(
            subject,
            body,
            html,
            [recipient],
            headers=self._get_unsubscribe_headers(event, user),
        ).send()
