from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path(
        'preferences/', views.NotificationPreferencesView.as_view(), name='preferences'
    ),
    path(
        'unsubscribe/<str:token>/',
        views.UnsubscribeView.as_view(),
        name='unsubscribe',
    ),
]
