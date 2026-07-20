from django.contrib import admin

from .models import Group, Task


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "color", "position"]
    search_fields = ["name"]
    ordering = ["position", "created_at"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "group",
        "parent",
        "completed_at",
        "archived_at",
        "created_at",
    ]
    list_filter = ["completed_at", "archived_at", "group"]
    search_fields = ["name"]
    ordering = ["created_at"]
    raw_id_fields = ["parent"]
