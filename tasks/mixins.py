from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render

from .models import MAX_TASK_WEIGHT, Group, Task


class BoardMixin(LoginRequiredMixin):
    def active_group(self):
        group_id = self.request.GET.get("group")
        if not group_id or not group_id.isdigit():
            return None
        return Group.objects.filter(id=int(group_id), user=self.request.user).first()

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
            "active_task_group": active_group,
            "group_query": f"?group={active_group.id}" if active_group else "",
        }

    def board_response(self):
        return render(
            self.request,
            "tasks/partials/shared/board_response.html",
            self.board_context(),
        )


class ArchiveMixin(LoginRequiredMixin):
    def archive_context(self):
        group_id = self.request.GET.get("group")
        group_query = f"?group={group_id}" if group_id and group_id.isdigit() else ""

        base = Task.objects.filter_archived().filter(
            user=self.request.user, parent__isnull=True
        )
        periods = [
            {
                "value": row["month"].strftime("%Y-%m"),
                "year": row["month"].year,
                "label": row["month"].strftime("%B"),
                "short": row["month"].strftime("%b %y"),
                "count": row["count"],
            }
            for row in base.annotate(month=TruncMonth("archived_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("-month")
        ]

        requested = self.request.GET.get("period")
        values = {p["value"] for p in periods}
        active_period = requested if requested in values else (
            periods[0]["value"] if periods else None
        )

        tasks = (
            base.select_related("group")
            .prefetch_related("subtasks")
            .annotate(day=TruncDate("archived_at"))
            .order_by("-archived_at")
        )
        if active_period:
            year, month = active_period.split("-")
            tasks = tasks.filter(
                archived_at__year=int(year), archived_at__month=int(month)
            )

        return {
            "archived_tasks": tasks,
            "archive_periods": periods,
            "active_period": active_period,
            "group_query": group_query,
        }

    def archive_response(self):
        return render(
            self.request, "tasks/partials/archive/list.html", self.archive_context()
        )
