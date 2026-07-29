from django.contrib import admin

from .models import (
    NotificationChannelSwitch,
    NotificationEventSwitch,
    NotificationLog,
    NotificationUserPreference,
)


class SwitchAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationChannelSwitch)
class NotificationChannelSwitchAdmin(SwitchAdmin):
    list_display = ('channel', 'enabled')
    list_editable = ('enabled',)


@admin.register(NotificationEventSwitch)
class NotificationEventSwitchAdmin(SwitchAdmin):
    list_display = ('event', 'channel', 'enabled', 'on_by_default')
    list_editable = ('enabled', 'on_by_default')
    list_filter = ('channel', 'enabled')


@admin.register(NotificationUserPreference)
class NotificationUserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'channel', 'enabled', 'updated_at')
    list_filter = ('event', 'channel', 'enabled')
    search_fields = ('user__username', 'user__email')
    list_select_related = ('user',)
    readonly_fields = ('updated_at',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'channel', 'dedup_key', 'created_at')
    list_filter = ('event', 'channel')
    search_fields = ('user__username', 'dedup_key')
    readonly_fields = ('user', 'event', 'channel', 'dedup_key', 'created_at')
