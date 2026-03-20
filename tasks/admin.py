from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "date",
        "completed",
        "position",
        "last_started",
        "elapsed_seconds",
        "created_at",
    ]
    list_filter = ["date", "completed"]
    search_fields = ["name"]
    ordering = ["position", "created_at"]
