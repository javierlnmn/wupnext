from .notifications.due_reminders import DueReminderNotification


def send_due_reminders():
    DueReminderNotification().send()
