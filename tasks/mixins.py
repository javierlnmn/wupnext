from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from .models import MAX_TASK_WEIGHT, DueFilter, Group, Task


class BoardMixin(LoginRequiredMixin):
    def active_group(self):
        group_id = self.request.GET.get("group")
        if not group_id or not group_id.isdigit():
            return None
        return Group.objects.filter(id=int(group_id), user=self.request.user).first()

    def board_context(self):
        active_group = self.active_group()
        due = self.request.GET.get("due")
        active_due = due if due in DueFilter.values else None
        today = timezone.localdate()

        order_field = "group_position" if active_group else "position"
        top_level = (
            Task.objects.filter_unarchived()
            .filter(user=self.request.user, parent__isnull=True)
            .select_related("group")
            .prefetch_related("subtasks")
            .order_by(order_field, "created_at")
        )
        if active_group:
            top_level = top_level.filter(group=active_group)
        if active_due == DueFilter.TODAY:
            top_level = top_level.filter(due_date=today)
        elif active_due == DueFilter.OVERDUE:
            top_level = top_level.filter(due_date__lt=today, completed_at__isnull=True)

        params = {}
        if active_group:
            params["group"] = active_group.id
        if active_due:
            params["due"] = active_due

        return {
            "pending_tasks": top_level.filter(completed_at__isnull=True),
            "completed_tasks": top_level.filter(completed_at__isnull=False),
            "max_task_weight": MAX_TASK_WEIGHT,
            "active_task_group": active_group,
            "active_due": active_due,
            "today": today,
            "board_query": f"?{urlencode(params)}" if params else "",
            "reorderable": active_due is None,
        }

    def board_response(self):
        return render(
            self.request,
            "tasks/partials/shared/board_response.html",
            self.board_context(),
        )


class ReorderMixin(LoginRequiredMixin):
    def ordered_ids(self):
        raw = self.request.POST.get("order", "")
        return [int(part) for part in raw.split(",") if part.isdigit()]

    def is_full_scope(self, ids, objects):
        expected = {obj.id for obj in objects}
        return len(ids) == len(expected) and set(ids) == expected

    def assign_positions(self, objects, ids, field="position"):
        by_id = {obj.id: obj for obj in objects}
        updated = []
        for position, obj_id in enumerate(ids):
            obj = by_id.get(obj_id)
            if obj and getattr(obj, field) != position:
                setattr(obj, field, position)
                updated.append(obj)
        return updated


class ArchiveMixin(LoginRequiredMixin):
    def archive_context(self):
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
        }

    def archive_response(self):
        return render(
            self.request, "tasks/partials/archive/list.html", self.archive_context()
        )
