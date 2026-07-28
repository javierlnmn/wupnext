from django.conf import settings
from django.db import models


class Channel(models.TextChoices):
    EMAIL = "email", "Email"


class NotificationLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    event = models.CharField(max_length=64)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    dedup_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event", "channel", "dedup_key"],
                name="unique_notification_dispatch",
            )
        ]

    def __str__(self):
        return f"{self.event} → {self.channel} ({self.dedup_key})"
