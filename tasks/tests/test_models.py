from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.models import Group, Task

from .factories import GroupFactory, TaskFactory


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
        parent = Task.objects.prefetch_related('subtasks').get(pk=self.parent.pk)
        self.assertEqual(parent.subtask_count, 2)
        self.assertEqual(parent.completed_subtask_count, 1)

    def test_counts_read_prefetch_cache_without_extra_queries(self):
        TaskFactory(user=self.parent.user, parent=self.parent, completed=True)
        parent = Task.objects.prefetch_related('subtasks').get(pk=self.parent.pk)
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


class NextPositionTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_next_position_starts_at_zero(self):
        self.assertEqual(Task.next_position(self.user, None), 0)
        self.assertEqual(Group.next_position(self.user), 0)

    def test_next_position_is_one_past_the_highest(self):
        TaskFactory(user=self.user, position=0)
        TaskFactory(user=self.user, position=4)
        self.assertEqual(Task.next_position(self.user, None), 5)

    def test_next_position_is_scoped_per_parent(self):
        parent = TaskFactory(user=self.user)
        TaskFactory(user=self.user, parent=parent, position=2)
        self.assertEqual(Task.next_position(self.user, parent), 3)
        self.assertEqual(Task.next_position(self.user, None), 1)

    def test_next_group_position_scoped_to_group(self):
        group = GroupFactory(user=self.user)
        other = GroupFactory(user=self.user)
        TaskFactory(user=self.user, group=group, group_position=0)
        TaskFactory(user=self.user, group=group, group_position=1)
        self.assertEqual(Task.next_group_position(self.user, group), 2)
        self.assertEqual(Task.next_group_position(self.user, other), 0)

    def test_group_next_position_ignores_other_users(self):
        GroupFactory(user=UserFactory(), position=9)
        self.assertEqual(Group.next_position(self.user), 0)


class SetCompleteWithSubtasksTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.parent = TaskFactory(user=self.user)
        self.subtask = TaskFactory(user=self.user, parent=self.parent)

    def test_completing_cascades_to_subtasks(self):
        self.parent.set_complete_with_subtasks(True)
        self.subtask.refresh_from_db()
        self.assertIsNotNone(self.parent.completed_at)
        self.assertIsNotNone(self.subtask.completed_at)

    def test_reopening_cascades_to_subtasks(self):
        self.parent.set_complete_with_subtasks(True)
        self.parent.set_complete_with_subtasks(False)
        self.subtask.refresh_from_db()
        self.assertIsNone(self.parent.completed_at)
        self.assertIsNone(self.subtask.completed_at)

    def test_the_parent_change_is_saved(self):
        self.parent.set_complete_with_subtasks(True)
        self.parent.refresh_from_db()
        self.assertIsNotNone(self.parent.completed_at)

    def test_does_not_touch_another_task_subtasks(self):
        other_parent = TaskFactory(user=self.user)
        other_subtask = TaskFactory(user=self.user, parent=other_parent)
        self.parent.set_complete_with_subtasks(True)
        other_subtask.refresh_from_db()
        self.assertIsNone(other_subtask.completed_at)


class SetArchivedWithSubtasksTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.parent = TaskFactory(user=self.user, completed=True)
        self.subtask = TaskFactory(user=self.user, parent=self.parent, completed=True)

    def test_archiving_cascades_to_subtasks(self):
        self.parent.set_archived_with_subtasks(True)
        self.subtask.refresh_from_db()
        self.assertIsNotNone(self.parent.archived_at)
        self.assertIsNotNone(self.subtask.archived_at)

    def test_unarchiving_cascades_to_subtasks(self):
        self.parent.set_archived_with_subtasks(True)
        self.parent.set_archived_with_subtasks(False)
        self.subtask.refresh_from_db()
        self.assertIsNone(self.parent.archived_at)
        self.assertIsNone(self.subtask.archived_at)

    def test_the_parent_change_is_saved(self):
        self.parent.set_archived_with_subtasks(True)
        self.parent.refresh_from_db()
        self.assertIsNotNone(self.parent.archived_at)

    def test_a_subtask_shares_the_parent_timestamp(self):
        self.parent.set_archived_with_subtasks(True)
        self.parent.refresh_from_db()
        self.subtask.refresh_from_db()
        self.assertEqual(self.subtask.archived_at, self.parent.archived_at)

    def test_does_not_touch_another_task_subtasks(self):
        other_parent = TaskFactory(user=self.user, completed=True)
        other_subtask = TaskFactory(user=self.user, parent=other_parent, completed=True)
        self.parent.set_archived_with_subtasks(True)
        other_subtask.refresh_from_db()
        self.assertIsNone(other_subtask.archived_at)
