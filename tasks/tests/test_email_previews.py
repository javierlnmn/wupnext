from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.email_previews import PREVIEW_USERNAME, PREVIEWS, get_preview
from tasks.email_previews import TaskDueReminderPreview
from tasks.models import Group, Task
from tasks.tests.factories import TaskFactory

EVENT = 'task_due_reminder'


class TaskDueReminderPreviewTests(TestCase):
    def test_the_preview_registers_itself_for_the_event(self):
        self.assertIs(PREVIEWS[EVENT], TaskDueReminderPreview)
        self.assertIsInstance(get_preview(EVENT), TaskDueReminderPreview)

    def test_renders_the_seeded_overdue_and_due_today_sections(self):
        _, body, _ = TaskDueReminderPreview().render()

        self.assertIn(f'Hi {PREVIEW_USERNAME}', body)
        self.assertIn('OVERDUE (1)', body)
        self.assertIn('DUE TODAY (1)', body)

    def test_renders_subtask_progress_from_saved_rows(self):
        _, body, _ = TaskDueReminderPreview().render()

        self.assertIn('1/2 subtasks done', body)

    def test_ignores_existing_users_and_their_tasks(self):
        today = timezone.localdate()
        existing = UserFactory(email='existing@example.com')
        TaskFactory(
            user=existing, name='Real overdue', due_date=today - timedelta(days=1)
        )
        TaskFactory(user=existing, name='Real due today', due_date=today)

        _, body, _ = TaskDueReminderPreview().render()

        self.assertNotIn('Real overdue', body)
        self.assertNotIn('Real due today', body)

    def test_rolls_back_the_seeded_rows(self):
        TaskDueReminderPreview().render()

        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)
