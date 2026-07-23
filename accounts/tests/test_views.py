from django.test import TestCase
from django.urls import reverse

from accounts.models import UserPreferences
from accounts.tests.factories import UserFactory


class PomodoroSettingsViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse("accounts:pomodoro-settings")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

    def test_saves_settings(self):
        response = self.client.post(
            self.url,
            {"focus": 30, "short": 10, "long": 20, "every": 3},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        prefs = UserPreferences.for_user(self.user)
        self.assertEqual(prefs.pomodoro_focus, 30)
        self.assertEqual(prefs.pomodoro_short_break, 10)
        self.assertEqual(prefs.pomodoro_long_break, 20)
        self.assertEqual(prefs.pomodoro_long_every, 3)

    def test_invalid_values_return_400_with_errors(self):
        response = self.client.post(
            self.url,
            {"focus": 999, "short": 5, "long": 15, "every": 4},
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertIn("pomodoro_focus", body["errors"])
