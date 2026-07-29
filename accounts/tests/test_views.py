from django.test import TestCase
from django.urls import reverse

from accounts.models import UserPreferences
from accounts.tests.factories import UserFactory


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
