from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path(
        'preferences/', views.NotificationPreferencesView.as_view(), name='preferences'
    ),
]
