from django.core.management.base import BaseCommand

from notifications.models import (
    Channel,
    NotificationChannelSwitch,
    NotificationEventSwitch,
)
from notifications.registry import NOTIFICATIONS


class Command(BaseCommand):
    help = (
        'Create a switch row for every registered optional notification and '
        'channel, so they can be turned on in the admin. New rows arrive '
        'disabled. Rows left behind by a removed notification, or by one that '
        'stopped being optional, are reported, never deleted.'
    )

    def handle(self, *args, **options):
        expected = {
            (event, channel)
            for event, notification in NOTIFICATIONS.items()
            if notification.optional
            for channel in notification.channels
        }

        created = self._create_missing(expected)
        orphaned = self._orphaned(expected)

        if created:
            self._write(
                'Created, disabled',
                created,
                'Enable what you want in the admin before it sends.',
            )

        if orphaned:
            self._write(
                'No longer registered',
                orphaned,
                'Delete these in the admin if the notification is gone for good.',
            )

        if not created and not orphaned:
            self.stdout.write('Already in sync.')

    def _create_missing(self, expected):
        created = []

        for channel in Channel.values:
            _, is_new = NotificationChannelSwitch.objects.get_or_create(channel=channel)
            if is_new:
                created.append(f'channel {channel}')

        for event, channel in sorted(expected):
            _, is_new = NotificationEventSwitch.objects.get_or_create(
                event=event, channel=channel
            )
            if is_new:
                created.append(f'{event} → {channel}')

        return created

    def _orphaned(self, expected):
        return [
            f'{event} → {channel}'
            for event, channel in NotificationEventSwitch.objects.values_list(
                'event', 'channel'
            )
            if (event, channel) not in expected
        ]

    def _write(self, heading, labels, footer):
        self.stdout.write(self.style.MIGRATE_HEADING(heading))
        for label in labels:
            self.stdout.write(f'  {label}')
        self.stdout.write(self.style.WARNING(footer))
