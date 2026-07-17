from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import render

from .models import DEFAULT_GROUP_COLOR, GROUP_COLORS, MAX_TASK_WEIGHT, Group, Task


class BoardMixin(LoginRequiredMixin):
    def active_group(self):
        group_id = self.request.session.get("active_group")
        if not group_id:
            return None
        return Group.objects.filter(id=group_id, user=self.request.user).first()

    def _task_context(self, active_group):
        top_level = (
            Task.objects.filter(user=self.request.user, parent__isnull=True)
            .select_related("group")
            .prefetch_related("subtasks")
        )
        if active_group:
            top_level = top_level.filter(group=active_group)
        return {
            "pending_tasks": top_level.filter(completed_at__isnull=True),
            "completed_tasks": top_level.filter(completed_at__isnull=False),
        }

    def _group_context(self, active_group):
        user = self.request.user
        groups = list(Group.objects.filter(user=user))
        counts = {
            row["group"]: row["c"]
            for row in Task.objects.filter(
                user=user, parent__isnull=True, completed_at__isnull=True
            )
            .values("group")
            .annotate(c=Count("id"))
        }
        for group in groups:
            group.pending_count = counts.get(group.id, 0)
        return {
            "groups": groups,
            "active_group": active_group,
            "group_all_count": sum(counts.values()),
            "group_palette": GROUP_COLORS,
            "default_group_color": DEFAULT_GROUP_COLOR,
        }

    def board_context(self):
        active_group = self.active_group()
        return {
            **self._task_context(active_group),
            **self._group_context(active_group),
            "max_task_weight": MAX_TASK_WEIGHT,
        }

    def board_response(self):
        return render(
            self.request, "tasks/partials/response.html", self.board_context()
        )
