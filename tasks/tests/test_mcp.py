from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.mcp import UserTasksToolset
from tasks.models import MAX_TASK_WEIGHT, Task

from .factories import GroupFactory, TaskFactory


class ToolsetTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        request = RequestFactory().post('/mcp')
        request.user = self.user
        self.tools = UserTasksToolset(request=request)
        self.today = timezone.localdate()


class GetTasksDueTests(ToolsetTestCase):
    def test_returns_a_task_due_today(self):
        TaskFactory(user=self.user, name='Today', due_date=self.today)
        TaskFactory(user=self.user, name='Tomorrow', due_date=self.today + timedelta(1))

        due = self.tools.get_tasks_due('today')

        self.assertEqual([task['name'] for task in due], ['Today'])

    def test_returns_an_overdue_task(self):
        TaskFactory(user=self.user, name='Late', due_date=self.today - timedelta(3))

        due = self.tools.get_tasks_due('overdue')

        self.assertEqual([task['name'] for task in due], ['Late'])

    def test_skips_an_overdue_task_that_is_already_complete(self):
        TaskFactory(
            user=self.user,
            name='Late but done',
            due_date=self.today - timedelta(3),
            completed=True,
        )

        self.assertEqual(self.tools.get_tasks_due('overdue'), [])

    def test_skips_an_archived_task(self):
        TaskFactory(user=self.user, due_date=self.today, archived=True)

        self.assertEqual(self.tools.get_tasks_due('today'), [])

    def test_skips_another_user_task(self):
        TaskFactory(user=UserFactory(), due_date=self.today)

        self.assertEqual(self.tools.get_tasks_due('today'), [])


class SearchTasksTests(ToolsetTestCase):
    def test_matches_regardless_of_case(self):
        TaskFactory(user=self.user, name='Buy Milk')

        found = self.tools.search_tasks('milk')

        self.assertEqual([task['name'] for task in found], ['Buy Milk'])

    def test_matches_a_subtask(self):
        parent = TaskFactory(user=self.user, name='Groceries')
        TaskFactory(user=self.user, name='Milk', parent=parent)

        found = self.tools.search_tasks('milk')

        self.assertEqual(found[0]['parent'], parent.id)

    def test_skips_an_archived_task_unless_asked(self):
        TaskFactory(user=self.user, name='Old milk', archived=True)

        self.assertEqual(self.tools.search_tasks('milk'), [])
        self.assertEqual(len(self.tools.search_tasks('milk', include_archived=True)), 1)

    def test_skips_another_user_task(self):
        TaskFactory(user=UserFactory(), name='Their milk')

        self.assertEqual(self.tools.search_tasks('milk'), [])


class GetTaskGroupsTests(ToolsetTestCase):
    def test_returns_only_the_user_groups(self):
        GroupFactory(user=self.user, name='Work')
        GroupFactory(user=UserFactory(), name='Theirs')

        groups = self.tools.get_task_groups()

        self.assertEqual([group['name'] for group in groups], ['Work'])


class CreateTaskTests(ToolsetTestCase):
    def test_creates_a_task_in_a_group_with_a_due_date(self):
        group = GroupFactory(user=self.user)

        created = self.tools.create_task(
            'Buy milk', group_id=group.id, due_date='2026-09-01'
        )

        task = Task.objects.get(id=created['id'])
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.group, group)
        self.assertEqual(str(task.due_date), '2026-09-01')

    def test_clamps_a_weight_above_the_maximum(self):
        created = self.tools.create_task('Heavy', weight=99)

        self.assertEqual(created['weight'], MAX_TASK_WEIGHT)

    def test_a_subtask_keeps_no_due_date(self):
        parent = TaskFactory(user=self.user)

        created = self.tools.create_task(
            'Milk', parent_id=parent.id, due_date='2026-09-01'
        )

        self.assertEqual(created['parent'], parent.id)
        self.assertIsNone(created['due_date'])

    def test_ignores_a_group_of_another_user(self):
        created = self.tools.create_task('Buy milk', group_id=GroupFactory().id)

        self.assertIsNone(created['group'])

    def test_ignores_a_parent_of_another_user(self):
        created = self.tools.create_task('Milk', parent_id=TaskFactory().id)

        self.assertIsNone(created['parent'])

    def test_a_blank_name_is_refused(self):
        with self.assertRaises(ValueError):
            self.tools.create_task('   ')

    def test_positions_follow_each_other(self):
        first = self.tools.create_task('First')
        second = self.tools.create_task('Second')

        self.assertEqual(
            Task.objects.get(id=second['id']).position,
            Task.objects.get(id=first['id']).position + 1,
        )


