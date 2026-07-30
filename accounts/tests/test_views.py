from django.test import TestCase
from django.urls import reverse

from accounts.models import UserPreferences
from accounts.tests.factories import UserFactory
from notifications.models import Channel, NotificationUserPreference
from notifications.tests.factories import enable_notification

NOTIFY_EMAIL = f'notify-task_due_reminder-{Channel.EMAIL}'


class PreferencesViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse('accounts:preferences')

    def payload(self, **overrides):
        data = {
            'pomodoro_focus': 30,
            'pomodoro_short_break': 10,
            'pomodoro_long_break': 20,
            'pomodoro_long_every': 3,
        }
        data.update(overrides)
        return data

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

    def test_saves_pomodoro_settings(self):
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})
        prefs = UserPreferences.for_user(self.user)
        self.assertEqual(prefs.pomodoro_focus, 30)
        self.assertEqual(prefs.pomodoro_short_break, 10)
        self.assertEqual(prefs.pomodoro_long_break, 20)
        self.assertEqual(prefs.pomodoro_long_every, 3)

    def test_invalid_values_return_400_with_errors(self):
        response = self.client.post(self.url, self.payload(pomodoro_focus=999))
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body['ok'])
        self.assertIn('pomodoro_focus', body['errors'])

    def test_saves_notification_preferences_alongside_pomodoro(self):
        enable_notification()

        response = self.client.post(self.url, self.payload(**{NOTIFY_EMAIL: 'on'}))

        self.assertEqual(response.status_code, 200)
        preference = NotificationUserPreference.objects.get(user=self.user)
        self.assertEqual(preference.event, 'task_due_reminder')
        self.assertEqual(preference.channel, Channel.EMAIL)
        self.assertTrue(preference.enabled)

    def test_an_unchecked_notification_is_stored_as_an_opt_out(self):
        enable_notification()

        response = self.client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(NotificationUserPreference.objects.get(user=self.user).enabled)

    def test_invalid_pomodoro_saves_no_notification_preference(self):
        enable_notification()

        response = self.client.post(
            self.url, self.payload(pomodoro_focus=999, **{NOTIFY_EMAIL: 'on'})
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(NotificationUserPreference.objects.exists())
