from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from common.models import SiteSettings
from notifications.exceptions import MissingRecipient
from notifications.models import Channel, NotificationEvent, NotificationLog
from notifications.service import NotificationService, notification_service

EVENT = NotificationEvent.TASK_DUE_REMINDER


def reminder_context():
    return {"date": timezone.localdate(), "overdue": [], "due_today": []}


class NotificationServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = UserFactory(email="user@example.com")

    def test_singleton_returns_same_instance(self):
        self.assertIs(NotificationService(), notification_service)

    def test_notify_sends_email(self):
        notification_service.notify(self.user, EVENT, reminder_context())

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])

    def test_notify_attaches_html_alternative(self):
        notification_service.notify(self.user, EVENT, reminder_context())

        alternatives = mail.outbox[0].alternatives
        self.assertEqual(len(alternatives), 1)
        self.assertEqual(alternatives[0][1], "text/html")

    def test_dedup_key_sends_only_once(self):
        for _ in range(3):
            notification_service.notify(
                self.user, EVENT, reminder_context(), dedup_key="2026-07-23"
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NotificationLog.objects.count(), 1)

    def test_distinct_dedup_keys_send_again(self):
        notification_service.notify(
            self.user, EVENT, reminder_context(), dedup_key="day-1"
        )
        notification_service.notify(
            self.user, EVENT, reminder_context(), dedup_key="day-2"
        )

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(NotificationLog.objects.count(), 2)

    def test_without_dedup_key_never_logs(self):
        notification_service.notify(self.user, EVENT, reminder_context())
        notification_service.notify(self.user, EVENT, reminder_context())

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_globally_disabled_channel_is_skipped(self):
        site = SiteSettings.load()
        site.notifications_disabled_channels = [Channel.EMAIL]
        site.save()

        notification_service.notify(
            self.user, EVENT, reminder_context(), dedup_key="day-1"
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_missing_recipient_raises_and_rolls_back_log(self):
        user = UserFactory(email="")

        with self.assertRaises(MissingRecipient):
            notification_service.notify(
                user, EVENT, reminder_context(), dedup_key="day-1"
            )

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)
