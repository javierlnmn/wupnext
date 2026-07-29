from .channels.registry import get_channel
from .models import (
    NotificationEventSwitch,
    NotificationLog,
    NotificationUserPreference,
)


class NotificationService:
    @classmethod
    def notify(cls, user, event, *, channels, context=None, dedup_key=''):
        context = context or {}

        for channel_key in channels:
            channel = get_channel(channel_key)

            if not channel.is_enabled():
                # TODO: Log skip
                continue

            if not NotificationEventSwitch.is_enabled_for_channel(event, channel_key):
                # TODO: Log skip
                continue

            if not NotificationUserPreference.is_enabled_for_channel(
                user, event, channel_key
            ):
                # TODO: Log skip
                continue

            log = None

            if dedup_key:
                log, created = NotificationLog.objects.get_or_create(
                    user=user,
                    event=event,
                    channel=channel_key,
                    dedup_key=dedup_key,
                )

                if not created:
                    continue

            try:
                channel.deliver(user=user, event=event, context=context)
            except Exception:
                if log is not None:
                    log.delete()
                raise
