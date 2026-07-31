from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.email_previews import PREVIEW_USERNAME, PREVIEWS, get_preview
from tasks.models import Group, Task
from tasks.notifications.email_previews import (
    TaskDueReminderPreview,
    TaskMonthlySummaryPreview,
)
from tasks.tests.factories import TaskFactory

EVENT = 'task_due_reminder'
MONTHLY_EVENT = 'task_monthly_summary'


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


class TaskMonthlySummaryPreviewTests(TestCase):
    def test_the_preview_registers_itself_for_the_event(self):
        self.assertIs(PREVIEWS[MONTHLY_EVENT], TaskMonthlySummaryPreview)
        self.assertIsInstance(get_preview(MONTHLY_EVENT), TaskMonthlySummaryPreview)

    def test_renders_every_section(self):
        _, body, _ = TaskMonthlySummaryPreview().render()

        self.assertIn(f'Hi {PREVIEW_USERNAME}', body)
        self.assertIn('COMPLETED (3)', body)
        self.assertIn('OVERDUE (1)', body)
        self.assertIn('STILL OPEN (2)', body)

    def test_shows_the_target_comparison_both_ways(self):
        _, body, _ = TaskMonthlySummaryPreview().render()

        self.assertIn('early', body)
        self.assertIn('late', body)
        self.assertIn('no target', body)

    def test_rolls_back_the_seeded_rows(self):
        TaskMonthlySummaryPreview().render()

        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)

    def test_renders_an_html_alternative(self):
        _, _, html = TaskMonthlySummaryPreview().render()

        self.assertIn('<!doctype html>', html)
        self.assertIn('Completed &middot; 3', html)
        self.assertIn('Overdue &middot; 1', html)
        self.assertIn('Still open &middot; 2', html)

    def test_the_html_badges_every_target_comparison(self):
        _, _, html = TaskMonthlySummaryPreview().render()

        for badge in ('3d early', '4d late', 'No target', 'No deadline'):
            with self.subTest(badge=badge):
                self.assertIn(f'>{badge}</span>', html)

    def test_the_html_leads_with_the_month_totals(self):
        _, _, html = TaskMonthlySummaryPreview().render()

        for label in ('Completed', 'Weight', 'Overdue', 'Open'):
            with self.subTest(label=label):
                self.assertIn(f'{label}</div>', html)
