from django.db.models import Count
from django.utils import timezone

from .models import DEFAULT_GROUP_COLOR, GROUP_COLORS, DueLens, Group, Task


def sidebar(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    pending = Task.objects.filter_unarchived().filter(
        user=user, parent__isnull=True, completed_at__isnull=True
    )
    groups = list(Group.objects.filter(user=user))
    counts = {
        row["group"]: row["c"]
        for row in pending.values("group").annotate(c=Count("id"))
    }
    for group in groups:
        group.pending_count = counts.get(group.id, 0)

    today = timezone.localdate()

    return {
        "task_groups": groups,
        "all_tasks_count": sum(counts.values()),
        "today_count": pending.filter(due_date=today).count(),
        "overdue_count": pending.filter(due_date__lt=today).count(),
        "task_group_palette": GROUP_COLORS,
        "default_task_group_color": DEFAULT_GROUP_COLOR,
        "DueLens": DueLens,
    }
