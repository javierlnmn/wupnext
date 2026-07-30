from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import UserFactory
from pomodoro.models import PomodoroUserPreference


class PomodoroUserPreferenceTests(TestCase):
    def test_for_user_creates_once(self):
        user = UserFactory()

        first = PomodoroUserPreference.for_user(user)
        second = PomodoroUserPreference.for_user(user)

        self.assertEqual(first, second)
        self.assertEqual(PomodoroUserPreference.objects.count(), 1)

    def test_settings_dict_serializes_defaults(self):
        preference = PomodoroUserPreference.for_user(UserFactory())

        self.assertEqual(
            preference.settings_dict(),
            {'focus': 25, 'short': 5, 'long': 15, 'every': 4},
        )

    def test_settings_dict_serializes_custom_values(self):
        preference = PomodoroUserPreference.for_user(UserFactory())
        preference.focus = 50
        preference.short_break = 10
        preference.long_break = 20
        preference.long_every = 3
        preference.save()

        self.assertEqual(
            preference.settings_dict(),
            {'focus': 50, 'short': 10, 'long': 20, 'every': 3},
        )


class PomodoroPreferencesViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse('pomodoro:preferences')

    def get_html(self):
        return self.client.get(self.url).content.decode()

    def test_requires_login(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_renders_the_current_values(self):
        preference = PomodoroUserPreference.for_user(self.user)
        preference.focus = 42
        preference.save()

        html = self.get_html()

        self.assertIn('name="focus"', html)
        self.assertIn('value="42"', html)

    def test_renders_fields_only_so_the_modal_owns_the_form(self):
        html = self.get_html()

        self.assertNotIn('<form', html)
        self.assertNotIn('type="submit"', html)
