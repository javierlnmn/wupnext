from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string


def send_notification_to_user(notification_path, user_id):
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return

    import_string(notification_path)().send_to(user)
