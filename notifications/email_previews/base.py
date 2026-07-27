from abc import ABC, abstractmethod
from contextlib import contextmanager

from django.core.mail import get_connection
from django.db import transaction

from ..channels.email import EmailChannel

PREVIEW_USERNAME = "preview"
PREVIEW_EMAIL = "preview@wupnext.invalid"
LIVE_EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"


class BaseEmailPreview(ABC):
    event = None
    user = None

    @abstractmethod
    def _seed(self): ...

    @abstractmethod
    def _get_notification_context(self): ...

    @contextmanager
    def _seeded_context(self):
        with transaction.atomic():
            self._seed()
            yield self._get_notification_context()
            transaction.set_rollback(True)

    def render(self):
        with self._seeded_context() as context:
            return EmailChannel().render(self.event, context)

    def send(self, recipient):
        subject, body, html = self.render()
        message = EmailChannel().build_message(subject, body, html, [recipient])
        message.connection = get_connection(LIVE_EMAIL_BACKEND)
        message.send()
        return subject, body, html
