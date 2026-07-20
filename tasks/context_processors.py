from django.db.models import Count

from .models import DEFAULT_GROUP_COLOR, GROUP_COLORS, Group, Task


def sidebar(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    groups = list(Group.objects.filter(user=user))
    counts = {
        row["group"]: row["c"]
        for row in Task.objects.filter_unarchived()
        .filter(user=user, parent__isnull=True, completed_at__isnull=True)
        .values("group")
        .annotate(c=Count("id"))
    }
    for group in groups:
        group.pending_count = counts.get(group.id, 0)

    active_group = None
    group_id = request.session.get("active_group")
    if group_id:
        active_group = next((g for g in groups if g.id == group_id), None)

    match = request.resolver_match
    nav_active = "archive" if match and match.url_name == "archive" else "board"

    return {
        "task_groups": groups,
        "active_task_group": active_group,
        "all_tasks_count": sum(counts.values()),
        "task_group_palette": GROUP_COLORS,
        "default_task_group_color": DEFAULT_GROUP_COLOR,
        "nav_active": nav_active,
    }
