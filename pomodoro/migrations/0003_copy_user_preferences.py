from django.db import migrations


def copy_from_accounts(apps, schema_editor):
    UserPreferences = apps.get_model('accounts', 'UserPreferences')
    PomodoroUserPreference = apps.get_model('pomodoro', 'PomodoroUserPreference')

    PomodoroUserPreference.objects.bulk_create(
        PomodoroUserPreference(
            user_id=user_id,
            focus=focus,
            short_break=short_break,
            long_break=long_break,
            long_every=long_every,
        )
        for user_id, focus, short_break, long_break, long_every in (
            UserPreferences.objects.values_list(
                'user_id',
                'pomodoro_focus',
                'pomodoro_short_break',
                'pomodoro_long_break',
                'pomodoro_long_every',
            )
        )
    )


def copy_back_to_accounts(apps, schema_editor):
    UserPreferences = apps.get_model('accounts', 'UserPreferences')
    PomodoroUserPreference = apps.get_model('pomodoro', 'PomodoroUserPreference')

    for preference in PomodoroUserPreference.objects.all():
        UserPreferences.objects.update_or_create(
            user_id=preference.user_id,
            defaults={
                'pomodoro_focus': preference.focus,
                'pomodoro_short_break': preference.short_break,
                'pomodoro_long_break': preference.long_break,
                'pomodoro_long_every': preference.long_every,
            },
        )

    PomodoroUserPreference.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('pomodoro', '0002_pomodoro_user_preference'),
        ('accounts', '0007_remove_userpreferences_notification_channels_email_enabled'),
    ]

    operations = [migrations.RunPython(copy_from_accounts, copy_back_to_accounts)]
