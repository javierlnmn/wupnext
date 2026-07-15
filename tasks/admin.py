from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["name", "completed_at", "created_at"]
    list_filter = ["completed_at"]
    search_fields = ["name"]
    ordering = ["created_at"]
