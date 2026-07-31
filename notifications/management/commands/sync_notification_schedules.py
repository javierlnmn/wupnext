from django.core.management.base import BaseCommand
from django_q.models import Schedule

from notifications.base import BaseBulkNotification
from notifications.exceptions import NotBulkNotification
from notifications.registry import NOTIFICATIONS, get_notification_path

ENQUEUE_JOB = 'notifications.jobs.enqueue_bulk_notification'
NAME_PREFIX = 'notification-'


class Command(BaseCommand):
    help = (
        'Load the cron schedule each notification declares into Django Q. '
        'Idempotent, so run it on every deploy. Schedules for notifications that '
        'no longer declare one are deleted, since an orphan would keep firing.'
    )

    def handle(self, *args, **options):
        synced = self._sync_declared_schedules()
        removed = self._remove_orphans(synced)

        if synced:
            self._write('Scheduled', synced)

        if removed:
            self._write('Removed, no longer declared', removed)

        if not synced and not removed:
            self.stdout.write('No notification declares a schedule.')

    def _sync_declared_schedules(self):
        names = []

        for event, notification in NOTIFICATIONS.items():
            cron = getattr(notification, 'schedule', '')

            if not cron:
                continue

            if not issubclass(notification, BaseBulkNotification):
                raise NotBulkNotification(
                    f'{notification.__name__} declares a schedule but no '
                    'recipients. Only a bulk notification can be scheduled.'
                )

            name = f'{NAME_PREFIX}{event}'
            Schedule.objects.update_or_create(
                name=name,
                defaults={
                    'func': ENQUEUE_JOB,
                    'args': repr(get_notification_path(notification)),
                    'schedule_type': Schedule.CRON,
                    'cron': cron,
                    'next_run': self._get_next_run(cron),
                    'repeats': -1,
                },
            )
            names.append(f'{name} ({cron})')

        return names

    def _remove_orphans(self, synced):
        expected = {entry.split(' ')[0] for entry in synced}
        orphans = Schedule.objects.filter(name__startswith=NAME_PREFIX).exclude(
            name__in=expected
        )
        names = list(orphans.values_list('name', flat=True))
        orphans.delete()

        return names

    def _get_next_run(self, cron):
        return Schedule(schedule_type=Schedule.CRON, cron=cron).calculate_next_run()

    def _write(self, heading, entries):
        self.stdout.write(self.style.MIGRATE_HEADING(heading))
        for entry in entries:
            self.stdout.write(f'  {entry}')
