from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.channels.base import BaseNotificationChannel
from notifications.channels.email import EmailChannel, has_resend_api_key
from notifications.channels.registry import (
    CHANNELS,
    get_channel,
    get_unavailable_channel_keys,
)
from notifications.exceptions import MissingRecipient, UnknownChannel
from notifications.models import Channel

EVENT = 'task_due_reminder'
LIVE_WITHOUT_KEY = override_settings(
    EMAIL_BACKEND=settings.LIVE_EMAIL_BACKEND, ANYMAIL={'RESEND_API_KEY': ''}
)
LIVE_WITH_KEY = override_settings(
    EMAIL_BACKEND=settings.LIVE_EMAIL_BACKEND, ANYMAIL={'RESEND_API_KEY': 're_test'}
)


class BaseChannelTests(TestCase):
    def test_cannot_instantiate_a_channel_without_deliver(self):
        class Hookless(BaseNotificationChannel):
            key = 'hookless'

        with self.assertRaises(TypeError):
            Hookless()


class ChannelAvailabilityTests(TestCase):
    def test_a_channel_is_available_unless_it_says_otherwise(self):
        class Plain(BaseNotificationChannel):
            key = 'plain'

            def deliver(self, *, user, event, context): ...

        self.assertTrue(Plain().is_available())

    @override_settings(ANYMAIL={'RESEND_API_KEY': ''})
    def test_email_is_available_when_the_backend_needs_no_key(self):
        # The test runner uses the locmem backend, which sends without a key.
        self.assertTrue(EmailChannel().is_available())

    @LIVE_WITHOUT_KEY
    def test_email_is_unavailable_when_the_live_backend_has_no_key(self):
        self.assertFalse(EmailChannel().is_available())

    @LIVE_WITH_KEY
    def test_email_is_available_when_the_live_backend_has_a_key(self):
        self.assertTrue(EmailChannel().is_available())

    @override_settings(ANYMAIL={})
    def test_an_absent_key_setting_counts_as_no_key(self):
        self.assertFalse(has_resend_api_key())

    def test_nothing_is_unavailable_under_the_test_backend(self):
        self.assertEqual(get_unavailable_channel_keys(), [])

    @LIVE_WITHOUT_KEY
    def test_email_is_listed_as_unavailable_without_a_key(self):
        self.assertEqual(get_unavailable_channel_keys(), [Channel.EMAIL])


class ChannelRegistryTests(TestCase):
    def test_discovers_the_email_channel(self):
        self.assertIsInstance(CHANNELS[Channel.EMAIL], EmailChannel)

    def test_does_not_register_the_keyless_base_class(self):
        self.assertNotIn(None, CHANNELS)

    def test_get_channel_resolves_a_known_key(self):
        self.assertIs(get_channel(Channel.EMAIL), CHANNELS[Channel.EMAIL])

    def test_get_channel_names_the_key_and_the_alternatives(self):
        with self.assertRaises(UnknownChannel) as caught:
            get_channel('emial')

        message = str(caught.exception)
        self.assertIn('emial', message)
        self.assertIn(Channel.EMAIL, message)


class EmailChannelTests(TestCase):
    def setUp(self):
        self.channel = EmailChannel()
        self.user = UserFactory(email='user@example.com')

    def test_deliver_renders_subject_and_body(self):
        context = {'date': timezone.localdate(), 'overdue': [], 'due_today': []}

        self.channel.deliver(user=self.user, event=EVENT, context=context)

        message = mail.outbox[0]
        self.assertIn('WupNext', message.subject)
        self.assertIn(self.user.username, message.body)

    def test_deliver_raises_when_no_recipient(self):
        user = UserFactory(email='')

        with self.assertRaises(MissingRecipient):
            self.channel.deliver(user=user, event=EVENT, context={})
