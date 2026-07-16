from accounts.models import UserPreferences


def pomodoro(request):
    if not request.user.is_authenticated:
        return {}
    return {"pomodoro_settings": UserPreferences.for_user(request.user).pomodoro_dict()}
