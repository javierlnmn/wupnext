from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.channels.base import BaseNotificationChannel
from notifications.channels.email import EmailChannel
from notifications.channels.registry import CHANNELS, get_channel
from notifications.exceptions import MissingRecipient, UnknownChannel
from notifications.models import Channel

EVENT = 'task_due_reminder'


class BaseChannelTests(TestCase):
    def test_cannot_instantiate_a_channel_without_deliver(self):
        class Hookless(BaseNotificationChannel):
            key = 'hookless'

        with self.assertRaises(TypeError):
            Hookless()


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
