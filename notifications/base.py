import logging
from abc import ABC, abstractmethod

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

from .service import notification_service

logger = logging.getLogger(__name__)


class BaseNotification(ABC):
    event = None

    @abstractmethod
    def _is_enabled_on_site(self): ...

    # TODO: Implement specific per-notification preference
    @abstractmethod
    def _is_enabled_for_user(self, user): ...

    @abstractmethod
    def _dedup_key(self, user, context): ...

    def _recipients(self):
        return get_user_model().objects.filter(is_active=True)

    @abstractmethod
    def context(self, user): ...

    def send(self):
        if not self.event:
            raise ImproperlyConfigured(f"{type(self).__name__} must set 'event'.")

        if not self._is_enabled_on_site():
            # TODO: Log skip
            return

        for user in self._recipients():
            if not self._is_enabled_for_user(user):
                # TODO: Log skip
                continue

            context = self.context(user)

            try:
                notification_service.notify(
                    user,
                    self.event,
                    context=context,
                    dedup_key=self._dedup_key(user, context),
                )
            except Exception:
                logger.exception("Failed to send %s to %s", self.event, user)
