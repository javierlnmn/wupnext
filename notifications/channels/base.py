class BaseChannel:
    key = None

    def is_enabled(self, user):
        return True

    def deliver(self, *, user, event, context):
        raise NotImplementedError
