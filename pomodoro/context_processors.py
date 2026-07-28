from accounts.models import UserPreferences

from .models import PomodoroState


def pomodoro(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'pomodoro_settings': UserPreferences.for_user(request.user).pomodoro_dict(),
        'pomodoro_state': PomodoroState.for_user(request.user).state_dict(),
    }
