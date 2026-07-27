from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from common.models import SiteSettings
from notifications.channels.base import BaseNotificationChannel
from notifications.channels.email import EmailChannel
from notifications.exceptions import MissingRecipient
from notifications.models import NotificationEvent

EVENT = NotificationEvent.TASK_DUE_REMINDER.value


class BaseChannelTests(TestCase):
    def test_cannot_instantiate_a_channel_without_its_hooks(self):
        class Hookless(BaseNotificationChannel):
            key = "hookless"

        with self.assertRaises(TypeError):
            Hookless()


class EmailChannelTests(TestCase):
    def setUp(self):
        cache.clear()
        self.channel = EmailChannel()
        self.user = UserFactory(email="user@example.com")

    def test_is_enabled_reflects_global_channel_setting(self):
        self.assertTrue(self.channel.is_enabled())

        site = SiteSettings.load()
        site.notification_channels_email_enabled = False
        site.save()
        self.assertFalse(self.channel.is_enabled())

    def test_recipient_is_none_when_blank(self):
        self.assertIsNone(self.channel.recipient(UserFactory(email="")))

    def test_deliver_renders_subject_and_body(self):
        context = {"date": timezone.localdate(), "overdue": [], "due_today": []}

        self.channel.deliver(user=self.user, event=EVENT, context=context)

        message = mail.outbox[0]
        self.assertIn("WupNext", message.subject)
        self.assertIn(self.user.username, message.body)

    def test_deliver_raises_when_no_recipient(self):
        user = UserFactory(email="")

        with self.assertRaises(MissingRecipient):
            self.channel.deliver(user=user, event=EVENT, context={})
