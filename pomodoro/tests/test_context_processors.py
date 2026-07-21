from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from accounts.models import UserPreferences
from accounts.tests.factories import UserFactory
from pomodoro.context_processors import pomodoro
from pomodoro.models import PomodoroState


class PomodoroContextTests(TestCase):
    def pomodoro_context(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return pomodoro(request)

    def test_returns_empty_for_anonymous_user(self):
        self.assertEqual(self.pomodoro_context(AnonymousUser()), {})

    def test_exposes_settings_and_state(self):
        user = UserFactory()
        context = self.pomodoro_context(user)
        self.assertEqual(
            context["pomodoro_settings"],
            UserPreferences.for_user(user).pomodoro_dict(),
        )
        self.assertEqual(
            context["pomodoro_state"],
            PomodoroState.for_user(user).state_dict(),
        )

    def test_creates_pomodoro_state_lazily(self):
        user = UserFactory()
        self.assertFalse(PomodoroState.objects.filter(user=user).exists())
        self.pomodoro_context(user)
        self.assertTrue(PomodoroState.objects.filter(user=user).exists())
