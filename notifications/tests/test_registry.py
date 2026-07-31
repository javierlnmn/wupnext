from django.test import TestCase

from notifications.exceptions import DuplicateNotification
from notifications.registry import NOTIFICATIONS, register
from tasks.notifications.notifications.due_reminders import DueReminderNotification


class RegistryTests(TestCase):
    def setUp(self):
        self.addCleanup(NOTIFICATIONS.pop, 'registry_test_event', None)

    def test_the_due_reminder_registers_itself(self):
        self.assertIs(NOTIFICATIONS['task_due_reminder'], DueReminderNotification)

    def test_register_returns_the_class_untouched(self):
        class Host:
            event = 'registry_test_event'

        self.assertIs(register(Host), Host)
        self.assertIs(NOTIFICATIONS['registry_test_event'], Host)

    def test_registering_the_same_class_twice_is_allowed(self):
        class Host:
            event = 'registry_test_event'

        register(Host)
        register(Host)

        self.assertIs(NOTIFICATIONS['registry_test_event'], Host)

    def test_two_notifications_cannot_claim_one_event(self):
        class First:
            event = 'registry_test_event'

        class Second:
            event = 'registry_test_event'

        register(First)

        with self.assertRaises(DuplicateNotification) as caught:
            register(Second)

        self.assertIn('First', str(caught.exception))

    def test_a_notification_without_an_event_is_rejected(self):
        class Eventless:
            event = None

        with self.assertRaises(ValueError):
            register(Eventless)
