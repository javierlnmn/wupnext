from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.exceptions import MissingPreview
from notifications.models import NotificationEvent
from notifications.previews import BaseEmailPreview, build_registry, preview_context
from tasks.models import Group, Task
from tasks.tests.factories import TaskFactory

EVENT = NotificationEvent.TASK_DUE_REMINDER.value


class PreviewContextTests(TestCase):
    def test_raises_when_no_preview_is_registered(self):
        with self.assertRaises(MissingPreview):
            with preview_context("nope"):
                pass

    def test_error_names_the_event_and_the_alternatives(self):
        with self.assertRaises(MissingPreview) as caught:
            with preview_context("nope"):
                pass

        message = str(caught.exception)
        self.assertIn("nope", message)
        self.assertIn(EVENT, message)

    def test_builds_context_from_seeded_rows(self):
        with preview_context(EVENT) as context:
            self.assertEqual(len(context["overdue"]), 1)
            self.assertEqual(len(context["due_today"]), 1)
            self.assertEqual(context["overdue"][0].subtask_count, 2)
            self.assertEqual(context["overdue"][0].completed_subtask_count, 1)

    def test_ignores_existing_users_and_their_tasks(self):
        today = timezone.localdate()
        existing = UserFactory(email="existing@example.com")
        TaskFactory(
            user=existing, name="Real overdue", due_date=today - timedelta(days=1)
        )
        TaskFactory(user=existing, name="Real due today", due_date=today)

        with preview_context(EVENT) as context:
            self.assertNotEqual(context["user"], existing)
            names = [
                task.name for task in context["overdue"] + context["due_today"]
            ]
            self.assertNotIn("Real overdue", names)
            self.assertNotIn("Real due today", names)

    def test_rolls_back_the_seeded_rows(self):
        with preview_context(EVENT):
            self.assertTrue(Task.objects.exists())

        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)


class StubPreview(BaseEmailPreview):
    def seed(self):
        pass

    def context(self):
        return {}


class BuildRegistryTests(TestCase):
    def test_rejects_a_preview_without_an_event(self):
        class Unnamed(StubPreview):
            pass

        with self.assertRaises(ImproperlyConfigured):
            build_registry(Unnamed())

    def test_keys_previews_by_event(self):
        class Named(StubPreview):
            event = "something"

        registry = build_registry(Named())

        self.assertEqual(sorted(registry), ["something"])

    def test_cannot_instantiate_a_preview_without_its_hooks(self):
        class Hookless(BaseEmailPreview):
            event = "hookless"

        with self.assertRaises(TypeError):
            Hookless()
