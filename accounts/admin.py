from django.contrib import admin

from .models import CustomUser, UserPreferences


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
    )
    search_fields = ('username', 'email')


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'pomodoro_focus',
        'pomodoro_short_break',
        'pomodoro_long_break',
        'pomodoro_long_every',
    )
    search_fields = ('user__username',)
