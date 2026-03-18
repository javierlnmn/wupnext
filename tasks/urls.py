from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.QueueView.as_view(), name="queue"),
    path("task/", views.TaskView.as_view(), name="task"),
    path("task/<int:task_id>/", views.TaskView.as_view(), name="task-detail"),
    path("task/<int:task_id>/toggle/", views.toggle_task, name="task-toggle"),
    path("task/<int:task_id>/complete/", views.complete_task, name="task-complete"),
]
