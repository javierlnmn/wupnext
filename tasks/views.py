from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .models import DEFAULT_GROUP_COLOR, GROUP_COLOR_VALUES, GROUP_COLORS, Group, Task


def _parse_weight(value):
    try:
        weight = int(value)
    except (TypeError, ValueError):
        return 0
    return min(max(weight, 0), 5)


def _active_group(request):
    group_id = request.session.get("active_group")
    if not group_id:
        return None
    return Group.objects.filter(id=group_id, user=request.user).first()


def _tasks_context(user, active_group):
    tasks = Task.objects.filter(user=user)
    top_level = (
        tasks.filter(parent__isnull=True)
        .select_related("group")
        .prefetch_related("subtasks")
    )
    if active_group:
        top_level = top_level.filter(group=active_group)
    return {
        "pending_tasks": top_level.filter(completed_at__isnull=True),
        "completed_tasks": top_level.filter(completed_at__isnull=False),
    }


def _groups_context(user, active_group):
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


def _queue_context(request):
    active_group = _active_group(request)
    context = _tasks_context(request.user, active_group)
    context.update(_groups_context(request.user, active_group))
    return context


def _queue_response(request):
    return render(
        request, "tasks/partials/queue_response.html", _queue_context(request)
    )


class QueueView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_queue_context(self.request))
        return context


class TaskView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        task_id = request.POST.get("task_id")

        if name:
            weight = _parse_weight(request.POST.get("weight"))
            group = None
            group_id = request.POST.get("group_id")
            if group_id:
                group = Group.objects.filter(id=group_id, user=request.user).first()

            if task_id:
                Task.objects.filter(id=task_id, user=request.user).update(
                    name=name, weight=weight, group=group
                )
            else:
                parent = None
                parent_id = request.POST.get("parent_id")
                if parent_id:
                    parent = Task.objects.filter(
                        id=parent_id, user=request.user, parent__isnull=True
                    ).first()
                if parent:
                    group = None
                Task.objects.create(
                    user=request.user,
                    name=name,
                    weight=weight,
                    group=group,
                    parent=parent,
                )

        return _queue_response(request)

    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()
        return _queue_response(request)


class TaskCompleteView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = Task.objects.filter(id=task_id, user=request.user).first()
        if not task:
            return HttpResponse(status=404)

        task.completed_at = timezone.now()
        task.save(update_fields=["completed_at"])

        return _queue_response(request)


class GroupFilterView(LoginRequiredMixin, View):
    def post(self, request):
        value = request.POST.get("group")
        if value and value != "all":
            group = Group.objects.filter(id=value, user=request.user).first()
            request.session["active_group"] = group.id if group else None
        else:
            request.session["active_group"] = None
        return _queue_response(request)


class GroupCreateView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        if name:
            color = request.POST.get("color", "")
            if color not in GROUP_COLOR_VALUES:
                color = DEFAULT_GROUP_COLOR
            position = Group.objects.filter(user=request.user).count()
            Group.objects.create(
                user=request.user, name=name, color=color, position=position
            )
        return _queue_response(request)


class GroupDeleteView(LoginRequiredMixin, View):
    def delete(self, request, group_id):
        Group.objects.filter(id=group_id, user=request.user).delete()
        if request.session.get("active_group") == group_id:
            request.session["active_group"] = None
        return _queue_response(request)
