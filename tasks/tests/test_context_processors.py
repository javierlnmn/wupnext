from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.context_processors import sidebar
from tasks.models import DEFAULT_GROUP_COLOR, GROUP_COLORS, DueFilter

from .factories import GroupFactory, TaskFactory


class SidebarTestCase(TestCase):
    def sidebar_context(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return sidebar(request)


class SidebarAuthTests(SidebarTestCase):
    def test_returns_empty_for_anonymous_user(self):
        self.assertEqual(self.sidebar_context(AnonymousUser()), {})

    def test_exposes_palette_and_due_filter(self):
        context = self.sidebar_context(UserFactory())
        self.assertEqual(context["task_group_palette"], GROUP_COLORS)
        self.assertEqual(context["default_task_group_color"], DEFAULT_GROUP_COLOR)
        self.assertIs(context["DueFilter"], DueFilter)


class SidebarCountTests(SidebarTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.group_a = GroupFactory(user=self.user)
        self.group_b = GroupFactory(user=self.user)

    def test_pending_count_per_group(self):
        TaskFactory(user=self.user, group=self.group_a)
        TaskFactory(user=self.user, group=self.group_a)
        TaskFactory(user=self.user, group=self.group_b)
        context = self.sidebar_context(self.user)
        counts = {group.id: group.pending_count for group in context["task_groups"]}
        self.assertEqual(counts[self.group_a.id], 2)
        self.assertEqual(counts[self.group_b.id], 1)

    def test_all_tasks_count_includes_ungrouped(self):
        TaskFactory(user=self.user, group=self.group_a)
        TaskFactory(user=self.user)
        self.assertEqual(self.sidebar_context(self.user)["all_tasks_count"], 2)

    def test_counts_exclude_completed_archived_and_subtasks(self):
        parent = TaskFactory(user=self.user, group=self.group_a)
        TaskFactory(user=self.user, group=self.group_a, parent=parent)
        TaskFactory(user=self.user, group=self.group_a, completed=True)
        TaskFactory(user=self.user, group=self.group_a, archived=True)
        context = self.sidebar_context(self.user)
        counts = {group.id: group.pending_count for group in context["task_groups"]}
        self.assertEqual(counts[self.group_a.id], 1)
        self.assertEqual(context["all_tasks_count"], 1)

    def test_counts_are_scoped_to_user(self):
        other = UserFactory()
        TaskFactory(user=other, group=GroupFactory(user=other))
        TaskFactory(user=self.user, group=self.group_a)
        context = self.sidebar_context(self.user)
        self.assertEqual(context["all_tasks_count"], 1)
        self.assertEqual(len(context["task_groups"]), 2)

    def test_today_and_overdue_counts(self):
        today = timezone.localdate()
        TaskFactory(user=self.user, due_date=today)
        TaskFactory(user=self.user, due_date=today - timedelta(days=1))
        TaskFactory(user=self.user, due_date=today - timedelta(days=3))
        TaskFactory(user=self.user, due_date=today + timedelta(days=1))
        context = self.sidebar_context(self.user)
        self.assertEqual(context["today_count"], 1)
        self.assertEqual(context["overdue_count"], 2)

    def test_overdue_count_excludes_completed(self):
        today = timezone.localdate()
        TaskFactory(user=self.user, due_date=today - timedelta(days=1), completed=True)
        self.assertEqual(self.sidebar_context(self.user)["overdue_count"], 0)
