from notifications.service import NotificationService

from .notifications.due_reminders import DueReminderNotification


def send_due_reminders():
    NotificationService(DueReminderNotification()).enqueue()
