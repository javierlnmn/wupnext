from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.module_loading import import_string

from accounts.models import UserPreferences
from accounts.tests.factories import UserFactory
from notifications.base import BaseBulkNotification, BaseNotification
from notifications.jobs import send_notification_to_user
from notifications.service import notification_service


class SingleHost(BaseNotification):
    event = "task_due_reminder"

    def _is_enabled_on_site(self):
        return True

    def _is_enabled_for_user(self, user):
        return True

    def _is_applicable_for_user(self, user, context):
        return True

    def _dedup_key(self, user, context):
        return ""

    def context(self, user):
        return {"username": user.username}


class BulkHost(BaseBulkNotification):
    event = "task_due_reminder"

    def _is_enabled_on_site(self):
        return True

    def _is_enabled_for_user(self, user):
        return UserPreferences.for_user(user).notification_channels_email_enabled

    def _is_applicable_for_user(self, user, context):
        return True

    def _dedup_key(self, user, context):
        return ""

    def _recipients(self):
        return get_user_model().objects.filter(is_active=True)

    def context(self, user):
        return {"username": user.username}


class DisabledHost(BulkHost):
    def _is_enabled_on_site(self):
        return False


class NotificationContractTests(TestCase):
    def test_cannot_instantiate_a_notification_without_its_hooks(self):
        class Hookless(BaseNotification):
            event = "task_due_reminder"

        with self.assertRaises(TypeError):
            Hookless()

    def test_a_notification_declares_every_hook_itself(self):
        self.assertEqual(
            BaseNotification.__abstractmethods__,
            frozenset(
                {
                    "_is_enabled_on_site",
                    "_is_enabled_for_user",
                    "_is_applicable_for_user",
                    "_dedup_key",
                    "context",
                }
            ),
        )

    def test_a_bulk_notification_also_declares_its_recipients(self):
        self.assertIn("_recipients", BaseBulkNotification.__abstractmethods__)

    def test_a_single_notification_has_no_batch_entry_points(self):
        self.assertFalse(hasattr(SingleHost(), "send"))
        self.assertFalse(hasattr(SingleHost(), "enqueue"))


class SendToTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        patcher = mock.patch.object(notification_service, "notify")
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_delivers_to_a_single_user(self):
        SingleHost().send_to(self.user)

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_respects_the_site_switch(self):
        DisabledHost().send_to(self.user)

        self.notify.assert_not_called()

    def test_skips_a_user_the_notification_does_not_apply_to(self):
        class NothingToSay(SingleHost):
            def _is_applicable_for_user(self, user, context):
                return False

        NothingToSay().send_to(self.user)

        self.notify.assert_not_called()

    def test_can_ignore_user_preferences(self):
        self.user.preferences.notification_channels_email_enabled = False
        self.user.preferences.save()

        SingleHost().send_to(self.user)

        self.notify.assert_called_once()

    def test_raises_instead_of_swallowing(self):
        self.notify.side_effect = Exception("boom")

        with self.assertRaises(Exception):
            SingleHost().send_to(self.user)


class BulkSendTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        patcher = mock.patch.object(notification_service, "notify")
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_nothing_when_disabled(self):
        DisabledHost().send()

        self.notify.assert_not_called()

    def test_notifies_each_recipient_with_its_own_context(self):
        other = UserFactory()

        BulkHost().send()

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

        BulkHost().send()

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_skips_user_who_disabled_the_channel(self):
        self.user.preferences.notification_channels_email_enabled = False
        self.user.preferences.save()

        BulkHost().send()

        self.notify.assert_not_called()

    def test_passes_the_dedup_key(self):
        class Deduped(BulkHost):
            def _dedup_key(self, user, context):
                return context["username"]

        Deduped().send()

        self.assertEqual(self.notify.call_args.kwargs["dedup_key"], self.user.username)

    def test_one_failure_does_not_stop_the_batch(self):
        UserFactory()
        self.notify.side_effect = [Exception("boom"), None]

        with self.assertLogs("notifications.base", level="ERROR"):
            BulkHost().send()

        self.assertEqual(self.notify.call_count, 2)


class BulkEnqueueTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        patcher = mock.patch("notifications.base.async_task")
        self.async_task = patcher.start()
        self.addCleanup(patcher.stop)

    def test_enqueues_one_job_per_recipient(self):
        other = UserFactory()

        BulkHost().enqueue()

        self.assertCountEqual(
            [call.args[2] for call in self.async_task.call_args_list],
            [self.user.pk, other.pk],
        )

    def test_enqueues_a_resolvable_job_and_notification(self):
        BulkHost().enqueue()

        job, path, _ = self.async_task.call_args.args
        self.assertIs(import_string(job), send_notification_to_user)
        self.assertIs(import_string(path), BulkHost)

    def test_enqueues_nothing_when_disabled_on_site(self):
        DisabledHost().enqueue()

        self.async_task.assert_not_called()