class UpdateTaskTests(ToolsetTestCase):
    def test_replaces_the_details(self):
        group = GroupFactory(user=self.user)
        task = TaskFactory(user=self.user, name='Old', weight=1)

        updated = self.tools.update_task(
            task.id, 'New', group_id=group.id, due_date='2026-09-01', weight=4
        )

        self.assertEqual(updated['name'], 'New')
        self.assertEqual(updated['weight'], 4)
        self.assertEqual(updated['group'], group.id)
        self.assertEqual(updated['due_date'], '2026-09-01')

    def test_an_omitted_field_goes_back_to_its_default(self):
        task = TaskFactory(user=self.user, weight=5, due_date=self.today)

        updated = self.tools.update_task(task.id, 'Renamed')

        self.assertEqual(updated['weight'], 0)
        self.assertIsNone(updated['due_date'])

    def test_a_subtask_keeps_no_group_and_no_due_date(self):
        parent = TaskFactory(user=self.user)
        subtask = TaskFactory(user=self.user, parent=parent)
        group = GroupFactory(user=self.user)

        updated = self.tools.update_task(
            subtask.id, 'Milk', group_id=group.id, due_date='2026-09-01'
        )

        self.assertEqual(updated['parent'], parent.id)
        self.assertIsNone(updated['group'])
        self.assertIsNone(updated['due_date'])

    def test_a_blank_name_is_refused(self):
        task = TaskFactory(user=self.user, name='Keep me')

        with self.assertRaises(ValueError):
            self.tools.update_task(task.id, '   ')

        task.refresh_from_db()
        self.assertEqual(task.name, 'Keep me')

    def test_another_user_task_is_refused(self):
        with self.assertRaises(ValueError):
            self.tools.update_task(TaskFactory().id, 'Mine now')


class SetTaskCompleteTests(ToolsetTestCase):
    def test_completing_a_task_completes_its_subtasks(self):
        parent = TaskFactory(user=self.user)
        subtask = TaskFactory(user=self.user, parent=parent)

        self.tools.set_task_complete(parent.id)

        subtask.refresh_from_db()
        self.assertIsNotNone(subtask.completed_at)

    def test_reopening_a_task_reopens_its_subtasks(self):
        parent = TaskFactory(user=self.user, completed=True)
        subtask = TaskFactory(user=self.user, parent=parent, completed=True)

        self.tools.set_task_complete(parent.id, complete=False)

        subtask.refresh_from_db()
        parent.refresh_from_db()
        self.assertIsNone(parent.completed_at)
        self.assertIsNone(subtask.completed_at)

    def test_another_user_task_is_refused(self):
        with self.assertRaises(ValueError):
            self.tools.set_task_complete(TaskFactory().id)


class ArchiveTaskTests(ToolsetTestCase):
    def test_archives_a_completed_task_and_its_subtasks(self):
        parent = TaskFactory(user=self.user, completed=True)
        subtask = TaskFactory(user=self.user, parent=parent, completed=True)

        self.tools.archive_task(parent.id)

        parent.refresh_from_db()
        subtask.refresh_from_db()
        self.assertIsNotNone(parent.archived_at)
        self.assertIsNotNone(subtask.archived_at)

    def test_an_incomplete_task_is_refused(self):
        task = TaskFactory(user=self.user)

        with self.assertRaises(ValueError):
            self.tools.archive_task(task.id)

    def test_another_user_task_is_refused(self):
        with self.assertRaises(ValueError):
            self.tools.archive_task(TaskFactory(completed=True).id)
