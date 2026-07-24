from collections import defaultdict

from django.db import migrations


def backfill_positions(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")

    position_counters = defaultdict(int)
    group_counters = defaultdict(int)
    tasks = list(Task.objects.order_by("user_id", "parent_id", "created_at"))

    for task in tasks:
        key = (task.user_id, task.parent_id)
        task.position = position_counters[key]
        position_counters[key] += 1

        if task.parent_id is None and task.group_id is not None:
            group_key = (task.user_id, task.group_id)
            task.group_position = group_counters[group_key]
            group_counters[group_key] += 1

    if tasks:
        Task.objects.bulk_update(tasks, ["position", "group_position"])


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0010_task_group_position"),
    ]

    operations = [
        migrations.RunPython(backfill_positions, migrations.RunPython.noop),
    ]
