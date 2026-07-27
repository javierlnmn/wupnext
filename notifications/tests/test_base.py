from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from accounts.tests.factories import UserFactory
from notifications.base import BaseNotification
from notifications.models import NotificationEvent
from notifications.service import notification_service


class NotificationHost(BaseNotification):
    event = NotificationEvent.TASK_DUE_REMINDER

    def context(self, user):
        return {"username": user.username}


class EventlessHost(NotificationHost):
    event = None


class DisabledHost(NotificationHost):
    def is_enabled(self):
        return False


class NotificationContractTests(TestCase):
    def test_cannot_instantiate_a_notification_without_a_context(self):
        class Contextless(BaseNotification):
            event = NotificationEvent.TASK_DUE_REMINDER

        with self.assertRaises(TypeError):
            Contextless()


class NotificationSendTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        patcher = mock.patch.object(notification_service, "notify")
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_requires_an_event(self):
        with self.assertRaises(ImproperlyConfigured):
            EventlessHost().send()

    def test_sends_nothing_when_disabled(self):
        DisabledHost().send()

        self.notify.assert_not_called()

    def test_notifies_each_recipient_with_its_own_context(self):
        other = UserFactory()

        NotificationHost().send()

        notified = {
            call.args[0]: call.kwargs["context"] for call in self.notify.call_args_list
        }
        self.assertEqual(
            notified,
            {
                self.user: {"username": self.user.username},
                other: {"username": other.username},
            },
        )

    def test_skips_inactive_users(self):
        UserFactory(is_active=False)

        NotificationHost().send()

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_skips_user_without_context(self):
        class NothingToSay(NotificationHost):
            def context(self, user):
                return None

        NothingToSay().send()

        self.notify.assert_not_called()

    def test_skips_user_who_disabled_the_channel(self):
        self.user.preferences.notification_channels_email_enabled = False
        self.user.preferences.save()

        NotificationHost().send()

        self.notify.assert_not_called()

    def test_passes_the_dedup_key(self):
        class Deduped(NotificationHost):
            def dedup_key(self, user, context):
                return context["username"]

        Deduped().send()

        self.assertEqual(self.notify.call_args.kwargs["dedup_key"], self.user.username)

    def test_defaults_to_no_dedup_key(self):
        NotificationHost().send()

        self.assertEqual(self.notify.call_args.kwargs["dedup_key"], "")

    def test_one_failure_does_not_stop_the_batch(self):
        UserFactory()
        self.notify.side_effect = [Exception("boom"), None]

        with self.assertLogs("notifications.base", level="ERROR"):
            NotificationHost().send()

        self.assertEqual(self.notify.call_count, 2)
