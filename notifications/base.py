from abc import ABC, abstractmethod


class BaseNotification(ABC):
    event = None
    label = ''
    description = ''
    channels = ()

    @abstractmethod
    def context(self, user): ...

    @abstractmethod
    def is_applicable_for(self, user, context): ...

    @abstractmethod
    def dedup_key(self, user, context): ...


class BaseBulkNotification(BaseNotification):
    schedule = ''

    @abstractmethod
    def recipients(self): ...
