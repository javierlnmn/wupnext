from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from common.models import SiteSettings

from ..exceptions import MissingRecipient
from ..models import Channel
from .base import BaseChannel


class EmailChannel(BaseChannel):
    key = Channel.EMAIL

    def is_enabled(self, user):
        return SiteSettings.load().email_notifications_enabled

    def recipient(self, user):
        return user.email or None

    def deliver(self, *, user, event, context):
        recipient = self.recipient(user)
        if not recipient:
            raise MissingRecipient(f"No email address for {user}")

        ctx = {**context, "user": user}
        subject = render_to_string(
            f"notifications/{event}/email_subject.txt", ctx
        ).strip()
        body = render_to_string(f"notifications/{event}/email_body.txt", ctx)
        message = EmailMultiAlternatives(subject=subject, body=body, to=[recipient])

        try:
            html = render_to_string(f"notifications/{event}/email_body.html", ctx)
        except TemplateDoesNotExist:
            html = None

        if html:
            message.attach_alternative(html, "text/html")
        message.send()
