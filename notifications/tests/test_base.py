from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.module_loading import import_string

from accounts.tests.factories import UserFactory
from notifications.base import BaseBulkNotification, BaseNotification
from notifications.jobs import send_notification_to_user
from notifications.models import Channel
from notifications.service import NotificationService
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)

EVENT = 'task_due_reminder'


class SingleHost(BaseNotification):
    event = EVENT
    channels = (Channel.EMAIL,)

    def _is_applicable_for_user(self, user, context):
        return True

    def _dedup_key(self, user, context):
        return ''

    def context(self, user):
        return {'username': user.username}


class BulkHost(BaseBulkNotification, SingleHost):
    def _recipients(self):
        return get_user_model().objects.filter(is_active=True)


class NotificationContractTests(TestCase):
    def test_cannot_instantiate_a_notification_without_its_hooks(self):
        class Hookless(BaseNotification):
            event = EVENT

        with self.assertRaises(TypeError):
            Hookless()

    def test_a_notification_declares_every_hook_itself(self):
        self.assertEqual(
            BaseNotification.__abstractmethods__,
            frozenset({'_is_applicable_for_user', '_dedup_key', 'context'}),
        )

    def test_a_bulk_notification_also_declares_its_recipients(self):
        self.assertIn('_recipients', BaseBulkNotification.__abstractmethods__)

    def test_a_single_notification_has_no_batch_entry_points(self):
        self.assertFalse(hasattr(SingleHost(), '_send'))
        self.assertFalse(hasattr(SingleHost(), 'enqueue'))


class SendToTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()
        patcher = mock.patch.object(NotificationService, 'notify')
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_delivers_to_a_single_user(self):
        SingleHost().send_to(self.user)

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_passes_the_declared_channels(self):
        SingleHost().send_to(self.user)

        self.assertEqual(self.notify.call_args.kwargs['channels'], (Channel.EMAIL,))

    def test_skips_an_event_disabled_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        SingleHost().send_to(self.user)

        self.notify.assert_not_called()

    def test_skips_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        SingleHost().send_to(self.user)

        self.notify.assert_not_called()

    def test_skips_a_user_the_notification_does_not_apply_to(self):
        class NothingToSay(SingleHost):
            def _is_applicable_for_user(self, user, context):
                return False

        NothingToSay().send_to(self.user)

        self.notify.assert_not_called()

    def test_does_not_build_context_for_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        with mock.patch.object(SingleHost, 'context') as context:
            SingleHost().send_to(self.user)

        context.assert_not_called()

    def test_raises_instead_of_swallowing(self):
        self.notify.side_effect = Exception('boom')

        with self.assertRaises(Exception):
            SingleHost().send_to(self.user)


class BulkSendTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()
        patcher = mock.patch.object(NotificationService, 'notify')
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_nothing_when_the_event_is_disabled_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        BulkHost()._send()

        self.notify.assert_not_called()

    def test_notifies_each_recipient_with_its_own_context(self):
        other = UserFactory()

        BulkHost()._send()

        notified = {
            call.args[0]: call.kwargs['context'] for call in self.notify.call_args_list
        }
        self.assertEqual(
            notified,
            {
                self.user: {'username': self.user.username},
                other: {'username': other.username},
            },
        )

    def test_skips_inactive_users(self):
        UserFactory(is_active=False)

        BulkHost()._send()

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_skips_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        BulkHost()._send()

        self.notify.assert_not_called()

    def test_passes_the_dedup_key(self):
        class Deduped(BulkHost):
            def _dedup_key(self, user, context):
                return context['username']

        Deduped()._send()

        self.assertEqual(self.notify.call_args.kwargs['dedup_key'], self.user.username)

    def test_one_failure_does_not_stop_the_batch(self):
        UserFactory()
        self.notify.side_effect = [Exception('boom'), None]

        with self.assertLogs('notifications.base', level='ERROR'):
            BulkHost()._send()

        self.assertEqual(self.notify.call_count, 2)


class BulkEnqueueTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()
        patcher = mock.patch('notifications.base.async_task')
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

    def test_enqueues_nothing_when_the_event_is_disabled_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        BulkHost().enqueue()

        self.async_task.assert_not_called()

    def test_enqueues_nothing_for_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        BulkHost().enqueue()

        self.async_task.assert_not_called()
