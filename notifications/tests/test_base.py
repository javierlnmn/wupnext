from django.test import TestCase

from notifications.base import BaseBulkNotification, BaseNotification


class NotificationContractTests(TestCase):
    def test_cannot_instantiate_a_notification_without_its_hooks(self):
        class Hookless(BaseNotification):
            event = 'task_due_reminder'

        with self.assertRaises(TypeError):
            Hookless()

    def test_a_notification_declares_every_hook_itself(self):
        self.assertEqual(
            BaseNotification.__abstractmethods__,
            frozenset({'context', 'is_applicable_for', 'dedup_key'}),
        )

    def test_a_bulk_notification_also_declares_its_recipients(self):
        self.assertIn('recipients', BaseBulkNotification.__abstractmethods__)

    def test_a_notification_does_not_send_itself(self):
        for entry_point in ('send', 'send_bulk', 'enqueue', 'notify'):
            with self.subTest(entry_point=entry_point):
                self.assertFalse(hasattr(BaseBulkNotification, entry_point))
