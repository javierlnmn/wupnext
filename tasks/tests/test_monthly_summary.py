from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.models import Channel, NotificationLog
from notifications.service import NotificationService
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)
from tasks.notifications.notifications.monthly_summary import MonthlySummaryNotification
from tasks.tests.factories import GroupFactory, TaskFactory

EVENT = 'task_monthly_summary'


def last_month_end():
    return timezone.localdate().replace(day=1) - timedelta(days=1)


def complete_on(task, day):
    task.completed_at = timezone.make_aware(
        timezone.datetime(day.year, day.month, day.day, 12)
    )
    task.save(update_fields=['completed_at'])
    return task


class PeriodTests(TestCase):
    def setUp(self):
        self.notification = MonthlySummaryNotification()

    def test_the_period_is_the_previous_calendar_month(self):
        start, end = self.notification._get_period()

        self.assertEqual(end, last_month_end())
        self.assertEqual(start, end.replace(day=1))
        self.assertEqual(start.month, end.month)

    def test_dedup_key_is_the_reported_month(self):
        context = self.notification.context(UserFactory())
        start = context['period_start']

        self.assertEqual(self.notification.dedup_key(None, context), f'{start:%Y-%m}')

    def test_does_not_apply_when_every_section_is_empty(self):
        user = UserFactory()

        context = self.notification.context(user)

        self.assertFalse(self.notification.is_applicable_for(user, context))


class BucketingTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.notification = MonthlySummaryNotification()
        self.end = last_month_end()
        self.today = timezone.localdate()

    def context(self):
        return self.notification.context(self.user)

    def test_a_task_completed_in_the_period_is_reported(self):
        complete_on(TaskFactory(user=self.user, name='Done'), self.end)

        completed = self.context()['completed']

        self.assertEqual([entry['task'].name for entry in completed], ['Done'])

    def test_a_task_completed_before_the_period_is_dropped(self):
        complete_on(
            TaskFactory(user=self.user, name='Ancient'),
            self.end.replace(day=1) - timedelta(days=1),
        )

        context = self.context()

        self.assertEqual(context['completed'], [])
        self.assertEqual(context['pending'], [])
        self.assertEqual(context['overdue'], [])

    def test_a_task_completed_this_month_is_dropped(self):
        complete_on(TaskFactory(user=self.user, name='Recent'), self.today)

        self.assertEqual(self.context()['completed'], [])

    def test_an_open_task_past_its_due_date_is_overdue(self):
        TaskFactory(
            user=self.user, name='Late', due_date=self.today - timedelta(days=1)
        )

        context = self.context()

        self.assertEqual([task.name for task in context['overdue']], ['Late'])
        self.assertEqual(context['pending'], [])

    def test_an_open_task_due_later_is_pending(self):
        TaskFactory(
            user=self.user, name='Soon', due_date=self.today + timedelta(days=1)
        )

        self.assertEqual([task.name for task in self.context()['pending']], ['Soon'])

    def test_an_open_task_due_today_is_pending(self):
        TaskFactory(user=self.user, name='Today', due_date=self.today)

        self.assertEqual([task.name for task in self.context()['pending']], ['Today'])

    def test_an_open_task_without_a_due_date_is_pending(self):
        TaskFactory(user=self.user, name='Someday')

        self.assertEqual([task.name for task in self.context()['pending']], ['Someday'])

    def test_ignores_archived_tasks_and_subtasks(self):
        parent = TaskFactory(user=self.user, name='Parent')
        TaskFactory(user=self.user, name='Subtask', parent=parent)
        TaskFactory(user=self.user, name='Archived', archived=True)

        self.assertEqual([task.name for task in self.context()['pending']], ['Parent'])

    def test_ignores_another_users_tasks(self):
        TaskFactory(user=UserFactory(), name='Theirs')

        self.assertEqual(self.context()['pending'], [])

    def test_sums_the_weight_of_completed_work(self):
        complete_on(TaskFactory(user=self.user, weight=5), self.end)
        complete_on(TaskFactory(user=self.user, weight=3), self.end)
        TaskFactory(user=self.user, weight=99)

        self.assertEqual(self.context()['completed_weight'], 8)

    def test_orders_pending_by_due_date_with_undated_last(self):
        TaskFactory(user=self.user, name='Undated')
        TaskFactory(
            user=self.user, name='Later', due_date=self.today + timedelta(days=9)
        )
        TaskFactory(
            user=self.user, name='Sooner', due_date=self.today + timedelta(days=2)
        )

        self.assertEqual(
            [task.name for task in self.context()['pending']],
            ['Sooner', 'Later', 'Undated'],
        )


class CompletionVerdictTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.notification = MonthlySummaryNotification()
        self.end = last_month_end()

    def entry(self):
        return self.notification.context(self.user)['completed'][0]

    def finish(self, due_date, finished):
        complete_on(TaskFactory(user=self.user, due_date=due_date), finished)

    def test_finished_on_the_target_day(self):
        self.finish(due_date=self.end, finished=self.end)

        entry = self.entry()
        self.assertTrue(entry['on_time'])
        self.assertEqual(entry['days'], 0)

    def test_finished_early(self):
        self.finish(due_date=self.end, finished=self.end - timedelta(days=3))

        entry = self.entry()
        self.assertTrue(entry['on_time'])
        self.assertEqual(entry['days'], 3)

    def test_finished_late(self):
        self.finish(due_date=self.end - timedelta(days=4), finished=self.end)

        entry = self.entry()
        self.assertFalse(entry['on_time'])
        self.assertEqual(entry['days'], 4)

    def test_no_target_means_no_verdict(self):
        self.finish(due_date=None, finished=self.end)

        entry = self.entry()
        self.assertIsNone(entry['on_time'])
        self.assertIsNone(entry['days'])
        self.assertIsNone(entry['target'])


class RecipientTests(TestCase):
    def setUp(self):
        self.notification = MonthlySummaryNotification()

    def test_includes_a_user_with_work_completed_in_the_period(self):
        user = UserFactory()
        complete_on(TaskFactory(user=user), last_month_end())

        self.assertEqual(list(self.notification.recipients()), [user])

    def test_includes_a_user_with_open_work(self):
        user = UserFactory()
        TaskFactory(user=user)

        self.assertEqual(list(self.notification.recipients()), [user])

    def test_excludes_a_user_with_nothing_reportable(self):
        UserFactory()

        self.assertEqual(list(self.notification.recipients()), [])


class MonthlySummaryDeliveryTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email='user@example.com')
        enable_notification(event=EVENT, channel=Channel.EMAIL)
        self.end = last_month_end()
        self.today = timezone.localdate()

    def send(self):
        NotificationService(MonthlySummaryNotification()).send_bulk()

    def test_emails_every_section(self):
        group = GroupFactory(user=self.user, name='Side project')
        complete_on(
            TaskFactory(
                user=self.user,
                name='Shipped it',
                weight=8,
                group=group,
                due_date=self.end,
            ),
            self.end - timedelta(days=2),
        )
        TaskFactory(
            user=self.user, name='Tax email', due_date=self.today - timedelta(days=3)
        )
        TaskFactory(user=self.user, name='Read that paper')

        self.send()

        body = mail.outbox[0].body
        self.assertIn('COMPLETED (1)', body)
        self.assertIn('Shipped it', body)
        self.assertIn('Side project', body)
        self.assertIn('2 days early', body)
        self.assertIn('OVERDUE (1)', body)
        self.assertIn('Tax email', body)
        self.assertIn('STILL OPEN (1)', body)
        self.assertIn('Read that paper', body)

    def test_the_subject_names_the_reported_month(self):
        TaskFactory(user=self.user)

        self.send()

        self.assertIn(f'{self.end:%B %Y}', mail.outbox[0].subject)

    def test_is_idempotent_within_the_month(self):
        TaskFactory(user=self.user)

        self.send()
        self.send()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NotificationLog.objects.get().dedup_key, f'{self.end:%Y-%m}')

    def test_sends_nothing_when_there_is_nothing_to_report(self):
        self.send()

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_skips_a_user_who_opted_out(self):
        TaskFactory(user=self.user)
        NotificationUserPreferenceFactory(
            user=self.user, event=EVENT, channel=Channel.EMAIL, enabled=False
        )

        self.send()

        self.assertEqual(len(mail.outbox), 0)

    def test_attaches_an_html_alternative(self):
        TaskFactory(user=self.user)

        self.send()

        content, mimetype = mail.outbox[0].alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('<!doctype html>', content)
