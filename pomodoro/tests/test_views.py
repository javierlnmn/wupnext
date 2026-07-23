import json

from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import UserFactory
from pomodoro.models import Phase, PomodoroState

from .factories import PomodoroStateFactory


class PomodoroStateViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse("pomodoro:state")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_returns_state_dict(self):
        PomodoroStateFactory(user=self.user, phase=Phase.SHORT, completed=2)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["phase"], Phase.SHORT)
        self.assertEqual(body["completed"], 2)
        self.assertIn("updatedAt", body)

    def test_get_creates_state_lazily(self):
        self.assertFalse(PomodoroState.objects.filter(user=self.user).exists())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PomodoroState.objects.filter(user=self.user).exists())

    def test_post_persists_state(self):
        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "phase": Phase.LONG,
                    "running": True,
                    "ends_at_ms": 1700000000000,
                    "remaining": None,
                    "completed": 4,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        state = PomodoroState.for_user(self.user)
        self.assertEqual(state.phase, Phase.LONG)
        self.assertTrue(state.running)
        self.assertEqual(state.ends_at_ms, 1700000000000)
        self.assertEqual(state.completed, 4)
        self.assertEqual(response.json()["endsAt"], 1700000000000)

    def test_post_with_malformed_json_returns_400(self):
        response = self.client.post(
            self.url, data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_post_with_invalid_field_returns_400_with_errors(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"phase": "invalid"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("phase", response.json()["errors"])
