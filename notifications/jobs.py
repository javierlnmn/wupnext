from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string

from .service import NotificationService


def send_notification_to_user(notification_class_path, user_id):
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return

    NotificationService(import_string(notification_class_path)()).send(user)


def enqueue_bulk_notification(notification_class_path):
    NotificationService(import_string(notification_class_path)()).enqueue_bulk()
