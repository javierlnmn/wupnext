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

SKIP_DISABLED_ON_SITE = 'no channel is enabled on site for this event'
SKIP_NO_CHANNEL_DECLARED = 'the notification declares no channel'
SKIP_USER_OPTED_OUT = 'the user opted out of every enabled channel'
SKIP_NOT_APPLICABLE = 'the notification had nothing to say for this user'
SKIP_ALREADY_SENT = 'it already went out under the same dedup key'


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

    def _log_skip(self, user, reason, channel=None):
        # user.pk, never the user: __str__ puts their name in the log file.
        logger.info(
            'Skipped %s for user %s%s: %s',
            self.event,
            user.pk,
            f' on {channel}' if channel else '',
            reason,
        )

    def _get_delivery_channels_for_user(self, user):
        channel_defaults = self._get_enabled_channels_defaults()

        if not channel_defaults:
            self._log_skip(user, SKIP_DISABLED_ON_SITE)
            return []

        stored = NotificationUserPreference.get_user_stored_preferences_for_event(
            user, self.event, channel_defaults
        )
        channels = self._get_enabled_channels_for_user_preferences(
            channel_defaults, stored
        )

        if not channels:
            self._log_skip(user, SKIP_USER_OPTED_OUT)

        return channels

    def _get_delivery_channels_by_user(self, users):
        channel_defaults = self._get_enabled_channels_defaults()

        if not channel_defaults:
            logger.info(
                'Skipped %s for every recipient: %s',
                self.event,
                SKIP_DISABLED_ON_SITE,
            )
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

            if not enabled_channels:
                self._log_skip(user, SKIP_USER_OPTED_OUT)
                continue

            deliveries[user] = enabled_channels

        return deliveries

    def _get_notification_deliveries(self):
        if not isinstance(self.notification, BaseBulkNotification):
            raise NotBulkNotification(
                f'{type(self.notification).__name__} declares no recipients, '
                'so it can only be sent to one user at a time.'
            )

        recipients = self.notification.recipients()

        if not self.notification.optional:
            return {user: list(self.channels) for user in recipients}

        return self._get_delivery_channels_by_user(recipients)

    def _get_notification_class_path(self):
        return get_notification_path(type(self.notification))

    def _deliver(self, user, channels):
        context = self.notification.context(user)

        if not self.notification.is_applicable_for(user, context):
            self._log_skip(user, SKIP_NOT_APPLICABLE)
            return

        self.notify(
            user,
            channels=channels,
            context=context,
            dedup_key=self.notification.dedup_key(user, context),
        )

    def send(self, user):
        channels = (
            self._get_delivery_channels_for_user(user)
            if self.notification.optional
            else list(self.channels)
        )

        if not channels:
            if not self.notification.optional:
                self._log_skip(user, SKIP_NO_CHANNEL_DECLARED)

            return

        self._deliver(user, channels)

    def send_bulk(self):
        for user, channels in self._get_notification_deliveries().items():
            try:
                self._deliver(user, channels)
            except Exception:
                logger.exception('Failed to send %s to user %s', self.event, user.pk)

    def enqueue_bulk(self):
        notification_class_path = self._get_notification_class_path()

        for user in self._get_notification_deliveries():
            async_task(FANOUT_JOB, notification_class_path, user.pk)

    def notify(self, user, *, channels, context=None, dedup_key=None):
        context = context or {}
        resolved = {key: get_channel(key) for key in channels}

        for channel_key, channel in resolved.items():
            log, to_be_sent = self._check_dedup_logs(user, channel_key, dedup_key)

            if not to_be_sent:
                self._log_skip(user, SKIP_ALREADY_SENT, channel=channel_key)
                continue

            try:
                channel.deliver(user=user, event=self.event, context=context)
            except Exception:
                log.delete()
                raise

    def _check_dedup_logs(self, user, channel_key, dedup_key):
        row = {'user': user, 'event': self.event, 'channel': channel_key}

        if not dedup_key:
            return NotificationLog.objects.create(**row, dedup_key=None), True

        return NotificationLog.objects.get_or_create(**row, dedup_key=dedup_key)
