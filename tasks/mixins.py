from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from .models import MAX_TASK_WEIGHT, Group, Task


class BoardMixin(LoginRequiredMixin):
    def active_group(self):
        group_id = self.request.session.get("active_group")
        if not group_id:
            return None
        return Group.objects.filter(id=group_id, user=self.request.user).first()

    def board_context(self):
        active_group = self.active_group()
        top_level = (
            Task.objects.filter_unarchived()
            .filter(user=self.request.user, parent__isnull=True)
            .select_related("group")
            .prefetch_related("subtasks")
        )
        if active_group:
            top_level = top_level.filter(group=active_group)
        return {
            "pending_tasks": top_level.filter(completed_at__isnull=True),
            "completed_tasks": top_level.filter(completed_at__isnull=False),
            "max_task_weight": MAX_TASK_WEIGHT,
        }

    def board_response(self):
        return render(
            self.request, "tasks/partials/response.html", self.board_context()
        )


class ArchiveMixin(LoginRequiredMixin):
    def archive_context(self):
        return {
            "archived_tasks": (
                Task.objects.filter_archived()
                .filter(user=self.request.user, parent__isnull=True)
                .select_related("group")
                .prefetch_related("subtasks")
                .order_by("-archived_at")
            )
        }

    def archive_response(self):
        return render(
            self.request, "tasks/partials/archive/list.html", self.archive_context()
        )
