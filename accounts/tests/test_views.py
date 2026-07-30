from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.tests.factories import UserFactory
from notifications.models import Channel, NotificationUserPreference
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)
from pomodoro.models import PomodoroUserPreference

EVENT = 'task_due_reminder'
EMAIL_FIELD = f'notify-{EVENT}-{Channel.EMAIL}'


class PreferencesViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse('accounts:preferences')
        enable_notification()

    def payload(self, **overrides):
        data = {
            'focus': 30,
            'short_break': 10,
            'long_break': 20,
            'long_every': 3,
            'sentinel': '1',
        }
        data.update(overrides)
        return data

    def pomodoro(self):
        return PomodoroUserPreference.for_user(self.user)

    def test_requires_login(self):
        self.client.logout()

        self.assertEqual(self.client.post(self.url).status_code, 302)

    def test_one_post_saves_both_tabs(self):
        response = self.client.post(self.url, self.payload(**{EMAIL_FIELD: 'on'}))

        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(self.pomodoro().focus, 30)
        self.assertTrue(NotificationUserPreference.objects.get(user=self.user).enabled)

    def test_an_unchecked_toggle_is_stored_as_an_opt_out(self):
        response = self.client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(NotificationUserPreference.objects.get(user=self.user).enabled)

    def test_an_invalid_duration_saves_neither_tab(self):
        response = self.client.post(
            self.url, self.payload(focus=999, **{EMAIL_FIELD: 'on'})
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('focus', response.json()['errors'])
        self.assertEqual(self.pomodoro().focus, 25)
        self.assertFalse(NotificationUserPreference.objects.exists())

    def test_a_missing_notifications_sentinel_saves_neither_tab(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=True)
        payload = self.payload()
        payload.pop('sentinel')

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn('sentinel', response.json()['errors'])
        self.assertEqual(self.pomodoro().focus, 25)
        self.assertTrue(NotificationUserPreference.objects.get(user=self.user).enabled)

    def test_reports_errors_from_both_tabs_together(self):
        payload = self.payload(focus=999)
        payload.pop('sentinel')

        errors = self.client.post(self.url, payload).json()['errors']

        self.assertIn('focus', errors)
        self.assertIn('sentinel', errors)


@override_settings(
    STORAGES={
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class PreferencesModalTests(TestCase):
    def setUp(self):
        self.client.force_login(UserFactory())

    def board(self):
        return self.client.get(reverse('tasks:board')).content.decode()

    def test_both_tabs_fetch_their_own_partial_on_open(self):
        html = self.board()

        self.assertIn(f'hx-get="{reverse("pomodoro:preferences")}"', html)
        self.assertIn(f'hx-get="{reverse("notifications:preferences")}"', html)
        self.assertEqual(html.count('hx-trigger="open-preferences from:window"'), 2)

    def test_one_form_posts_everything_to_the_central_view(self):
        html = self.board()

        self.assertEqual(html.count(f'hx-post="{reverse("accounts:preferences")}"'), 1)

    def test_the_single_save_button_sits_inside_that_form(self):
        html = self.board()

        form_at = html.index(f'hx-post="{reverse("accounts:preferences")}"')
        form_end = html.index('</form>', form_at)
        preferences_form = html[form_at:form_end]

        self.assertEqual(preferences_form.count('type="submit"'), 1)
        self.assertIn('Save', preferences_form)

    def test_the_board_renders_no_preference_fields_itself(self):
        enable_notification()

        html = self.board()

        self.assertNotIn(f'name="{EMAIL_FIELD}"', html)
        self.assertNotIn('name="focus"', html)


class MissingTabTests(PreferencesViewTests):
    """A tab that never rendered must not be read as "the user cleared it"."""

    def test_a_missing_pomodoro_tab_saves_neither_tab(self):
        payload = {'sentinel': '1', EMAIL_FIELD: 'on'}

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn('focus', response.json()['errors'])
        self.assertEqual(self.pomodoro().focus, 25)
        self.assertFalse(NotificationUserPreference.objects.exists())
