from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.QueueView.as_view(), name="queue"),
    path("task/", views.TaskView.as_view(), name="task"),
    path("task/<int:task_id>/", views.TaskView.as_view(), name="task-detail"),
    path(
        "task/<int:task_id>/complete/",
        views.TaskCompleteView.as_view(),
        name="task-complete",
    ),
]
