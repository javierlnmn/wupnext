from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import UserFactory
from notifications.models import Channel
from notifications.tests.factories import enable_notification

EVENT = 'task_due_reminder'
EMAIL_FIELD = f'notify-{EVENT}-{Channel.EMAIL}'


class NotificationPreferencesViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse('notifications:preferences')

    def get_html(self):
        return self.client.get(self.url).content.decode()

    def test_requires_login(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_renders_a_toggle_and_the_sentinel(self):
        enable_notification()

        html = self.get_html()

        self.assertIn(f'name="{EMAIL_FIELD}"', html)
        self.assertIn('name="sentinel"', html)
        self.assertIn('Email', html)

    def test_renders_fields_only_so_the_modal_owns_the_form(self):
        enable_notification()

        html = self.get_html()

        self.assertNotIn('<form', html)
        self.assertNotIn('type="submit"', html)

    def test_says_so_when_nothing_is_switched_on(self):
        self.assertIn('No notifications are switched on', self.get_html())
