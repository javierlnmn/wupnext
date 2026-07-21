from django.test import TestCase

from accounts.tests.factories import UserFactory
from pomodoro.models import Phase, PomodoroState

from .factories import PomodoroStateFactory


class ForUserTests(TestCase):
    def test_creates_state_on_first_call(self):
        user = UserFactory()
        self.assertFalse(PomodoroState.objects.filter(user=user).exists())
        state = PomodoroState.for_user(user)
        self.assertEqual(state.user, user)
        self.assertEqual(PomodoroState.objects.filter(user=user).count(), 1)

    def test_returns_existing_state_on_later_calls(self):
        user = UserFactory()
        first = PomodoroState.for_user(user)
        second = PomodoroState.for_user(user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PomodoroState.objects.filter(user=user).count(), 1)

    def test_defaults(self):
        state = PomodoroState.for_user(UserFactory())
        self.assertEqual(state.phase, Phase.FOCUS)
        self.assertFalse(state.running)
        self.assertIsNone(state.ends_at_ms)
        self.assertIsNone(state.remaining)
        self.assertEqual(state.completed, 0)


class StateDictTests(TestCase):
    def test_serializes_defaults(self):
        state = PomodoroStateFactory()
        data = state.state_dict()
        self.assertEqual(
            set(data),
            {"phase", "running", "endsAt", "remaining", "completed", "updatedAt"},
        )
        self.assertEqual(data["phase"], Phase.FOCUS)
        self.assertFalse(data["running"])
        self.assertIsNone(data["endsAt"])
        self.assertIsNone(data["remaining"])
        self.assertEqual(data["completed"], 0)

    def test_serializes_running_state(self):
        state = PomodoroStateFactory(
            phase=Phase.LONG,
            running=True,
            ends_at_ms=1_800_000_000_000,
            remaining=900,
            completed=3,
        )
        data = state.state_dict()
        self.assertEqual(data["phase"], Phase.LONG)
        self.assertTrue(data["running"])
        self.assertEqual(data["endsAt"], 1_800_000_000_000)
        self.assertEqual(data["remaining"], 900)
        self.assertEqual(data["completed"], 3)

    def test_updated_at_is_serialized_as_epoch_ms(self):
        state = PomodoroStateFactory()
        expected = int(state.updated_at.timestamp() * 1000)
        self.assertEqual(state.state_dict()["updatedAt"], expected)
