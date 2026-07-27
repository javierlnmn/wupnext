from abc import ABC, abstractmethod


class BaseNotificationChannel(ABC):
    key = None

    @abstractmethod
    def is_enabled(self): ...

    @abstractmethod
    def is_enabled_for_user(self, user): ...

    @abstractmethod
    def deliver(self, *, user, event, context): ...
