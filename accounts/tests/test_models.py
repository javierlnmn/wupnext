from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import UserPreferences

from .factories import UserFactory


class CustomUserTests(TestCase):
    def test_email_must_be_unique(self):
        UserFactory(email="taken@example.com")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserFactory(email="taken@example.com")


class PreferencesSignalTests(TestCase):
    def test_preferences_created_with_user(self):
        user = UserFactory()
        self.assertTrue(UserPreferences.objects.filter(user=user).exists())

    def test_preferences_not_duplicated_on_update(self):
        user = UserFactory()
        user.first_name = "Javier"
        user.save()
        self.assertEqual(UserPreferences.objects.filter(user=user).count(), 1)

    def test_for_user_returns_signal_created_row(self):
        user = UserFactory()
        prefs = UserPreferences.for_user(user)
        self.assertEqual(prefs, user.preferences)
        self.assertEqual(UserPreferences.objects.filter(user=user).count(), 1)


class PomodoroDictTests(TestCase):
    def test_serializes_defaults(self):
        prefs = UserFactory().preferences
        self.assertEqual(
            prefs.pomodoro_dict(),
            {"focus": 25, "short": 5, "long": 15, "every": 4},
        )

    def test_serializes_custom_values(self):
        prefs = UserFactory().preferences
        prefs.pomodoro_focus = 50
        prefs.pomodoro_short_break = 10
        prefs.pomodoro_long_break = 20
        prefs.pomodoro_long_every = 3
        prefs.save()
        self.assertEqual(
            prefs.pomodoro_dict(),
            {"focus": 50, "short": 10, "long": 20, "every": 3},
        )
