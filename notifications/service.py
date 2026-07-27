from .channels.email import EmailChannel
from .models import NotificationEvent, NotificationLog


class NotificationService:
    channel_classes = [EmailChannel]
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.channels = {cls.key: cls() for cls in self.channel_classes}
        self._initialized = True

    def notify(self, user, event, context=None, *, channels=None, dedup_key=""):
        context = context or {}
        event = NotificationEvent(event)

        for channel_key in channels or self.channels:
            channel = self.channels[channel_key]

            if not channel.is_enabled():
                # TODO: Log skip
                continue

            if not channel.is_enabled_for_user(user):
                # TODO: Log skip
                continue

            log = None

            if dedup_key:
                log, created = NotificationLog.objects.get_or_create(
                    user=user,
                    event=event.value,
                    channel=channel_key,
                    dedup_key=dedup_key,
                )

                if not created:
                    continue

            try:
                channel.deliver(user=user, event=event.value, context=context)
            except Exception:
                if log is not None:
                    log.delete()
                raise


notification_service = NotificationService()
