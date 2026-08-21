from typing import Literal

from django.utils import timezone
from mcp_server import MCPToolset

from tasks.forms import TaskForm
from tasks.models import DueFilter, Group, Task
from tasks.serializers import GroupSerializer, ParentTaskSerializer, TaskSerializer


class UserTasksToolset(MCPToolset):
    def get_user_unarchived_tasks(self):
        """Lists all unarchived user tasks"""
        parent_tasks = (
            Task.objects.filter_unarchived()
            .filter(user=self.request.user, parent__isnull=True)
            .prefetch_related('subtasks')
        )
        serializer = ParentTaskSerializer(parent_tasks, many=True)
        return serializer.data

    def get_user_archived_tasks(self):
        """Lists all archived user tasks"""
        parent_tasks = (
            Task.objects.filter_archived()
            .filter(user=self.request.user, parent__isnull=True)
            .prefetch_related('subtasks')
        )
        serializer = ParentTaskSerializer(parent_tasks, many=True)
        return serializer.data

    def get_tasks_due(self, due: Literal['today', 'overdue']):
        """Lists unarchived top level user tasks that are due today or overdue"""
        today = timezone.localdate()
        parent_tasks = (
            Task.objects.filter_unarchived()
            .filter(user=self.request.user, parent__isnull=True)
            .prefetch_related('subtasks')
        )

        if due == DueFilter.OVERDUE:
            parent_tasks = parent_tasks.filter(
                due_date__lt=today, completed_at__isnull=True
            )
        else:
            parent_tasks = parent_tasks.filter(due_date=today)

        serializer = ParentTaskSerializer(parent_tasks, many=True)
        return serializer.data

    def search_tasks(self, query: str, include_archived: bool = False):
        """Finds user tasks whose name contains the query. Matches subtasks too"""
        tasks = Task.objects.filter(user=self.request.user, name__icontains=query)

        if not include_archived:
            tasks = tasks.filter_unarchived()

        serializer = TaskSerializer(tasks.select_related('group'), many=True)
        return serializer.data

    def get_task_groups(self):
        """Lists the user task groups. Read a group id from here in order to place
        a task"""
        groups = Group.objects.filter(user=self.request.user)
        serializer = GroupSerializer(groups, many=True)
        return serializer.data

    def create_task(
        self,
        name: str,
        group_id: int | None = None,
        parent_id: int | None = None,
        due_date: str | None = None,
        weight: int = 0,
    ):
        """Creates a user task. due_date is YYYY-MM-DD. parent_id makes it a subtask,
        which takes no group and no due date. weight goes from 0 to 5"""
        form = TaskForm(
            {
                'name': name,
                'weight': weight,
                'group_id': group_id,
                'parent_id': parent_id,
                'due_date': due_date,
            },
            user=self.request.user,
        )
        if not form.is_valid():
            raise ValueError(form.errors.as_json())

        data = form.cleaned_data
        group = data['group']
        task = Task.objects.create(
            user=self.request.user,
            name=data['name'],
            weight=data['weight'],
            group=group,
            parent=data['parent'],
            due_date=data['due_date'],
            position=Task.next_position(self.request.user, data['parent']),
            group_position=(
                Task.next_group_position(self.request.user, group) if group else 0
            ),
        )

        serializer = TaskSerializer(task)
        return serializer.data

    def update_task(
        self,
        task_id: int,
        name: str,
        group_id: int | None = None,
        due_date: str | None = None,
        weight: int = 0,
    ):
        """Replaces the details of a user task. Send every field you want to keep:
        a field you leave out goes back to its default. due_date is YYYY-MM-DD.
        A subtask keeps no group and no due date. Use create_task for a new task"""
        task = Task.objects.filter(id=task_id, user=self.request.user).first()
        if task is None:
            raise ValueError(f'No task {task_id} found.')

        form = TaskForm(
            {
                'name': name,
                'weight': weight,
                'group_id': group_id,
                'parent_id': task.parent_id,
                'due_date': due_date,
            },
            user=self.request.user,
        )
        if not form.is_valid():
            raise ValueError(form.errors.as_json())

        data = form.cleaned_data
        group = data['group']

        if task.group_id != (group.id if group else None):
            task.group_position = (
                Task.next_group_position(self.request.user, group) if group else 0
            )

        task.name = data['name']
        task.weight = data['weight']
        task.group = group
        task.due_date = data['due_date']
        task.save(
            update_fields=['name', 'weight', 'group', 'due_date', 'group_position']
        )

        serializer = TaskSerializer(task)
        return serializer.data

    def set_task_complete(self, task_id: int, complete: bool = True):
        """Marks a user task complete or incomplete. Its subtasks follow it"""
        task = Task.objects.filter(id=task_id, user=self.request.user).first()
        if task is None:
            raise ValueError(f'No task {task_id} found.')

        task.set_complete_with_subtasks(complete)

        serializer = TaskSerializer(task)
        return serializer.data

    def archive_task(self, task_id: int):
        """Archives a completed user task and its subtasks. Prefer this over deleting"""
        task = Task.objects.filter(id=task_id, user=self.request.user).first()
        if task is None:
            raise ValueError(f'No task {task_id} found.')
        if not task.completed_at:
            raise ValueError(
                f'Task {task_id} is not complete, so it cannot be archived.'
            )

        task.set_archived_with_subtasks(True)

        serializer = TaskSerializer(task)
        return serializer.data
