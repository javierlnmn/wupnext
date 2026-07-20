from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.BoardView.as_view(), name="board"),
    path("task/", views.TaskView.as_view(), name="task"),
    path("task/<int:task_id>/", views.TaskView.as_view(), name="task-detail"),
    path(
        "task/<int:task_id>/complete/",
        views.TaskCompleteView.as_view(),
        name="task-complete",
    ),
    path(
        "task/<int:task_id>/archive/",
        views.TaskArchiveView.as_view(),
        name="task-archive",
    ),
    path(
        "task/<int:task_id>/unarchive/",
        views.TaskUnarchiveView.as_view(),
        name="task-unarchive",
    ),
    path("archive/", views.ArchiveView.as_view(), name="archive"),
    path(
        "archive/task/<int:task_id>/",
        views.ArchiveTaskDeleteView.as_view(),
        name="archive-task-detail",
    ),
    path("group/", views.GroupCreateView.as_view(), name="group-create"),
    path("group/<int:group_id>/", views.GroupDeleteView.as_view(), name="group-detail"),
]
