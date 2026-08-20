from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule
from django_q.scheduler import scheduler

from notifications.management.commands.sync_notification_schedules import (
    ENQUEUE_JOB,
    NAME_PREFIX,
)
from notifications.registry import NOTIFICATIONS, get_notification_path
from tasks.notifications.notifications.due_reminders import DueReminderNotification

EVENT = 'task_due_reminder'
SCHEDULE_NAME = f'{NAME_PREFIX}{EVENT}'
PATH = get_notification_path(DueReminderNotification)


class SyncNotificationSchedulesTests(TestCase):
    def run_command(self):
        out = StringIO()
        call_command('sync_notification_schedules', stdout=out)
        return out.getvalue()

    def schedule(self):
        return Schedule.objects.get(name=SCHEDULE_NAME)

    def test_creates_a_cron_schedule_for_a_declaring_notification(self):
        output = self.run_command()

        schedule = self.schedule()
        self.assertEqual(schedule.schedule_type, Schedule.CRON)
        self.assertEqual(schedule.cron, DueReminderNotification.schedule)
        self.assertEqual(schedule.func, ENQUEUE_JOB)
        self.assertEqual(schedule.repeats, -1)
        self.assertIn(SCHEDULE_NAME, output)

    def test_passes_the_notification_path_as_the_only_argument(self):
        self.run_command()

        self.assertEqual(self.schedule().args, repr(PATH))

    def test_next_run_comes_from_the_cron_expression(self):
        self.run_command()

        next_run = self.schedule().next_run
        self.assertEqual((next_run.hour, next_run.minute), (7, 0))
        self.assertGreater(next_run, timezone.now())

    def test_only_declaring_notifications_get_a_schedule(self):
        self.run_command()

        declared = {
            f'{NAME_PREFIX}{event}'
            for event, notification in NOTIFICATIONS.items()
            if getattr(notification, 'schedule', '')
        }
        self.assertEqual(set(Schedule.objects.values_list('name', flat=True)), declared)

    def test_is_idempotent(self):
        self.run_command()
        self.run_command()

        self.assertEqual(Schedule.objects.filter(name=SCHEDULE_NAME).count(), 1)

    def test_a_changed_cron_is_applied_and_next_run_recomputed(self):
        self.run_command()
        Schedule.objects.filter(name=SCHEDULE_NAME).update(
            cron='0 3 * * *', next_run=timezone.now() + timedelta(days=400)
        )

        self.run_command()

        schedule = self.schedule()
        self.assertEqual(schedule.cron, DueReminderNotification.schedule)
        self.assertEqual(schedule.next_run.hour, 7)

    def test_removes_a_schedule_that_is_no_longer_declared(self):
        Schedule.objects.create(
            name=f'{NAME_PREFIX}retired_event',
            func=ENQUEUE_JOB,
            schedule_type=Schedule.DAILY,
        )

        output = self.run_command()

        self.assertFalse(
            Schedule.objects.filter(name=f'{NAME_PREFIX}retired_event').exists()
        )
        self.assertIn('no longer declared', output)

    def test_leaves_schedules_it_does_not_manage_alone(self):
        Schedule.objects.create(
            name='some-other-job',
            func='tasks.something.else',
            schedule_type=Schedule.DAILY,
        )

        self.run_command()

        self.assertTrue(Schedule.objects.filter(name='some-other-job').exists())


class ScheduleFiringTests(TestCase):
    def test_firing_the_schedule_enqueues_that_notification(self):
        call_command('sync_notification_schedules', stdout=StringIO())
        Schedule.objects.filter(name=SCHEDULE_NAME).update(
            next_run=timezone.now() - timedelta(minutes=1)
        )

        with (
            self.assertLogs('django-q', level='INFO'),
            mock.patch('django_q.conf.Conf.SYNC', True),
            mock.patch(
                'notifications.jobs.enqueue_bulk_notification', return_value=None
            ) as job,
        ):
            scheduler()

        job.assert_called_once_with(PATH)

    def test_the_schedule_is_rescheduled_rather_than_consumed(self):
        call_command('sync_notification_schedules', stdout=StringIO())
        Schedule.objects.filter(name=SCHEDULE_NAME).update(
            next_run=timezone.now() - timedelta(minutes=1)
        )

        with (
            self.assertLogs('django-q', level='INFO'),
            mock.patch('django_q.conf.Conf.SYNC', True),
            mock.patch(
                'notifications.jobs.enqueue_bulk_notification', return_value=None
            ),
        ):
            scheduler()

        schedule = Schedule.objects.get(name=SCHEDULE_NAME)
        self.assertGreater(schedule.next_run, timezone.now())
        self.assertEqual(schedule.repeats, -1)
