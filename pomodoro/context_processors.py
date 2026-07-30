from .models import PomodoroState, PomodoroUserPreference


def pomodoro(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'pomodoro_settings': PomodoroUserPreference.for_user(
            request.user
        ).settings_dict(),
        'pomodoro_state': PomodoroState.for_user(request.user).state_dict(),
    }
