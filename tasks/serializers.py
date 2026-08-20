from rest_framework import serializers

from tasks.models import Group, Task


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('name', 'color', 'position', 'created_at')


class TaskSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(
        source='group.name', default=None, read_only=True
    )

    class Meta:
        model = Task
        fields = (
            'name',
            'weight',
            'group',
            'group_name',
            'parent',
            'due_date',
            'position',
            'group_position',
            'completed_at',
            'archived_at',
            'created_at',
        )


class ParentTaskSerializer(serializers.ModelSerializer):
    subtasks = TaskSerializer(many=True, read_only=True)
    group_name = serializers.CharField(
        source='group.name', default=None, read_only=True
    )

    class Meta:
        model = Task
        fields = (
            'name',
            'weight',
            'group',
            'group_name',
            'subtasks',
            'due_date',
            'position',
            'group_position',
            'completed_at',
            'archived_at',
            'created_at',
        )
