from abc import ABC, abstractmethod


class BaseNotification(ABC):
    event = None
    label = ''
    description = ''
    channels = ()
    optional = True

    @abstractmethod
    def context(self, user): ...

    @abstractmethod
    def is_applicable_for(self, user, context): ...

    def dedup_key(self, user, context):
        return None


class BaseBulkNotification(BaseNotification):
    schedule = ''

    @abstractmethod
    def recipients(self): ...
