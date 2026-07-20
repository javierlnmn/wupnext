from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import GroupForm, TaskForm
from .mixins import ArchiveMixin, BoardMixin
from .models import Group, Task


class BoardView(BoardMixin, TemplateView):
    template_name = "tasks/board.html"

    def get(self, request, *args, **kwargs):
        group = request.GET.get("group")
        if group is not None:
            if group.isdigit() and Group.objects.filter(
                id=group, user=request.user
            ).exists():
                request.session["active_group"] = int(group)
            else:
                request.session["active_group"] = None
        return super().get(request, *args, **kwargs)

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
                    name=data["name"], weight=data["weight"], group=data["group"]
                )
            else:
                Task.objects.create(
                    user=request.user,
                    name=data["name"],
                    weight=data["weight"],
                    group=data["group"],
                    parent=data["parent"],
                )
        return self.board_response()

    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()
        return self.board_response()


class TaskCompleteView(BoardMixin, View):
    def post(self, request, task_id):
        task = Task.objects.filter(id=task_id, user=request.user).first()
        if not task:
            return HttpResponse(status=404)

        now = timezone.now()

        task.completed_at = now
        task.save(update_fields=["completed_at"])

        task.subtasks.update(completed_at=now)

        return self.board_response()


class TaskArchiveView(BoardMixin, View):
    def post(self, request, task_id):
        Task.objects.filter(
            id=task_id, user=request.user, completed_at__isnull=False
        ).update(archived_at=timezone.now())
        return self.board_response()


class GroupCreateView(BoardMixin, View):
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
        request.session["active_group"] = group.id
        return self.board_response()


class GroupDeleteView(BoardMixin, View):
    def delete(self, request, group_id):
        Group.objects.filter(id=group_id, user=request.user).delete()
        if request.session.get("active_group") == group_id:
            request.session["active_group"] = None
        return self.board_response()


class ArchiveView(ArchiveMixin, View):
    def get(self, request):
        return self.archive_response()


class TaskUnarchiveView(BoardMixin, ArchiveMixin, View):
    def post(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).update(archived_at=None)
        return render(
            request,
            "tasks/partials/archive/unarchive_response.html",
            {**self.board_context(), **self.archive_context()},
        )


class ArchiveTaskDeleteView(ArchiveMixin, View):
    def delete(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).delete()
        return self.archive_response()
