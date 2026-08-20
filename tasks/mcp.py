from mcp_server import MCPToolset

from tasks.models import Task
from tasks.serializers import ParentTaskSerializer


class UserTasksToolset(MCPToolset):
    def get_user_unarchived_tasks(self):
        """Tool that lists all unarchived user tasks"""
        parent_tasks = (
            Task.objects.filter_unarchived()
            .filter(user=self.request.user, parent__isnull=True)
            .prefetch_related('subtasks')
        )
        serializer = ParentTaskSerializer(parent_tasks, many=True)
        return serializer.data

    def get_user_archived_tasks(self):
        """Tool that lists all archived user tasks"""
        parent_tasks = (
            Task.objects.filter_archived()
            .filter(user=self.request.user, parent__isnull=True)
            .prefetch_related('subtasks')
        )
        serializer = ParentTaskSerializer(parent_tasks, many=True)
        return serializer.data
