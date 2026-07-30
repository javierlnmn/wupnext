from django.urls import path

from . import views

app_name = 'pomodoro'

urlpatterns = [
    path('state/', views.PomodoroStateView.as_view(), name='state'),
    path('preferences/', views.PomodoroPreferencesView.as_view(), name='preferences'),
]
