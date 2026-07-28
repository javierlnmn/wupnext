from ..exceptions import MissingPreview
from .task_due_reminder_preview import TaskDueReminderPreview

PREVIEWS = {
    TaskDueReminderPreview.event: TaskDueReminderPreview,
}


def get_preview(event):
    preview_class = PREVIEWS.get(event)
    if preview_class is None:
        raise MissingPreview(
            f"No preview registered for '{event}'. "
            f'Available: {", ".join(sorted(PREVIEWS)) or "none"}.'
        )
    return preview_class()
