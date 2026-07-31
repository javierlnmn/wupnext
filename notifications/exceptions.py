class NotificationError(Exception):
    pass


class MissingRecipient(NotificationError):
    pass


class MissingPreview(NotificationError):
    pass


class DuplicateNotification(NotificationError):
    pass


class UnknownChannel(NotificationError):
    pass


class NotBulkNotification(NotificationError):
    pass
