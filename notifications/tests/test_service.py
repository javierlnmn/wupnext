from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.exceptions import MissingRecipient, UnknownChannel
from notifications.models import Channel, NotificationLog
from notifications.service import NotificationService
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)

EVENT = 'task_due_reminder'
EMAIL = [Channel.EMAIL]


def reminder_context():
    return {'date': timezone.localdate(), 'overdue': [], 'due_today': []}


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email='user@example.com')
        self.channel_switch, self.event_switch = enable_notification()

    def notify(self, **kwargs):
        NotificationService.notify(
            self.user, EVENT, channels=EMAIL, context=reminder_context(), **kwargs
        )

    def assertNothingSent(self):
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_channels_must_be_given(self):
        with self.assertRaises(TypeError):
            NotificationService.notify(self.user, EVENT)

    def test_unknown_channel_names_the_alternatives(self):
        with self.assertRaises(UnknownChannel) as caught:
            NotificationService.notify(self.user, EVENT, channels=['emial'])

        self.assertIn('emial', str(caught.exception))

    def test_no_channels_sends_nothing(self):
        NotificationService.notify(self.user, EVENT, channels=[])

        self.assertNothingSent()

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

    def test_disabled_channel_switch_is_skipped(self):
        self.channel_switch.enabled = False
        self.channel_switch.save()

        self.notify(dedup_key='day-1')

        self.assertNothingSent()

    def test_disabled_event_switch_is_skipped(self):
        self.event_switch.enabled = False
        self.event_switch.save()

        self.notify(dedup_key='day-1')

        self.assertNothingSent()

    def test_user_who_opted_out_is_skipped(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        self.notify(dedup_key='day-1')

        self.assertNothingSent()

    def test_user_who_never_chose_and_is_not_on_by_default_is_skipped(self):
        self.event_switch.on_by_default = False
        self.event_switch.save()

        self.notify(dedup_key='day-1')

        self.assertNothingSent()

    def test_user_who_opted_in_against_an_off_default_is_sent_to(self):
        self.event_switch.on_by_default = False
        self.event_switch.save()
        NotificationUserPreferenceFactory(user=self.user, enabled=True)

        self.notify()

        self.assertEqual(len(mail.outbox), 1)

    def test_missing_recipient_raises_and_rolls_back_log(self):
        self.user = UserFactory(email='')

        with self.assertRaises(MissingRecipient):
            self.notify(dedup_key='day-1')

        self.assertNothingSent()
