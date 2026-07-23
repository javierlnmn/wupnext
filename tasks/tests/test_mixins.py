from datetime import datetime, timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.views import View

from accounts.tests.factories import UserFactory
from tasks.mixins import ArchiveMixin, BoardMixin
from tasks.models import MAX_TASK_WEIGHT, DueFilter

from .factories import GroupFactory, TaskFactory


class BoardHost(BoardMixin, View):
    pass


class ArchiveHost(ArchiveMixin, View):
    pass


class BoardMixinTestCase(TestCase):
    def board_view(self, user, **params):
        request = RequestFactory().get("/", params)
        request.user = user
        view = BoardHost()
        view.setup(request)
        return view


class ActiveGroupTests(BoardMixinTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory(user=self.user)

    def test_resolves_group_from_query(self):
        view = self.board_view(self.user, group=self.group.id)
        self.assertEqual(view.active_group(), self.group)

    def test_none_without_group_param(self):
        self.assertIsNone(self.board_view(self.user).active_group())

    def test_none_for_non_digit_value(self):
        self.assertIsNone(self.board_view(self.user, group="all").active_group())

    def test_none_for_other_users_group(self):
        other_group = GroupFactory(user=UserFactory())
        view = self.board_view(self.user, group=other_group.id)
        self.assertIsNone(view.active_group())


class BoardContextFilterTests(BoardMixinTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.today = timezone.localdate()
        self.group = GroupFactory(user=self.user)

    def test_unfiltered_splits_pending_and_completed(self):
        pending = TaskFactory(user=self.user)
        completed = TaskFactory(user=self.user, completed=True)
        context = self.board_view(self.user).board_context()
        self.assertIn(pending, context["pending_tasks"])
        self.assertIn(completed, context["completed_tasks"])
        self.assertNotIn(completed, context["pending_tasks"])

    def test_excludes_archived_and_subtasks(self):
        parent = TaskFactory(user=self.user)
        TaskFactory(user=self.user, parent=parent)
        TaskFactory(user=self.user, archived=True)
        context = self.board_view(self.user).board_context()
        self.assertEqual(list(context["pending_tasks"]), [parent])

    def test_scoped_to_user(self):
        TaskFactory(user=UserFactory())
        mine = TaskFactory(user=self.user)
        context = self.board_view(self.user).board_context()
        self.assertEqual(list(context["pending_tasks"]), [mine])

    def test_group_filter(self):
        in_group = TaskFactory(user=self.user, group=self.group)
        TaskFactory(user=self.user)
        context = self.board_view(self.user, group=self.group.id).board_context()
        self.assertEqual(list(context["pending_tasks"]), [in_group])
        self.assertEqual(context["active_task_group"], self.group)

    def test_today_filter(self):
        due_today = TaskFactory(user=self.user, due_date=self.today)
        TaskFactory(user=self.user, due_date=self.today - timedelta(days=1))
        context = self.board_view(self.user, due=DueFilter.TODAY).board_context()
        self.assertEqual(list(context["pending_tasks"]), [due_today])
        self.assertEqual(context["active_due"], DueFilter.TODAY)

    def test_overdue_filter_excludes_completed(self):
        overdue = TaskFactory(user=self.user, due_date=self.today - timedelta(days=1))
        TaskFactory(
            user=self.user,
            due_date=self.today - timedelta(days=1),
            completed=True,
        )
        context = self.board_view(self.user, due=DueFilter.OVERDUE).board_context()
        self.assertEqual(list(context["pending_tasks"]), [overdue])

    def test_invalid_due_value_ignored(self):
        context = self.board_view(self.user, due="someday").board_context()
        self.assertIsNone(context["active_due"])

    def test_exposes_max_task_weight_and_today(self):
        context = self.board_view(self.user).board_context()
        self.assertEqual(context["max_task_weight"], MAX_TASK_WEIGHT)
        self.assertEqual(context["today"], self.today)


class BoardQueryTests(BoardMixinTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory(user=self.user)

    def test_empty_without_filters(self):
        self.assertEqual(self.board_view(self.user).board_context()["board_query"], "")

    def test_group_only(self):
        query = self.board_view(self.user, group=self.group.id).board_context()
        self.assertEqual(query["board_query"], f"?group={self.group.id}")

    def test_due_only(self):
        query = self.board_view(self.user, due=DueFilter.TODAY).board_context()
        self.assertEqual(query["board_query"], "?due=today")

    def test_group_and_due_combined(self):
        query = self.board_view(
            self.user, group=self.group.id, due=DueFilter.OVERDUE
        ).board_context()
        self.assertEqual(
            query["board_query"], f"?group={self.group.id}&due=overdue"
        )


class ArchiveContextTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def archive_view(self, user, **params):
        request = RequestFactory().get("/", params)
        request.user = user
        view = ArchiveHost()
        view.setup(request)
        return view

    def archive_task(self, year, month, day=15):
        task = TaskFactory(user=self.user, completed=True)
        moment = timezone.make_aware(datetime(year, month, day, 12, 0))
        type(task).objects.filter(pk=task.pk).update(archived_at=moment)
        return task

    def test_empty_when_nothing_archived(self):
        context = self.archive_view(self.user).archive_context()
        self.assertEqual(context["archive_periods"], [])
        self.assertIsNone(context["active_period"])
        self.assertEqual(list(context["archived_tasks"]), [])

    def test_periods_ordered_most_recent_first_with_counts(self):
        self.archive_task(2026, 7)
        self.archive_task(2026, 7)
        self.archive_task(2026, 5)
        context = self.archive_view(self.user).archive_context()
        values = [p["value"] for p in context["archive_periods"]]
        counts = {p["value"]: p["count"] for p in context["archive_periods"]}
        self.assertEqual(values, ["2026-07", "2026-05"])
        self.assertEqual(counts["2026-07"], 2)
        self.assertEqual(counts["2026-05"], 1)

    def test_active_period_defaults_to_most_recent(self):
        self.archive_task(2026, 7)
        self.archive_task(2026, 5)
        context = self.archive_view(self.user).archive_context()
        self.assertEqual(context["active_period"], "2026-07")

    def test_requested_period_selects_that_month(self):
        recent = self.archive_task(2026, 7)
        older = self.archive_task(2026, 5)
        context = self.archive_view(self.user, period="2026-05").archive_context()
        self.assertEqual(context["active_period"], "2026-05")
        self.assertIn(older, context["archived_tasks"])
        self.assertNotIn(recent, context["archived_tasks"])

    def test_invalid_period_falls_back_to_default(self):
        self.archive_task(2026, 7)
        context = self.archive_view(self.user, period="1999-01").archive_context()
        self.assertEqual(context["active_period"], "2026-07")

    def test_scoped_to_user(self):
        mine = self.archive_task(2026, 7)
        other = TaskFactory(user=UserFactory(), completed=True, archived=True)
        context = self.archive_view(self.user).archive_context()
        self.assertIn(mine, context["archived_tasks"])
        self.assertNotIn(other, context["archived_tasks"])
