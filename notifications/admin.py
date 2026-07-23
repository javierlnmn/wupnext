from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "channel", "dedup_key", "created_at")
    list_filter = ("event", "channel")
    search_fields = ("user__username", "dedup_key")
    readonly_fields = ("user", "event", "channel", "dedup_key", "created_at")
