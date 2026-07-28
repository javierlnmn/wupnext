from django.utils.module_loading import import_string

from ..exceptions import MissingPreview
from ..models import NotificationEvent
from .base import PREVIEW_EMAIL, PREVIEW_USERNAME, BaseEmailPreview

PREVIEWS = {
    NotificationEvent.TASK_DUE_REMINDER.value: (
        "notifications.email_previews.task_due_reminder_preview.TaskDueReminderPreview"
    ),
}

__all__ = [
    "PREVIEWS",
    "PREVIEW_EMAIL",
    "PREVIEW_USERNAME",
    "BaseEmailPreview",
    "get_preview",
]


def get_preview(event):
    path = PREVIEWS.get(event)
    if path is None:
        raise MissingPreview(
            f"No preview registered for '{event}'. "
            f"Available: {', '.join(sorted(PREVIEWS)) or 'none'}."
        )
    return import_string(path)()
