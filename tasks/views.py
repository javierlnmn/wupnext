from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import GroupForm, TaskForm
from .mixins import ArchiveMixin, BoardMixin, ReorderMixin
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
            group = data["group"]
            if data["task_id"]:
                task = Task.objects.filter(
                    id=data["task_id"], user=request.user
                ).first()
                if task:
                    fields = ["name", "weight", "group", "due_date"]
                    if task.group_id != (group.id if group else None):
                        task.group_position = (
                            Task.next_group_position(request.user, group)
                            if group
                            else 0
                        )
                        fields.append("group_position")
                    task.name = data["name"]
                    task.weight = data["weight"]
                    task.group = group
                    task.due_date = data["due_date"]
                    task.save(update_fields=fields)
            else:
                Task.objects.create(
                    user=request.user,
                    name=data["name"],
                    weight=data["weight"],
                    group=group,
                    parent=data["parent"],
                    due_date=data["due_date"],
                    position=Task.next_position(request.user, data["parent"]),
                    group_position=(
                        Task.next_group_position(request.user, group) if group else 0
                    ),
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

        if form.cleaned_data["group_id"]:
            Group.objects.filter(
                id=form.cleaned_data["group_id"], user=request.user
            ).update(
                name=form.cleaned_data["name"],
                color=form.cleaned_data["color"],
            )
            return self.board_response()

        group = Group.objects.create(
            user=request.user,
            name=form.cleaned_data["name"],
            color=form.cleaned_data["color"],
            position=Group.next_position(request.user),
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


class TaskReorderView(BoardMixin, ReorderMixin, View):
    def post(self, request):
        group = self.active_group()
        field = "group_position" if group else "position"
        scope = Task.objects.filter_unarchived().filter(
            user=request.user, parent__isnull=True, completed_at__isnull=True
        )
        if group:
            scope = scope.filter(group=group)

        objects = list(scope)
        ids = self.ordered_ids()
        if not self.is_full_scope(ids, objects):
            return HttpResponse(status=400)

        updated = self.assign_positions(objects, ids, field)
        Task.objects.bulk_update(updated, [field])
        return self.board_response()


class GroupReorderView(BoardMixin, ReorderMixin, View):
    def post(self, request):
        objects = list(Group.objects.filter(user=request.user))
        ids = self.ordered_ids()
        if not self.is_full_scope(ids, objects):
            return HttpResponse(status=400)

        updated = self.assign_positions(objects, ids)
        Group.objects.bulk_update(updated, ["position"])
        return self.board_response()


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


class ArchivePeriodView(ArchiveMixin, View):
    def delete(self, request, period):
        try:
            year, month = (int(part) for part in period.split("-"))
        except ValueError:
            return HttpResponse(status=400)
        Task.objects.filter_archived().filter(
            user=request.user,
            parent__isnull=True,
            archived_at__year=year,
            archived_at__month=month,
        ).delete()
        return self.archive_response()


class UnarchiveTaskView(BoardMixin, ArchiveMixin, View):
    def post(self, request, task_id):
        Task.objects.filter(id=task_id, user=request.user).update(archived_at=None)
        return render(
            request,
            "tasks/partials/archive/unarchive_response.html",
            {**self.archive_context(), **self.board_context()},
        )
