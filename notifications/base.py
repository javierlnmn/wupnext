import logging
from abc import ABC, abstractmethod

from django_q.tasks import async_task

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
    def _is_applicable_for_user(self, user, context): ...

    @abstractmethod
    def _dedup_key(self, user, context): ...

    @abstractmethod
    def context(self, user): ...

    def send_to(self, user):
        if not self._is_enabled_on_site():
            # TODO: Log skip
            return

        if not self._is_enabled_for_user(user):
            # TODO: Log skip
            return

        context = self.context(user)

        if not self._is_applicable_for_user(user, context):
            # TODO: Log skip
            return

        notification_service.notify(
            user,
            self.event,
            context=context,
            dedup_key=self._dedup_key(user, context),
        )


class BaseBulkNotification(BaseNotification):
    FANOUT_JOB = 'notifications.jobs.send_notification_to_user'

    @abstractmethod
    def _recipients(self): ...

    def _path(self):
        cls = type(self)
        return f'{cls.__module__}.{cls.__qualname__}'

    def send(self):
        for user in self._recipients():
            try:
                self.send_to(user)
            except Exception:
                logger.exception('Failed to send %s to %s', self.event, user)

    def enqueue(self):
        if not self._is_enabled_on_site():
            # TODO: Log skip
            return

        for user in self._recipients():
            if not self._is_enabled_for_user(user):
                # TODO: Log skip
                continue

            async_task(self.FANOUT_JOB, self._path(), user.pk)
