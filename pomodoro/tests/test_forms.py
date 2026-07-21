from django.test import TestCase

from pomodoro.forms import PomodoroStateForm
from pomodoro.models import Phase


class PomodoroStateFormTests(TestCase):
    def test_valid_state(self):
        form = PomodoroStateForm(
            data={
                "phase": Phase.SHORT,
                "running": True,
                "ends_at_ms": 1_800_000_000_000,
                "remaining": 300,
                "completed": 2,
            }
        )
        self.assertTrue(form.is_valid())

    def test_nullable_runtime_fields_are_optional(self):
        form = PomodoroStateForm(data={"phase": Phase.FOCUS, "completed": 0})
        self.assertTrue(form.is_valid())

    def test_invalid_phase_is_rejected(self):
        form = PomodoroStateForm(data={"phase": "siesta", "completed": 0})
        self.assertFalse(form.is_valid())
        self.assertIn("phase", form.errors)

    def test_negative_remaining_is_rejected(self):
        form = PomodoroStateForm(
            data={"phase": Phase.FOCUS, "remaining": -1, "completed": 0}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("remaining", form.errors)
