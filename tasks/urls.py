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
    path("group/filter/", views.GroupFilterView.as_view(), name="group-filter"),
    path("group/", views.GroupCreateView.as_view(), name="group-create"),
    path("group/<int:group_id>/", views.GroupDeleteView.as_view(), name="group-detail"),
]
