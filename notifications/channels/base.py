from abc import ABC, abstractmethod


class BaseNotificationChannel(ABC):
    key = None

    def is_available(self):
        return True

    @abstractmethod
    def deliver(self, *, user, event, context): ...
