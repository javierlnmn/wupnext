from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        autodiscover_modules('notifications')
