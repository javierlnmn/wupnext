class NotificationError(Exception):
    pass


class MissingRecipient(NotificationError):
    pass


class MissingPreview(NotificationError):
    pass
