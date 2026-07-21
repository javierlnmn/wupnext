from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.models import Task

from .factories import TaskFactory


class DueDatePropertiesTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def test_is_due_today_true_when_due_date_is_today(self):
        task = TaskFactory(due_date=self.today)
        self.assertTrue(task.is_due_today)

    def test_is_due_today_false_for_other_dates(self):
        yesterday = TaskFactory(due_date=self.today - timedelta(days=1))
        tomorrow = TaskFactory(due_date=self.today + timedelta(days=1))
        self.assertFalse(yesterday.is_due_today)
        self.assertFalse(tomorrow.is_due_today)

    def test_is_due_today_false_without_due_date(self):
        self.assertFalse(TaskFactory(due_date=None).is_due_today)

    def test_is_overdue_true_for_past_incomplete_task(self):
        task = TaskFactory(due_date=self.today - timedelta(days=1))
        self.assertTrue(task.is_overdue)

    def test_is_overdue_false_for_today(self):
        self.assertFalse(TaskFactory(due_date=self.today).is_overdue)

    def test_is_overdue_false_when_completed(self):
        task = TaskFactory(due_date=self.today - timedelta(days=1), completed=True)
        self.assertFalse(task.is_overdue)

    def test_is_overdue_false_without_due_date(self):
        self.assertFalse(TaskFactory(due_date=None).is_overdue)


class SubtaskCountTests(TestCase):
    def setUp(self):
        self.parent = TaskFactory()

    def test_counts_zero_without_subtasks(self):
        self.assertEqual(self.parent.subtask_count, 0)
        self.assertEqual(self.parent.completed_subtask_count, 0)

    def test_counts_reflect_subtasks(self):
        TaskFactory(user=self.parent.user, parent=self.parent)
        TaskFactory(user=self.parent.user, parent=self.parent, completed=True)
        parent = Task.objects.prefetch_related("subtasks").get(pk=self.parent.pk)
        self.assertEqual(parent.subtask_count, 2)
        self.assertEqual(parent.completed_subtask_count, 1)

    def test_counts_read_prefetch_cache_without_extra_queries(self):
        TaskFactory(user=self.parent.user, parent=self.parent, completed=True)
        parent = Task.objects.prefetch_related("subtasks").get(pk=self.parent.pk)
        with self.assertNumQueries(0):
            self.assertEqual(parent.subtask_count, 1)
            self.assertEqual(parent.completed_subtask_count, 1)


class TaskQuerySetTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.active = TaskFactory(user=self.user)
        self.archived = TaskFactory(user=self.user, archived=True)

    def test_filter_unarchived(self):
        qs = Task.objects.filter_unarchived()
        self.assertIn(self.active, qs)
        self.assertNotIn(self.archived, qs)

    def test_filter_archived(self):
        qs = Task.objects.filter_archived()
        self.assertIn(self.archived, qs)
        self.assertNotIn(self.active, qs)

    def test_filters_are_chainable(self):
        TaskFactory(user=self.user, archived=True)
        self.assertEqual(
            Task.objects.filter(user=self.user).filter_archived().count(), 2
        )
