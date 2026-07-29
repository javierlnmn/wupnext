from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.tests.factories import UserFactory
from notifications.models import (
    Channel,
    NotificationChannelSwitch,
    NotificationEventSwitch,
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


class NotificationChannelSwitchTests(TestCase):
    def test_str(self):
        switch = NotificationChannelSwitchFactory()
        self.assertEqual(str(switch), f'{Channel.EMAIL}: on')

    def test_is_enabled_without_a_row(self):
        self.assertFalse(NotificationChannelSwitch.is_enabled(Channel.EMAIL))

    def test_is_enabled_follows_the_row(self):
        switch = NotificationChannelSwitchFactory()
        self.assertTrue(NotificationChannelSwitch.is_enabled(Channel.EMAIL))

        switch.enabled = False
        switch.save()
        self.assertFalse(NotificationChannelSwitch.is_enabled(Channel.EMAIL))

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

    def test_is_enabled_for_channel_without_a_row(self):
        self.assertFalse(
            NotificationEventSwitch.is_enabled_for_channel(EVENT, Channel.EMAIL)
        )

    def test_is_enabled_for_channel_follows_the_row(self):
        switch = NotificationEventSwitchFactory()
        self.assertTrue(
            NotificationEventSwitch.is_enabled_for_channel(EVENT, Channel.EMAIL)
        )

        switch.enabled = False
        switch.save()
        self.assertFalse(
            NotificationEventSwitch.is_enabled_for_channel(EVENT, Channel.EMAIL)
        )

    def test_is_enabled_anywhere_ignores_which_channel_is_on(self):
        NotificationEventSwitchFactory(channel=Channel.EMAIL, enabled=False)
        NotificationEventSwitchFactory(channel=PUSH, enabled=True)

        self.assertTrue(NotificationEventSwitch.is_enabled_anywhere(EVENT))
        self.assertFalse(
            NotificationEventSwitch.is_enabled_for_channel(EVENT, Channel.EMAIL)
        )

    def test_is_enabled_anywhere_when_every_channel_is_off(self):
        NotificationEventSwitchFactory(enabled=False)

        self.assertFalse(NotificationEventSwitch.is_enabled_anywhere(EVENT))

    def test_default_for_needs_both_flags(self):
        switch = NotificationEventSwitchFactory(enabled=True, on_by_default=True)
        self.assertTrue(NotificationEventSwitch.default_for(EVENT, Channel.EMAIL))

        switch.on_by_default = False
        switch.save()
        self.assertFalse(NotificationEventSwitch.default_for(EVENT, Channel.EMAIL))

        switch.enabled = False
        switch.on_by_default = True
        switch.save()
        self.assertFalse(NotificationEventSwitch.default_for(EVENT, Channel.EMAIL))


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

    def test_falls_back_to_the_site_default(self):
        NotificationEventSwitchFactory(on_by_default=True)

        self.assertTrue(
            NotificationUserPreference.is_enabled_for_channel(
                self.user, EVENT, Channel.EMAIL
            )
        )

    def test_falls_back_to_off_when_not_on_by_default(self):
        NotificationEventSwitchFactory(on_by_default=False)

        self.assertFalse(
            NotificationUserPreference.is_enabled_for_channel(
                self.user, EVENT, Channel.EMAIL
            )
        )

    def test_an_explicit_choice_beats_the_default(self):
        NotificationEventSwitchFactory(on_by_default=True)
        NotificationUserPreferenceFactory(user=self.user, enabled=False)

        self.assertFalse(
            NotificationUserPreference.is_enabled_for_channel(
                self.user, EVENT, Channel.EMAIL
            )
        )

    def test_an_explicit_opt_in_beats_an_off_default(self):
        NotificationEventSwitchFactory(on_by_default=False)
        NotificationUserPreferenceFactory(user=self.user, enabled=True)

        self.assertTrue(
            NotificationUserPreference.is_enabled_for_channel(
                self.user, EVENT, Channel.EMAIL
            )
        )

    def test_another_users_choice_does_not_leak(self):
        NotificationEventSwitchFactory(on_by_default=True)
        NotificationUserPreferenceFactory(user=UserFactory(), enabled=False)

        self.assertTrue(
            NotificationUserPreference.is_enabled_for_channel(
                self.user, EVENT, Channel.EMAIL
            )
        )

    def test_is_enabled_for_any_channel_needs_only_one(self):
        NotificationEventSwitchFactory(channel=Channel.EMAIL, on_by_default=False)
        NotificationEventSwitchFactory(channel=PUSH, on_by_default=True)

        self.assertTrue(
            NotificationUserPreference.is_enabled_for_any_channel(
                self.user, EVENT, [Channel.EMAIL, PUSH]
            )
        )

    def test_is_enabled_for_any_channel_when_all_are_off(self):
        NotificationEventSwitchFactory(channel=Channel.EMAIL, on_by_default=False)
        NotificationEventSwitchFactory(channel=PUSH, on_by_default=False)

        self.assertFalse(
            NotificationUserPreference.is_enabled_for_any_channel(
                self.user, EVENT, [Channel.EMAIL, PUSH]
            )
        )

    def test_is_enabled_for_any_channel_without_channels(self):
        self.assertFalse(
            NotificationUserPreference.is_enabled_for_any_channel(self.user, EVENT, [])
        )
