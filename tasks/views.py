from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from common.utils import parse_date

from .models import Task


def _tasks_queue_context(user, view_date):
    tasks = Task.get_user_tasks_for_date(user, view_date)
    pending = tasks.filter(completed=False)
    completed = tasks.filter(completed=True)
    return {
        "pending_tasks": pending,
        "completed_tasks": completed,
        "total_tasks": tasks.count(),
        "current_task": pending.first(),
        "view_date": view_date,
        "today": timezone.localdate(),
    }


class QueueView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view_date = parse_date(self.request.GET.get("date"))
        context.update(_tasks_queue_context(self.request.user, view_date))
        context["prev_date"] = view_date - timedelta(days=1)
        context["next_date"] = view_date + timedelta(days=1)
        return context


class TaskView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        view_date = parse_date(request.POST.get("date"))

        if name:
            Task.objects.create(
                user=request.user,
                name=name,
                date=view_date,
            )

        context = _tasks_queue_context(request.user, view_date)
        return render(request, "tasks/partials/queue_response.html", context)

    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()

        view_date = parse_date(request.GET.get("date"))
        context = _tasks_queue_context(request.user, view_date)
        return render(request, "tasks/partials/queue_response.html", context)


@login_required
def toggle_task_timer(request, task_id):
    task = Task.objects.filter(id=task_id, user=request.user).first()
    if not task:
        return HttpResponse(status=404)

    if task.is_running:
        delta = int((timezone.now() - task.last_started).total_seconds())
        task.elapsed_seconds += delta
        task.last_started = None
    else:
        task.last_started = timezone.now()

    task.save(update_fields=["last_started", "elapsed_seconds"])
    return HttpResponse(status=204)


@login_required
def complete_task(request, task_id):
    task = Task.objects.filter(id=task_id, user=request.user).first()
    if not task:
        return HttpResponse(status=404)

    task.completed = True
    if task.is_running:
        delta = int((timezone.now() - task.last_started).total_seconds())
        task.elapsed_seconds += delta
        task.last_started = None
        task.save(update_fields=["completed", "last_started", "elapsed_seconds"])
    else:
        task.save(update_fields=["completed"])

    view_date = parse_date(request.POST.get("date") or request.GET.get("date"))
    context = _tasks_queue_context(request.user, view_date)
    return render(request, "tasks/partials/queue_response.html", context)
