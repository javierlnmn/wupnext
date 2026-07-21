from django.urls import path

from . import views

app_name = "pomodoro"

urlpatterns = [
    path("state/", views.PomodoroStateView.as_view(), name="state"),
]
