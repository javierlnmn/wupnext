from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule
from django_q.scheduler import scheduler

from tasks.management.commands._periodic import PeriodicScheduleCommand


class ConfiguredHost(PeriodicScheduleCommand):
    schedule_name = 'host-schedule'
    func = 'tasks.jobs.send_due_reminders'

    def schedule_defaults(self):
        return {'schedule_type': Schedule.DAILY, 'next_run': timezone.now()}


class NamelessHost(ConfiguredHost):
    schedule_name = None


class FunclessHost(ConfiguredHost):
    func = None


class PeriodicScheduleCommandTests(TestCase):
    def host(self, host_cls):
        return host_cls(stdout=StringIO())

    def test_requires_schedule_name(self):
        with self.assertRaises(ImproperlyConfigured):
            self.host(NamelessHost).handle()

    def test_requires_func(self):
        with self.assertRaises(ImproperlyConfigured):
            self.host(FunclessHost).handle()

    def test_creates_then_updates_without_duplicating(self):
        self.host(ConfiguredHost).handle()
        self.host(ConfiguredHost).handle()

        self.assertEqual(Schedule.objects.filter(name='host-schedule').count(), 1)


class ScheduleDueRemindersCommandTests(TestCase):
    def call(self):
        call_command('schedule_due_reminders', stdout=StringIO())

    def test_registers_daily_schedule_for_the_reminder_job(self):
        self.call()

        schedule = Schedule.objects.get(name='due-reminders')
        self.assertEqual(schedule.func, 'tasks.jobs.send_due_reminders')
        self.assertEqual(schedule.schedule_type, Schedule.DAILY)

    def test_next_run_is_the_upcoming_seven_am(self):
        self.call()

        next_run = Schedule.objects.get(name='due-reminders').next_run
        self.assertEqual(next_run.hour, 7)
        self.assertGreater(next_run, timezone.now())
        self.assertLessEqual(next_run, timezone.now() + timedelta(days=1))

    def test_is_idempotent(self):
        self.call()
        self.call()

        self.assertEqual(Schedule.objects.filter(name='due-reminders').count(), 1)

    def test_firing_the_schedule_runs_the_reminder_job(self):
        self.call()
        Schedule.objects.filter(name='due-reminders').update(
            next_run=timezone.now() - timedelta(minutes=1)
        )

        with (
            self.assertLogs('django-q', level='INFO'),
            mock.patch('django_q.conf.Conf.SYNC', True),
            mock.patch('tasks.jobs.send_due_reminders', return_value=None) as job,
        ):
            scheduler()

        job.assert_called_once()
