import logging
from abc import ABC, abstractmethod

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

from accounts.models import UserPreferences

from .service import notification_service

logger = logging.getLogger(__name__)


class BaseNotification(ABC):
    event = None

    def is_enabled(self):
        return True

    def is_enabled_for(self, user):
        return UserPreferences.for_user(user).notification_channels_email_enabled

    def recipients(self):
        return get_user_model().objects.filter(is_active=True)

    @abstractmethod
    def context(self, user): ...

    def dedup_key(self, user, context):
        return ""

    def send(self):
        if not self.event:
            raise ImproperlyConfigured(f"{type(self).__name__} must set 'event'.")

        if not self.is_enabled():
            return

        for user in self.recipients():
            context = self.context(user)
            if context is None or not self.is_enabled_for(user):
                continue

            try:
                notification_service.notify(
                    user,
                    self.event,
                    context=context,
                    dedup_key=self.dedup_key(user, context),
                )
            except Exception:
                logger.exception("Failed to send %s to %s", self.event, user)
