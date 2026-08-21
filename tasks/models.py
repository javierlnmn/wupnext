from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

GROUP_COLORS = [
    {'name': 'Clay', 'hex': '#d1793f'},
    {'name': 'Amber', 'hex': '#f59e0b'},
    {'name': 'Olive', 'hex': '#8a9b6e'},
    {'name': 'Emerald', 'hex': '#10b981'},
    {'name': 'Sky', 'hex': '#38bdf8'},
    {'name': 'Violet', 'hex': '#8b5cf6'},
    {'name': 'Rose', 'hex': '#f43f5e'},
    {'name': 'Slate', 'hex': '#64748b'},
]
DEFAULT_GROUP_COLOR = GROUP_COLORS[0]['hex']
GROUP_COLOR_VALUES = {color['hex'] for color in GROUP_COLORS}

MAX_TASK_WEIGHT = 5


class DueFilter(models.TextChoices):
    TODAY = 'today', 'Today'
    OVERDUE = 'overdue', 'Overdue'


class Group(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_groups',
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=9, default=DEFAULT_GROUP_COLOR)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'created_at']

    def __str__(self):
        return self.name

    @classmethod
    def next_position(cls, user):
        last = cls.objects.filter(user=user).aggregate(
            max_position=models.Max('position')
        )['max_position']
        return last + 1 if last is not None else 0


class TaskQuerySet(models.QuerySet):
    def filter_unarchived(self):
        return self.filter(archived_at__isnull=True)

    def filter_archived(self):
        return self.filter(archived_at__isnull=False)


class Task(models.Model):
    objects = TaskQuerySet.as_manager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    name = models.CharField(max_length=255)
    weight = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(MAX_TASK_WEIGHT)],
    )
    group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks',
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subtasks',
    )
    due_date = models.DateField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    group_position = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'created_at']

    def __str__(self):
        return self.name

    @classmethod
    def next_position(cls, user, parent):
        last = cls.objects.filter(user=user, parent=parent).aggregate(
            max_position=models.Max('position')
        )['max_position']
        return last + 1 if last is not None else 0

    @classmethod
    def next_group_position(cls, user, group):
        last = cls.objects.filter(
            user=user, group=group, parent__isnull=True
        ).aggregate(max_position=models.Max('group_position'))['max_position']
        return last + 1 if last is not None else 0

    def set_complete_with_subtasks(self, complete):
        self.completed_at = timezone.now() if complete else None
        self.save(update_fields=['completed_at'])
        self.subtasks.update(completed_at=self.completed_at)

    def set_archived_with_subtasks(self, archived):
        self.archived_at = timezone.now() if archived else None
        self.save(update_fields=['archived_at'])
        self.subtasks.update(archived_at=self.archived_at)

    @property
    def subtask_count(self):
        return len(self.subtasks.all())

    @property
    def completed_subtask_count(self):
        return sum(1 for subtask in self.subtasks.all() if subtask.completed_at)

    @property
    def is_due_today(self):
        return bool(self.due_date and self.due_date == timezone.localdate())

    @property
    def is_overdue(self):
        return bool(
            self.due_date
            and not self.completed_at
            and self.due_date < timezone.localdate()
        )
