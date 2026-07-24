class BaseChannel:
    key = None

    def is_enabled(self):
        raise NotImplementedError

    def deliver(self, *, user, event, context):
        raise NotImplementedError
