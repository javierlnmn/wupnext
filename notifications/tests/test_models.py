from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.tests.factories import UserFactory
from notifications.models import Channel
from notifications.tests.factories import NotificationLogFactory


class NotificationLogTests(TestCase):
    def test_str(self):
        log = NotificationLogFactory(dedup_key="2026-07-23")
        self.assertEqual(
            str(log),
            f"task_due_reminder → {Channel.EMAIL} (2026-07-23)",
        )

    def test_unique_per_user_event_channel_key(self):
        user = UserFactory()
        NotificationLogFactory(user=user, dedup_key="2026-07-23")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationLogFactory(user=user, dedup_key="2026-07-23")

    def test_same_key_different_user_is_allowed(self):
        NotificationLogFactory(user=UserFactory(), dedup_key="2026-07-23")
        NotificationLogFactory(user=UserFactory(), dedup_key="2026-07-23")
