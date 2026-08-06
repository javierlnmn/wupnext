from django.test import TestCase

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
MANDATORY_EVENT = 'account_password_reset'
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

        self.assertEqual(list(form.fields), ['sentinel', EMAIL_FIELD])
        self.assertEqual(form.cells, {EMAIL_FIELD: (EVENT, Channel.EMAIL)})


class MandatoryRowTests(TestCase):
    """A notification that isn't optional is never offered as a toggle."""

    def setUp(self):
        self.user = UserFactory()
        enable_notification(event=MANDATORY_EVENT)

    def test_gets_no_row_even_with_an_enabled_switch(self):
        rows = NotificationPreferencesForm(user=self.user).rows

        self.assertEqual(rows, [])

    def test_gets_no_field_even_with_an_enabled_switch(self):
        form = NotificationPreferencesForm(user=self.user)

        self.assertEqual(list(form.fields), ['sentinel'])
        self.assertEqual(form.cells, {})

    def test_a_posted_toggle_stores_nothing(self):
        field = f'notify-{MANDATORY_EVENT}-{Channel.EMAIL}'
        form = NotificationPreferencesForm(
            {'sentinel': '1', field: 'on'}, user=self.user
        )

        self.assertTrue(form.is_valid())
        form.save()

        self.assertFalse(
            NotificationUserPreference.objects.filter(event=MANDATORY_EVENT).exists()
        )


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
        form = NotificationPreferencesForm({'sentinel': '1', **data}, user=self.user)
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


class SentinelTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        enable_notification()
        NotificationUserPreferenceFactory(user=self.user, enabled=True)

    def test_a_post_without_the_sentinel_is_invalid(self):
        form = NotificationPreferencesForm({}, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn('sentinel', form.errors)

    def test_a_post_without_the_sentinel_changes_nothing(self):
        NotificationPreferencesForm({}, user=self.user).is_valid()

        self.assertTrue(NotificationUserPreference.objects.get(user=self.user).enabled)
