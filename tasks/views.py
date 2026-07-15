from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .models import Task


def _parse_weight(value):
    try:
        weight = int(value)
    except (TypeError, ValueError):
        return 0
    return min(max(weight, 0), 5)


def _tasks_context(user):
    tasks = Task.objects.filter(user=user)
    top_level = tasks.filter(parent__isnull=True).prefetch_related("subtasks")
    return {
        "pending_tasks": top_level.filter(completed_at__isnull=True),
        "completed_tasks": top_level.filter(completed_at__isnull=False),
        "total_tasks": tasks.count(),
    }


class QueueView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_tasks_context(self.request.user))
        return context


class TaskView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        task_id = request.POST.get("task_id")

        if name:
            weight = _parse_weight(request.POST.get("weight"))
            if task_id:
                Task.objects.filter(id=task_id, user=request.user).update(
                    name=name, weight=weight
                )
            else:
                parent = None
                parent_id = request.POST.get("parent_id")
                if parent_id:
                    parent = Task.objects.filter(
                        id=parent_id, user=request.user, parent__isnull=True
                    ).first()
                Task.objects.create(
                    user=request.user, name=name, weight=weight, parent=parent
                )

        context = _tasks_context(request.user)
        return render(request, "tasks/partials/queue_response.html", context)

    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()

        context = _tasks_context(request.user)
        return render(request, "tasks/partials/queue_response.html", context)


class TaskCompleteView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = Task.objects.filter(id=task_id, user=request.user).first()
        if not task:
            return HttpResponse(status=404)

        task.completed_at = timezone.now()
        task.save(update_fields=["completed_at"])

        context = _tasks_context(request.user)
        return render(request, "tasks/partials/queue_response.html", context)
