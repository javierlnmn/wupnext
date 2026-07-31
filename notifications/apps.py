from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # Everything an app contributes lives under <app>/notifications/, so
        # importing that package is what fills the notification and preview
        # registries. An app that puts them elsewhere registers nothing.
        autodiscover_modules('notifications')
