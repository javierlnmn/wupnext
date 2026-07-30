from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.tests.factories import UserFactory
from notifications.forms import NotificationPreferencesForm
from notifications.models import Channel, NotificationUserPreference
from notifications.tests.factories import (
    NotificationChannelSwitchFactory,
    NotificationEventSwitchFactory,
    NotificationUserPreferenceFactory,
    enable_notification,
)

EVENT = 'task_due_reminder'
PUSH = 'push'
EMAIL_FIELD = f'notify-{EVENT}-{Channel.EMAIL}'
PUSH_FIELD = f'notify-{EVENT}-{PUSH}'


class MatrixShapeTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def form(self):
        return NotificationPreferencesForm(user=self.user)

    def test_no_rows_without_any_switch(self):
        form = self.form()

        self.assertEqual(form.channels, [])
        self.assertEqual(form.rows, [])

    def test_a_column_per_enabled_channel(self):
        NotificationChannelSwitchFactory(channel=Channel.EMAIL)

        self.assertEqual(
            self.form().channels, [{'key': Channel.EMAIL, 'label': 'Email'}]
        )

    def test_a_disabled_channel_is_not_a_column(self):
        NotificationChannelSwitchFactory(channel=Channel.EMAIL, enabled=False)

        self.assertEqual(self.form().channels, [])

    def test_a_channel_the_code_does_not_implement_is_not_a_column(self):
        NotificationChannelSwitchFactory(channel=PUSH)

        self.assertEqual(self.form().channels, [])

    def test_a_row_per_event_with_a_cell_the_site_allows(self):
        enable_notification()

        rows = self.form().rows

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['label'], 'Deadline reminders')
        self.assertEqual(len(rows[0]['cells']), 1)

    def test_an_event_switched_off_gets_no_row(self):
        NotificationChannelSwitchFactory()
        NotificationEventSwitchFactory(enabled=False)

        self.assertEqual(self.form().rows, [])

    def test_a_cell_is_unavailable_when_the_site_does_not_allow_the_pair(self):
        enable_notification()

        self.assertEqual(
            self.form()._build_cell(EVENT, PUSH, {}, {}), {'available': False}
        )

    def test_only_available_cells_become_fields(self):
        enable_notification()

        form = self.form()

        self.assertEqual(list(form.fields), [EMAIL_FIELD])
        self.assertEqual(form.cells, {EMAIL_FIELD: (EVENT, Channel.EMAIL)})


class MatrixValueTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()

    def cell(self):
        return NotificationPreferencesForm(user=self.user).rows[0]['cells'][0]

    def test_shows_the_site_default_when_the_user_never_chose(self):
        self.assertTrue(self.cell()['enabled'])

    def test_shows_off_when_the_default_is_off(self):
        self.event_switch.on_by_default = False
        self.event_switch.save()

        self.assertFalse(self.cell()['enabled'])

    def test_shows_the_users_own_choice_over_the_default(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        self.assertFalse(self.cell()['enabled'])

    def test_ignores_another_users_choice(self):
        NotificationUserPreferenceFactory(user=UserFactory(), enabled=False)

        self.assertTrue(self.cell()['enabled'])


class SaveTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.channel_switch, self.event_switch = enable_notification()

    def save(self, data):
        form = NotificationPreferencesForm(data, user=self.user)
        self.assertTrue(form.is_valid())
        form.save()

    def stored(self):
        return NotificationUserPreference.objects.get(
            user=self.user, event=EVENT, channel=Channel.EMAIL
        ).enabled

    def test_a_checked_box_stores_an_opt_in(self):
        self.save({EMAIL_FIELD: 'on'})

        self.assertTrue(self.stored())

    def test_an_unchecked_box_stores_an_opt_out(self):
        self.save({})

        self.assertFalse(self.stored())

    def test_saving_twice_updates_rather_than_duplicates(self):
        self.save({EMAIL_FIELD: 'on'})
        self.save({})

        self.assertEqual(NotificationUserPreference.objects.count(), 1)
        self.assertFalse(self.stored())

    def test_stores_nothing_for_a_cell_the_site_does_not_allow(self):
        self.save({PUSH_FIELD: 'on'})

        self.assertFalse(
            NotificationUserPreference.objects.filter(channel=PUSH).exists()
        )


class MatrixTagTests(TestCase):
    def render(self, user):
        request = RequestFactory().get('/')
        request.user = user
        template = Template(
            '{% load notification_preferences %}{% notification_preferences_matrix %}'
        )
        return template.render(Context({'request': request}))

    def test_renders_a_toggle_per_available_cell(self):
        enable_notification()
        user = UserFactory()

        html = self.render(user)

        self.assertIn(f'name="{EMAIL_FIELD}"', html)
        self.assertIn('checked', html)
        self.assertIn('Email', html)

    def test_says_so_when_nothing_is_switched_on(self):
        html = self.render(UserFactory())

        self.assertIn('No notifications are switched on', html)

    def test_renders_nothing_for_an_anonymous_visitor(self):
        from django.contrib.auth.models import AnonymousUser

        enable_notification()

        html = self.render(AnonymousUser())

        self.assertNotIn(f'name="{EMAIL_FIELD}"', html)


@override_settings(
    STORAGES={
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class BoardIntegrationTests(TestCase):
    def get_board(self):
        self.client.force_login(UserFactory())
        return self.client.get(reverse('tasks:board')).content.decode()

    def test_the_matrix_reaches_the_preferences_form_on_the_board(self):
        enable_notification()

        html = self.get_board()

        self.assertIn(f'name="{EMAIL_FIELD}"', html)
        self.assertIn('Deadline reminders', html)

    def test_the_checkbox_sits_inside_the_preferences_form(self):
        enable_notification()

        html = self.get_board()

        form_at = html.index(f'hx-post="{reverse("accounts:preferences")}"')
        checkbox_at = html.index(f'name="{EMAIL_FIELD}"')

        self.assertGreater(checkbox_at, form_at)
