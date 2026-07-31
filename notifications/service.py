import logging

from django_q.tasks import async_task

from .base import BaseBulkNotification
from .channels.registry import get_channel
from .exceptions import NotBulkNotification
from .models import (
    NotificationEventSwitch,
    NotificationLog,
    NotificationUserPreference,
)
from .registry import get_notification_path

logger = logging.getLogger(__name__)

FANOUT_JOB = 'notifications.jobs.send_notification_to_user'


class NotificationService:
    def __init__(self, notification):
        self.notification = notification
        self.event = notification.event
        self.channels = notification.channels

    def _get_enabled_channels_defaults(self):
        enabled = NotificationEventSwitch.get_enabled_channels_defaults_for_event(
            self.event
        )

        return {
            channel: on_by_default
            for channel, on_by_default in enabled.items()
            if channel in self.channels
        }

    def _get_enabled_channels_for_user_preferences(
        self, channel_defaults, user_stored_preferences
    ):
        return [
            channel
            for channel, on_by_default in channel_defaults.items()
            if user_stored_preferences.get(channel, on_by_default)
        ]

    def _get_delivery_channels_for_user(self, user):
        channel_defaults = self._get_enabled_channels_defaults()

        if not channel_defaults:
            return []

        stored = NotificationUserPreference.get_user_stored_preferences_for_event(
            user, self.event, channel_defaults
        )

        return self._get_enabled_channels_for_user_preferences(channel_defaults, stored)

    def _get_delivery_channels_by_user(self, users):
        channel_defaults = self._get_enabled_channels_defaults()

        if not channel_defaults:
            return {}

        users = list(users)
        stored = NotificationUserPreference.get_bulk_user_stored_preferences_for_event(
            users, self.event, channel_defaults
        )
        deliveries = {}

        for user in users:
            enabled_channels = self._get_enabled_channels_for_user_preferences(
                channel_defaults, stored.get(user.pk, {})
            )

            if enabled_channels:
                deliveries[user] = enabled_channels

        return deliveries

    def _get_notification_deliveries(self):
        if not isinstance(self.notification, BaseBulkNotification):
            raise NotBulkNotification(
                f'{type(self.notification).__name__} declares no recipients, '
                'so it can only be sent to one user at a time.'
            )

        return self._get_delivery_channels_by_user(self.notification.recipients())

    def _get_notification_class_path(self):
        return get_notification_path(type(self.notification))

    def _deliver(self, user, channels):
        context = self.notification.context(user)

        if not self.notification.is_applicable_for(user, context):
            # TODO: Log skip
            return

        self.notify(
            user,
            channels=channels,
            context=context,
            dedup_key=self.notification.dedup_key(user, context),
        )

    def send(self, user):
        channels = self._get_delivery_channels_for_user(user)

        if not channels:
            # TODO: Log skip
            return

        self._deliver(user, channels)

    def send_bulk(self):
        for user, channels in self._get_notification_deliveries().items():
            try:
                self._deliver(user, channels)
            except Exception:
                logger.exception('Failed to send %s to %s', self.event, user)

    def enqueue_bulk(self):
        notification_class_path = self._get_notification_class_path()

        for user in self._get_notification_deliveries():
            async_task(FANOUT_JOB, notification_class_path, user.pk)

    def notify(self, user, *, channels, context=None, dedup_key=''):
        context = context or {}
        resolved = {key: get_channel(key) for key in channels}

        for channel_key, channel in resolved.items():
            log = None

            if dedup_key:
                log, created = NotificationLog.objects.get_or_create(
                    user=user,
                    event=self.event,
                    channel=channel_key,
                    dedup_key=dedup_key,
                )

                if not created:
                    continue

            try:
                channel.deliver(user=user, event=self.event, context=context)
            except Exception:
                if log is not None:
                    log.delete()
                raise
