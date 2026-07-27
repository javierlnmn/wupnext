from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from common.models import SiteSettings

from ..exceptions import MissingRecipient
from ..models import Channel
from .base import BaseNotificationChannel


class EmailChannel(BaseNotificationChannel):
    key = Channel.EMAIL

    def is_enabled(self):
        return SiteSettings.load().notification_channels_email_enabled

    def recipient(self, user):
        return user.email or None

    def render(self, event, context):
        ctx = {"site_url": settings.SITE_URL, **context}
        subject = render_to_string(
            f"notifications/{event}/email_subject.txt", ctx
        ).strip()
        body = render_to_string(f"notifications/{event}/email_body.txt", ctx)

        try:
            html = render_to_string(f"notifications/{event}/email_body.html", ctx)
        except TemplateDoesNotExist:
            html = None

        return subject, body, html

    def build_message(self, subject, body, html, to):
        message = EmailMultiAlternatives(subject=subject, body=body, to=to)
        if html:
            message.attach_alternative(html, "text/html")
        return message

    def deliver(self, *, user, event, context):
        recipient = self.recipient(user)
        if not recipient:
            raise MissingRecipient(f"No email address for {user}")

        subject, body, html = self.render(event, {**context, "user": user})
        self.build_message(subject, body, html, [recipient]).send()
