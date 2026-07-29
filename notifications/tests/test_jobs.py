from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.jobs import send_notification_to_user
from notifications.tests.factories import enable_notification
from tasks.tests.factories import TaskFactory

NOTIFICATION = 'tasks.notifications.due_reminders.DueReminderNotification'


class SendNotificationToUserTests(TestCase):
    def setUp(self):
        enable_notification()
        self.user = UserFactory(email='user@example.com')
        TaskFactory(
            user=self.user,
            name='Renew the domain',
            due_date=timezone.localdate() - timedelta(days=1),
        )

    def test_delivers_to_the_resolved_user(self):
        send_notification_to_user(NOTIFICATION, self.user.pk)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['user@example.com'])
        self.assertIn('Renew the domain', mail.outbox[0].body)

    def test_does_nothing_when_the_user_no_longer_exists(self):
        user_id = self.user.pk
        self.user.delete()

        send_notification_to_user(NOTIFICATION, user_id)

        self.assertEqual(len(mail.outbox), 0)

    def test_does_nothing_when_the_user_has_nothing_due(self):
        quiet = UserFactory(email='quiet@example.com')

        send_notification_to_user(NOTIFICATION, quiet.pk)

        self.assertEqual(len(mail.outbox), 0)
