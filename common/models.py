from django.db import models


class AbstractSingleton(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]


class SiteSettings(AbstractSingleton):
    # Notification channels
    notification_channels_email_enabled = models.BooleanField(default=True)

    # Task notifications
    tasks_notification_due_reminders_enabled = models.BooleanField(default=True)
