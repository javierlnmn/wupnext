from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import GroupForm, TaskForm
from .mixins import ArchiveMixin, BoardMixin
from .models import Group, Task


class BoardView(BoardMixin, TemplateView):
    template_name = "tasks/board.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.board_context())
        return context


class TaskView(BoardMixin, View):
    def post(self, request):
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            if data["task_id"]:
                Task.objects.filter(id=data["task_id"], user=request.user).update(
                    name=data["name"],
                    weight=data["weight"],
                    group=data["group"],
                    due_date=data["due_date"],
                )
            else:
                Task.objects.create(
                    user=request.user,
                    name=data["name"],
                    weight=data["weight"],
                    group=data["group"],
                    parent=data["parent"],
                    due_date=data["due_date"],
                )
        return self.board_response()

    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()
        return self.board_response()


class ToggleCompleteTaskView(BoardMixin, View):
    def post(self, request, task_id):
        task = Task.objects.filter(id=task_id, user=request.user).first()
        if not task:
            return HttpResponse(status=404)

        now = None if task.completed_at else timezone.now()
        task.completed_at = now
        task.save(update_fields=["completed_at"])
        task.subtasks.update(completed_at=now)

        return self.board_response()


class GroupView(BoardMixin, View):
    def post(self, request):
        form = GroupForm(request.POST)
        if not form.is_valid():
            return self.board_response()
        group = Group.objects.create(
            user=request.user,
            name=form.cleaned_data["name"],
            color=form.cleaned_data["color"],
            position=Group.objects.filter(user=request.user).count(),
        )
        response = HttpResponse(status=204)
        response["HX-Location"] = f"{reverse('tasks:board')}?group={group.id}"
        return response

    def delete(self, request, group_id):
        was_active = request.GET.get("group") == str(group_id)
        Group.objects.filter(id=group_id, user=request.user).delete()
        response = self.board_response()
        if was_active:
            response["HX-Push-Url"] = reverse("tasks:board")
        return response


class ArchiveView(BoardMixin, ArchiveMixin, View):
    def get(self, request):
        return self.archive_response()

    def post(self, request, task_id):
        Task.objects.filter(
            id=task_id, user=request.user, completed_at__isnull=False
        ).update(archived_at=timezone.now())
        return self.board_response()

    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()
        return self.archive_response()


class UnarchiveTaskView(BoardMixin, ArchiveMixin, View):
    def post(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).update(archived_at=None)
        return render(
            request,
            "tasks/partials/archive/unarchive_response.html",
            {**self.archive_context(), **self.board_context()},
        )
