from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from django.utils.module_loading import import_string

from accounts.tests.factories import UserFactory
from notifications.base import BaseBulkNotification, BaseNotification
from notifications.exceptions import MissingRecipient, UnknownChannel
from notifications.jobs import send_notification_to_user
from notifications.models import Channel, NotificationLog
from notifications.service import NotificationService
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)

EVENT = 'task_due_reminder'
EMAIL = [Channel.EMAIL]
PUSH = 'push'


def reminder_context():
    return {'date': timezone.localdate(), 'overdue': [], 'due_today': []}


class SingleHost(BaseNotification):
    event = EVENT
    channels = (Channel.EMAIL,)

    def context(self, user):
        return {'username': user.username}

    def is_applicable_for(self, user, context):
        return True

    def dedup_key(self, user, context):
        return ''


class BulkHost(BaseBulkNotification, SingleHost):
    def recipients(self):
        return get_user_model().objects.filter(is_active=True)


class NotifyTests(TestCase):
    """notify delivers what it is given: the gating happened upstream."""

    def setUp(self):
        self.user = UserFactory(email='user@example.com')

    def notify(self, **kwargs):
        NotificationService(SingleHost()).notify(
            self.user, channels=EMAIL, context=reminder_context(), **kwargs
        )

    def test_channels_must_be_given(self):
        with self.assertRaises(TypeError):
            NotificationService(SingleHost()).notify(self.user)

    def test_unknown_channel_names_the_alternatives(self):
        with self.assertRaises(UnknownChannel) as caught:
            NotificationService(SingleHost()).notify(self.user, channels=['emial'])

        self.assertIn('emial', str(caught.exception))

    def test_an_unknown_channel_sends_nothing_at_all(self):
        with self.assertRaises(UnknownChannel):
            NotificationService(SingleHost()).notify(
                self.user, channels=[Channel.EMAIL, 'emial']
            )

        self.assertEqual(len(mail.outbox), 0)

    def test_no_channels_sends_nothing(self):
        NotificationService(SingleHost()).notify(self.user, channels=[])

        self.assertEqual(len(mail.outbox), 0)

    def test_sends_email(self):
        self.notify()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['user@example.com'])

    def test_attaches_html_alternative(self):
        self.notify()

        alternatives = mail.outbox[0].alternatives
        self.assertEqual(len(alternatives), 1)
        self.assertEqual(alternatives[0][1], 'text/html')

    def test_dedup_key_sends_only_once(self):
        for _ in range(3):
            self.notify(dedup_key='2026-07-23')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NotificationLog.objects.count(), 1)

    def test_distinct_dedup_keys_send_again(self):
        self.notify(dedup_key='day-1')
        self.notify(dedup_key='day-2')

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(NotificationLog.objects.count(), 2)

    def test_without_dedup_key_never_logs(self):
        self.notify()
        self.notify()

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_missing_recipient_raises_and_rolls_back_log(self):
        self.user = UserFactory(email='')

        with self.assertRaises(MissingRecipient):
            self.notify(dedup_key='day-1')

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)


class DeliveryChannelsByUserTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()

    def deliveries(self, channels=EMAIL):
        host = BulkHost()
        host.channels = tuple(channels)
        return NotificationService(host)._get_delivery_channels_by_user(
            [self.user, self.other]
        )

    def test_maps_every_user_to_the_channels_they_get(self):
        self.assertEqual(
            self.deliveries(),
            {self.user: [Channel.EMAIL], self.other: [Channel.EMAIL]},
        )

    def test_omits_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        self.assertEqual(self.deliveries(), {self.other: [Channel.EMAIL]})

    def test_empty_when_the_channel_is_switched_off_on_site(self):
        self.channel_switch.enabled = False
        self.channel_switch.save()

        self.assertEqual(self.deliveries(), {})

    def test_empty_when_the_event_is_switched_off_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        self.assertEqual(self.deliveries(), {})

    def test_empty_when_the_notification_declares_no_channel(self):
        self.assertEqual(self.deliveries(channels=[]), {})

    def test_empty_when_nobody_chose_and_it_is_not_on_by_default(self):
        self.event_switch.on_by_default = False
        self.event_switch.save()

        self.assertEqual(self.deliveries(), {})

    def test_includes_only_the_user_who_opted_in_against_an_off_default(self):
        self.event_switch.on_by_default = False
        self.event_switch.save()
        NotificationUserPreferenceFactory(user=self.user, enabled=True)

        self.assertEqual(self.deliveries(), {self.user: [Channel.EMAIL]})

    def test_lists_only_the_channels_the_user_gets(self):
        enable_notification(channel=PUSH)
        self.event_switch.on_by_default = False
        self.event_switch.save()

        self.assertEqual(
            self.deliveries(channels=[Channel.EMAIL, PUSH]),
            {self.user: [PUSH], self.other: [PUSH]},
        )

    def test_an_opt_in_cannot_beat_the_site_switch(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=True)
        self.event_switch.enabled = False
        self.event_switch.save()

        self.assertEqual(self.deliveries(), {})

    def test_ignores_a_channel_the_notification_does_not_declare(self):
        enable_notification(channel=PUSH)

        self.assertEqual(
            self.deliveries(),
            {self.user: [Channel.EMAIL], self.other: [Channel.EMAIL]},
        )

    def test_ignores_a_preference_for_another_event(self):
        NotificationUserPreferenceFactory(
            user=self.user, event='other_event', enabled=False
        )

        self.assertEqual(
            self.deliveries(),
            {self.user: [Channel.EMAIL], self.other: [Channel.EMAIL]},
        )

    def test_ignores_a_preference_of_a_user_not_asked_about(self):
        NotificationUserPreferenceFactory(user=UserFactory(), enabled=False)

        self.assertEqual(
            self.deliveries(),
            {self.user: [Channel.EMAIL], self.other: [Channel.EMAIL]},
        )

    def test_costs_two_queries_for_any_number_of_users(self):
        with self.assertNumQueries(2):
            self.deliveries()

        for _ in range(8):
            UserFactory()

        users = list(get_user_model().objects.all())
        with self.assertNumQueries(2):
            NotificationService(BulkHost())._get_delivery_channels_by_user(users)


class SendTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()
        patcher = mock.patch.object(NotificationService, 'notify')
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_delivers_to_a_single_user(self):
        NotificationService(SingleHost()).send(self.user)

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_passes_only_the_channels_the_user_gets(self):
        NotificationService(SingleHost()).send(self.user)

        self.assertEqual(self.notify.call_args.kwargs['channels'], [Channel.EMAIL])

    def test_skips_an_event_disabled_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        NotificationService(SingleHost()).send(self.user)

        self.notify.assert_not_called()

    def test_skips_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        NotificationService(SingleHost()).send(self.user)

        self.notify.assert_not_called()

    def test_skips_a_user_the_notification_does_not_apply_to(self):
        class NothingToSay(SingleHost):
            def is_applicable_for(self, user, context):
                return False

        NotificationService(NothingToSay()).send(self.user)

        self.notify.assert_not_called()

    def test_does_not_build_context_for_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        with mock.patch.object(SingleHost, 'context') as context:
            NotificationService(SingleHost()).send(self.user)

        context.assert_not_called()

    def test_raises_instead_of_swallowing(self):
        self.notify.side_effect = Exception('boom')

        with self.assertRaises(Exception):
            NotificationService(SingleHost()).send(self.user)


class SendBulkTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()
        patcher = mock.patch.object(NotificationService, 'notify')
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_sends_nothing_when_the_event_is_disabled_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        NotificationService(BulkHost()).send_bulk()

        self.notify.assert_not_called()

    def test_notifies_each_recipient_with_its_own_context(self):
        other = UserFactory()

        NotificationService(BulkHost()).send_bulk()

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

        NotificationService(BulkHost()).send_bulk()

        self.notify.assert_called_once()
        self.assertEqual(self.notify.call_args.args[0], self.user)

    def test_skips_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        NotificationService(BulkHost()).send_bulk()

        self.notify.assert_not_called()

    def test_passes_the_dedup_key(self):
        class Deduped(BulkHost):
            def dedup_key(self, user, context):
                return context['username']

        NotificationService(Deduped()).send_bulk()

        self.assertEqual(self.notify.call_args.kwargs['dedup_key'], self.user.username)

    def test_one_failure_does_not_stop_the_batch(self):
        UserFactory()
        self.notify.side_effect = [Exception('boom'), None]

        with self.assertLogs('notifications.service', level='ERROR'):
            NotificationService(BulkHost()).send_bulk()

        self.assertEqual(self.notify.call_count, 2)

    def test_resolves_the_batch_without_querying_per_user(self):
        for _ in range(8):
            UserFactory()

        with self.assertNumQueries(3):
            NotificationService(BulkHost()).send_bulk()

        self.assertEqual(self.notify.call_count, 9)


class EnqueueTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()
        patcher = mock.patch('notifications.service.async_task')
        self.async_task = patcher.start()
        self.addCleanup(patcher.stop)

    def test_enqueues_one_job_per_recipient(self):
        other = UserFactory()

        NotificationService(BulkHost()).enqueue()

        self.assertCountEqual(
            [call.args[2] for call in self.async_task.call_args_list],
            [self.user.pk, other.pk],
        )

    def test_enqueues_a_resolvable_job_and_notification(self):
        NotificationService(BulkHost()).enqueue()

        job, path, _ = self.async_task.call_args.args
        self.assertIs(import_string(job), send_notification_to_user)
        self.assertIs(import_string(path), BulkHost)

    def test_enqueues_nothing_when_the_event_is_disabled_on_site(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        NotificationService(BulkHost()).enqueue()

        self.async_task.assert_not_called()

    def test_enqueues_nothing_when_the_channel_is_disabled_on_site(self):
        self.channel_switch.enabled = False
        self.channel_switch.save()

        NotificationService(BulkHost()).enqueue()

        self.async_task.assert_not_called()

    def test_enqueues_nothing_for_a_user_who_opted_out(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        NotificationService(BulkHost()).enqueue()

        self.async_task.assert_not_called()

    def test_resolves_the_batch_without_querying_per_user(self):
        for _ in range(8):
            UserFactory()

        with self.assertNumQueries(3):
            NotificationService(BulkHost()).enqueue()

        self.assertEqual(self.async_task.call_count, 9)
