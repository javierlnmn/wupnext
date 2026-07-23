from datetime import timedelta

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.models import NotificationLog
from tasks.reminders import send_due_reminders
from tasks.tests.factories import TaskFactory


class SendDueRemindersTests(TestCase):
    def setUp(self):
        cache.clear()
        self.today = timezone.localdate()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)
        self.user = UserFactory(email="user@example.com")

    def test_reminds_about_due_and_overdue_only(self):
        due = TaskFactory(user=self.user, name="Due today", due_date=self.today)
        overdue = TaskFactory(user=self.user, name="Overdue", due_date=self.yesterday)
        TaskFactory(user=self.user, name="Future", due_date=self.tomorrow)
        TaskFactory(user=self.user, name="No deadline", due_date=None)
        TaskFactory(
            user=self.user, name="Done", due_date=self.yesterday, completed=True
        )
        TaskFactory(
            user=self.user, name="Archived", due_date=self.yesterday, archived=True
        )
        TaskFactory(
            user=self.user, name="Subtask", due_date=self.yesterday, parent=due
        )

        send_due_reminders()

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn(due.name, body)
        self.assertIn(overdue.name, body)
        for excluded in ("Future", "No deadline", "Done", "Archived", "Subtask"):
            self.assertNotIn(excluded, body)

    def test_creates_dedup_log_for_today(self):
        TaskFactory(user=self.user, due_date=self.today)

        send_due_reminders()

        log = NotificationLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.dedup_key, str(self.today))

    def test_is_idempotent_within_the_day(self):
        TaskFactory(user=self.user, due_date=self.today)

        send_due_reminders()
        send_due_reminders()

        self.assertEqual(len(mail.outbox), 1)

    def test_no_email_when_nothing_due(self):
        TaskFactory(user=self.user, due_date=self.tomorrow)

        send_due_reminders()

        self.assertEqual(len(mail.outbox), 0)

    def test_one_user_failure_does_not_block_others(self):
        no_email = UserFactory(email="")
        TaskFactory(user=no_email, due_date=self.today)
        TaskFactory(user=self.user, due_date=self.today)

        with self.assertLogs("tasks.reminders", level="ERROR"):
            send_due_reminders()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])
