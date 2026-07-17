from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

GROUP_COLORS = [
    {"name": "Clay", "hex": "#d1793f"},
    {"name": "Amber", "hex": "#f59e0b"},
    {"name": "Olive", "hex": "#8a9b6e"},
    {"name": "Emerald", "hex": "#10b981"},
    {"name": "Sky", "hex": "#38bdf8"},
    {"name": "Violet", "hex": "#8b5cf6"},
    {"name": "Rose", "hex": "#f43f5e"},
    {"name": "Slate", "hex": "#64748b"},
]
DEFAULT_GROUP_COLOR = GROUP_COLORS[0]["hex"]
GROUP_COLOR_VALUES = {color["hex"] for color in GROUP_COLORS}

MAX_TASK_WEIGHT = 5


class Group(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_groups",
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=9, default=DEFAULT_GROUP_COLOR)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]

    def __str__(self):
        return self.name


class Task(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
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
        related_name="tasks",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.name

    @property
    def subtask_count(self):
        return len(self.subtasks.all())

    @property
    def completed_subtask_count(self):
        return sum(1 for subtask in self.subtasks.all() if subtask.completed_at)
