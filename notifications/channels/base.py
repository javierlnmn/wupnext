from abc import ABC, abstractmethod

from ..models import NotificationChannelSwitch


class BaseNotificationChannel(ABC):
    key = None

    def is_enabled(self):
        return NotificationChannelSwitch.is_enabled(self.key)

    @abstractmethod
    def deliver(self, *, user, event, context): ...
