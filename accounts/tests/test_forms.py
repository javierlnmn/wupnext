from django.test import TestCase

from accounts.forms import PreferencesForm

VALID = {
    "pomodoro_focus": 25,
    "pomodoro_short_break": 5,
    "pomodoro_long_break": 15,
    "pomodoro_long_every": 4,
}


class PreferencesFormTests(TestCase):
    def test_valid_settings(self):
        self.assertTrue(PreferencesForm(data=VALID).is_valid())

    def test_duration_below_minimum_is_invalid(self):
        form = PreferencesForm(data={**VALID, "pomodoro_focus": 0})
        self.assertFalse(form.is_valid())
        self.assertIn("pomodoro_focus", form.errors)

    def test_duration_above_maximum_is_invalid(self):
        form = PreferencesForm(data={**VALID, "pomodoro_short_break": 181})
        self.assertFalse(form.is_valid())
        self.assertIn("pomodoro_short_break", form.errors)

    def test_long_every_above_maximum_is_invalid(self):
        form = PreferencesForm(data={**VALID, "pomodoro_long_every": 13})
        self.assertFalse(form.is_valid())
        self.assertIn("pomodoro_long_every", form.errors)

    def test_boundary_values_are_valid(self):
        form = PreferencesForm(
            data={
                "pomodoro_focus": 1,
                "pomodoro_short_break": 180,
                "pomodoro_long_break": 180,
                "pomodoro_long_every": 12,
            }
        )
        self.assertTrue(form.is_valid())
