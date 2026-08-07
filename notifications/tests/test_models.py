from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.tests.factories import UserFactory
from notifications.models import (
    Channel,
    NotificationChannelSwitch,
    NotificationEventSwitch,
    NotificationLog,
    NotificationUserPreference,
)
from notifications.tests.factories import (
    NotificationChannelSwitchFactory,
    NotificationEventSwitchFactory,
    NotificationLogFactory,
    NotificationUserPreferenceFactory,
)

EVENT = 'task_due_reminder'
PUSH = 'push'


class NotificationLogTests(TestCase):
    def test_str(self):
        log = NotificationLogFactory(dedup_key='2026-07-23')
        self.assertEqual(
            str(log),
            f'task_due_reminder → {Channel.EMAIL} (2026-07-23)',
        )

    def test_unique_per_user_event_channel_key(self):
        user = UserFactory()
        NotificationLogFactory(user=user, dedup_key='2026-07-23')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationLogFactory(user=user, dedup_key='2026-07-23')

    def test_same_key_different_user_is_allowed(self):
        NotificationLogFactory(user=UserFactory(), dedup_key='2026-07-23')
        NotificationLogFactory(user=UserFactory(), dedup_key='2026-07-23')

    def test_keyless_rows_never_collide(self):
        user = UserFactory()

        NotificationLogFactory(user=user, dedup_key=None)
        NotificationLogFactory(user=user, dedup_key=None)

        self.assertEqual(NotificationLog.objects.count(), 2)

    def test_str_leaves_out_a_key_that_is_not_there(self):
        log = NotificationLogFactory(dedup_key=None)

        self.assertEqual(str(log), f'task_due_reminder → {Channel.EMAIL}')


class NotificationChannelSwitchTests(TestCase):
    def test_str(self):
        switch = NotificationChannelSwitchFactory()
        self.assertEqual(str(switch), f'{Channel.EMAIL}: on')

    def test_channel_is_unique(self):
        NotificationChannelSwitch.objects.create(channel=Channel.EMAIL)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationChannelSwitch.objects.create(channel=Channel.EMAIL)


class NotificationEventSwitchTests(TestCase):
    def test_str(self):
        switch = NotificationEventSwitchFactory()
        self.assertEqual(str(switch), f'{EVENT} → {Channel.EMAIL}: on')

    def test_unique_per_event_and_channel(self):
        NotificationEventSwitch.objects.create(event=EVENT, channel=Channel.EMAIL)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationEventSwitch.objects.create(
                    event=EVENT, channel=Channel.EMAIL
                )

    def test_enabled_channels_without_any_row(self):
        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {},
        )

    def test_enabled_channels_maps_to_the_user_default(self):
        NotificationChannelSwitchFactory()
        switch = NotificationEventSwitchFactory(on_by_default=True)
        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {Channel.EMAIL: True},
        )

        switch.on_by_default = False
        switch.save()
        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {Channel.EMAIL: False},
        )

    def test_enabled_channels_needs_the_event_switch(self):
        NotificationChannelSwitchFactory()
        NotificationEventSwitchFactory(enabled=False)

        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {},
        )

    def test_enabled_channels_needs_the_channel_switch(self):
        NotificationChannelSwitchFactory(enabled=False)
        NotificationEventSwitchFactory(enabled=True)

        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {},
        )

    def test_enabled_channels_drops_only_the_channel_that_is_off(self):
        NotificationChannelSwitchFactory(channel=Channel.EMAIL, enabled=False)
        NotificationChannelSwitchFactory(channel=PUSH, enabled=True)
        NotificationEventSwitchFactory(channel=Channel.EMAIL)
        NotificationEventSwitchFactory(channel=PUSH, on_by_default=False)

        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {PUSH: False},
        )

    def test_enabled_channels_ignores_another_event(self):
        NotificationChannelSwitchFactory()
        NotificationEventSwitchFactory(event='other_event')

        self.assertEqual(
            NotificationEventSwitch.get_enabled_channels_defaults_for_event(EVENT),
            {},
        )


class NotificationUserPreferenceTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_str(self):
        preference = NotificationUserPreferenceFactory(user=self.user, enabled=False)
        self.assertEqual(str(preference), f'{EVENT} → {Channel.EMAIL}: off')

    def test_unique_per_user_event_and_channel(self):
        NotificationUserPreference.objects.create(
            user=self.user, event=EVENT, channel=Channel.EMAIL, enabled=True
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationUserPreference.objects.create(
                    user=self.user, event=EVENT, channel=Channel.EMAIL, enabled=False
                )


class BulkUserStoredPreferencesTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other = UserFactory()

    def stored(self, channels=(Channel.EMAIL,)):
        return NotificationUserPreference.get_bulk_user_stored_preferences_for_event(
            [self.user, self.other], EVENT, channels
        )

    def test_empty_when_nobody_chose(self):
        self.assertEqual(self.stored(), {})

    def test_nests_channels_under_each_user(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)
        NotificationUserPreferenceFactory(user=self.other, enabled=True)

        self.assertEqual(
            self.stored(),
            {
                self.user.pk: {Channel.EMAIL: False},
                self.other.pk: {Channel.EMAIL: True},
            },
        )

    def test_groups_several_channels_under_one_user(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)
        NotificationUserPreferenceFactory(user=self.user, channel=PUSH, enabled=True)

        self.assertEqual(
            self.stored(channels=(Channel.EMAIL, PUSH)),
            {self.user.pk: {Channel.EMAIL: False, PUSH: True}},
        )

    def test_excludes_another_event(self):
        NotificationUserPreferenceFactory(
            user=self.user, event='other_event', enabled=False
        )

        self.assertEqual(self.stored(), {})

    def test_excludes_a_channel_not_asked_for(self):
        NotificationUserPreferenceFactory(user=self.user, channel=PUSH, enabled=False)

        self.assertEqual(self.stored(), {})

    def test_reads_the_whole_batch_in_one_query(self):
        for _ in range(5):
            UserFactory()

        users = list(get_user_model().objects.all())

        with self.assertNumQueries(1):
            NotificationUserPreference.get_bulk_user_stored_preferences_for_event(
                users, EVENT, (Channel.EMAIL,)
            )


class UserStoredPreferencesTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def stored(self, channels=(Channel.EMAIL,)):
        return NotificationUserPreference.get_user_stored_preferences_for_event(
            self.user, EVENT, channels
        )

    def test_empty_when_the_user_never_chose(self):
        self.assertEqual(self.stored(), {})

    def test_keys_by_channel_alone(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        self.assertEqual(self.stored(), {Channel.EMAIL: False})

    def test_includes_every_channel_asked_for(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=False)
        NotificationUserPreferenceFactory(user=self.user, channel=PUSH, enabled=True)

        self.assertEqual(
            self.stored(channels=(Channel.EMAIL, PUSH)),
            {Channel.EMAIL: False, PUSH: True},
        )

    def test_excludes_another_users_preference(self):
        NotificationUserPreferenceFactory(user=UserFactory(), enabled=False)

        self.assertEqual(self.stored(), {})

    def test_excludes_another_event(self):
        NotificationUserPreferenceFactory(
            user=self.user, event='other_event', enabled=False
        )

        self.assertEqual(self.stored(), {})

    def test_costs_one_query(self):
        with self.assertNumQueries(1):
            self.stored(channels=(Channel.EMAIL, PUSH))
