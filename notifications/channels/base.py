from abc import ABC, abstractmethod


class BaseNotificationChannel(ABC):
    key = None

    @abstractmethod
    def is_enabled(self): ...

    @abstractmethod
    def deliver(self, *, user, event, context): ...
