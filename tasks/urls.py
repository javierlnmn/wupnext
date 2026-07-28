from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.BoardView.as_view(), name='board'),
    path('task/', views.TaskView.as_view(), name='task'),
    path('task/reorder/', views.TaskReorderView.as_view(), name='task-reorder'),
    path('task/<int:task_id>/', views.TaskView.as_view(), name='task-detail'),
    path(
        'task/<int:task_id>/toggle-complete/',
        views.ToggleCompleteTaskView.as_view(),
        name='task-toggle-complete',
    ),
    path(
        'task/<int:task_id>/archive/',
        views.ArchiveView.as_view(),
        name='task-archive',
    ),
    path(
        'task/<int:task_id>/unarchive/',
        views.UnarchiveTaskView.as_view(),
        name='task-unarchive',
    ),
    path('archive/', views.ArchiveView.as_view(), name='archive'),
    path(
        'archive/task/<int:task_id>/',
        views.ArchiveView.as_view(),
        name='archive-task-detail',
    ),
    path(
        'archive/period/<str:period>/',
        views.ArchivePeriodView.as_view(),
        name='archive-period-delete',
    ),
    path('group/', views.GroupView.as_view(), name='group-create'),
    path('group/reorder/', views.GroupReorderView.as_view(), name='group-reorder'),
    path('group/<int:group_id>/', views.GroupView.as_view(), name='group-detail'),
]
