from .exceptions import DuplicateNotification

NOTIFICATIONS = {}


def register(notification_class):
    event = notification_class.event

    if not event:
        raise ValueError(f'{notification_class.__name__} declares no event.')

    registered = NOTIFICATIONS.get(event)
    if registered is not None and registered is not notification_class:
        raise DuplicateNotification(
            f"'{event}' is already registered by {registered.__name__}."
        )

    NOTIFICATIONS[event] = notification_class
    return notification_class
