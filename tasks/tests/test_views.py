from datetime import date, datetime

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.models import Group, Task

from .factories import GroupFactory, TaskFactory


class BoardClientTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class BoardViewTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("tasks:board"))
        self.assertEqual(response.status_code, 302)

    def test_renders_board(self):
        response = self.client.get(reverse("tasks:board"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/board.html")


class TaskCreateTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("tasks:task"), {"name": "Nope"})
        self.assertEqual(response.status_code, 302)

    def test_creates_task(self):
        response = self.client.post(reverse("tasks:task"), {"name": "Write tests"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "innerHTML:#group-nav")
        task = Task.objects.get(user=self.user)
        self.assertEqual(task.name, "Write tests")

    def test_clamps_weight_and_resolves_group(self):
        group = GroupFactory(user=self.user)
        self.client.post(
            reverse("tasks:task"),
            {"name": "Heavy", "weight": 99, "group_id": group.id},
        )
        task = Task.objects.get(user=self.user)
        self.assertEqual(task.weight, 5)
        self.assertEqual(task.group, group)

    def test_creates_subtask_with_parent(self):
        parent = TaskFactory(user=self.user)
        self.client.post(
            reverse("tasks:task"),
            {"name": "Sub", "parent_id": parent.id},
        )
        self.assertEqual(parent.subtasks.get().name, "Sub")

    def test_appends_to_the_end_of_position_and_group(self):
        group = GroupFactory(user=self.user)
        TaskFactory(user=self.user, position=0)
        TaskFactory(user=self.user, group=group, position=1, group_position=0)
        self.client.post(
            reverse("tasks:task"),
            {"name": "Newest", "group_id": group.id},
        )
        task = Task.objects.get(user=self.user, name="Newest")
        self.assertEqual(task.position, 2)
        self.assertEqual(task.group_position, 1)

    def test_invalid_form_creates_nothing(self):
        response = self.client.post(reverse("tasks:task"), {"name": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.exists())


class TaskEditTests(BoardClientTestCase):
    def test_requires_login(self):
        task = TaskFactory(user=self.user)
        self.client.logout()
        response = self.client.post(
            reverse("tasks:task"),
            {"task_id": task.id, "name": "New"},
        )
        self.assertEqual(response.status_code, 302)

    def test_updates_existing_task(self):
        task = TaskFactory(user=self.user, name="Old")
        self.client.post(
            reverse("tasks:task"),
            {"task_id": task.id, "name": "New", "weight": 3, "due_date": "2026-08-01"},
        )
        task.refresh_from_db()
        self.assertEqual(task.name, "New")
        self.assertEqual(task.weight, 3)
        self.assertEqual(task.due_date, date(2026, 8, 1))

    def test_cannot_edit_other_users_task(self):
        task = TaskFactory(user=UserFactory(), name="Theirs")
        self.client.post(
            reverse("tasks:task"),
            {"task_id": task.id, "name": "Hijacked"},
        )
        task.refresh_from_db()
        self.assertEqual(task.name, "Theirs")

    def test_moving_to_a_group_appends_to_that_groups_end(self):
        group = GroupFactory(user=self.user)
        TaskFactory(user=self.user, group=group, group_position=0)
        moving = TaskFactory(user=self.user, name="Move me", group_position=0)
        self.client.post(
            reverse("tasks:task"),
            {"task_id": moving.id, "name": "Move me", "group_id": group.id},
        )
        moving.refresh_from_db()
        self.assertEqual(moving.group, group)
        self.assertEqual(moving.group_position, 1)

    def test_editing_without_group_change_keeps_group_position(self):
        group = GroupFactory(user=self.user)
        task = TaskFactory(user=self.user, group=group, group_position=4)
        self.client.post(
            reverse("tasks:task"),
            {"task_id": task.id, "name": "Renamed", "group_id": group.id},
        )
        task.refresh_from_db()
        self.assertEqual(task.group_position, 4)


class TaskDeleteTests(BoardClientTestCase):
    def test_requires_login(self):
        task = TaskFactory(user=self.user)
        self.client.logout()
        response = self.client.delete(
            reverse("tasks:task-detail", args=[task.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_deletes_own_task(self):
        task = TaskFactory(user=self.user)
        response = self.client.delete(
            reverse("tasks:task-detail", args=[task.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_cannot_delete_other_users_task(self):
        task = TaskFactory(user=UserFactory())
        self.client.delete(reverse("tasks:task-detail", args=[task.id]))
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())


class ToggleCompleteTests(BoardClientTestCase):
    def setUp(self):
        super().setUp()
        self.task = TaskFactory(user=self.user)
        self.subtask = TaskFactory(user=self.user, parent=self.task)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("tasks:task-toggle-complete", args=[self.task.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_completes_task_and_cascades_to_subtasks(self):
        self.client.post(
            reverse("tasks:task-toggle-complete", args=[self.task.id])
        )
        self.task.refresh_from_db()
        self.subtask.refresh_from_db()
        self.assertIsNotNone(self.task.completed_at)
        self.assertIsNotNone(self.subtask.completed_at)

    def test_reopens_task_and_cascades(self):
        self.client.post(reverse("tasks:task-toggle-complete", args=[self.task.id]))
        self.client.post(reverse("tasks:task-toggle-complete", args=[self.task.id]))
        self.task.refresh_from_db()
        self.subtask.refresh_from_db()
        self.assertIsNone(self.task.completed_at)
        self.assertIsNone(self.subtask.completed_at)

    def test_missing_task_returns_404(self):
        response = self.client.post(
            reverse("tasks:task-toggle-complete", args=[999999])
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_toggle_other_users_task(self):
        other = TaskFactory(user=UserFactory())
        response = self.client.post(
            reverse("tasks:task-toggle-complete", args=[other.id])
        )
        self.assertEqual(response.status_code, 404)


class GroupCreateTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("tasks:group-create"), {"name": "Nope"})
        self.assertEqual(response.status_code, 302)

    def test_creates_group_and_redirects_via_hx_location(self):
        response = self.client.post(
            reverse("tasks:group-create"),
            {"name": "Work", "color": "#000000"},
        )
        self.assertEqual(response.status_code, 204)
        group = Group.objects.get(user=self.user)
        self.assertEqual(response["HX-Location"], f"/?group={group.id}")

    def test_position_is_one_past_the_highest(self):
        GroupFactory(user=self.user, position=0)
        GroupFactory(user=self.user, position=5)
        self.client.post(reverse("tasks:group-create"), {"name": "Newest"})
        newest = Group.objects.get(user=self.user, name="Newest")
        self.assertEqual(newest.position, 6)

    def test_first_group_gets_position_zero(self):
        self.client.post(reverse("tasks:group-create"), {"name": "First"})
        self.assertEqual(Group.objects.get(user=self.user).position, 0)

    def test_invalid_form_returns_board_without_creating(self):
        response = self.client.post(reverse("tasks:group-create"), {"name": "  "})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Group.objects.exists())


class GroupEditTests(BoardClientTestCase):
    def test_requires_login(self):
        group = GroupFactory(user=self.user)
        self.client.logout()
        response = self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": "Renamed", "color": group.color},
        )
        self.assertEqual(response.status_code, 302)

    def test_renames_group(self):
        group = GroupFactory(user=self.user, name="Old")
        response = self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": "Renamed", "color": group.color},
        )
        self.assertEqual(response.status_code, 200)
        group.refresh_from_db()
        self.assertEqual(group.name, "Renamed")

    def test_updates_color(self):
        group = GroupFactory(user=self.user)
        self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": group.name, "color": "#8b5cf6"},
        )
        group.refresh_from_db()
        self.assertEqual(group.color, "#8b5cf6")

    def test_refreshes_group_nav_with_new_name(self):
        group = GroupFactory(user=self.user, name="Old")
        response = self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": "Renamed", "color": group.color},
        )
        self.assertContains(response, "innerHTML:#group-nav")
        self.assertContains(response, "Renamed")

    def test_does_not_create_a_new_group(self):
        group = GroupFactory(user=self.user, name="Old")
        self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": "Renamed", "color": group.color},
        )
        self.assertEqual(Group.objects.filter(user=self.user).count(), 1)

    def test_cannot_edit_other_users_group(self):
        group = GroupFactory(user=UserFactory(), name="Theirs")
        self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": "Hijacked", "color": group.color},
        )
        group.refresh_from_db()
        self.assertEqual(group.name, "Theirs")


class GroupDeleteTests(BoardClientTestCase):
    def test_requires_login(self):
        group = GroupFactory(user=self.user)
        self.client.logout()
        response = self.client.delete(
            reverse("tasks:group-detail", args=[group.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_deletes_group(self):
        group = GroupFactory(user=self.user)
        response = self.client.delete(
            reverse("tasks:group-detail", args=[group.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_pushes_url_when_deleting_active_group(self):
        group = GroupFactory(user=self.user)
        url = reverse("tasks:group-detail", args=[group.id])
        response = self.client.delete(f"{url}?group={group.id}")
        self.assertEqual(response["HX-Push-Url"], reverse("tasks:board"))

    def test_no_push_url_when_group_not_active(self):
        group = GroupFactory(user=self.user)
        response = self.client.delete(
            reverse("tasks:group-detail", args=[group.id])
        )
        self.assertNotIn("HX-Push-Url", response)


class ArchiveViewTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("tasks:archive"))
        self.assertEqual(response.status_code, 302)

    def test_get_renders_archive_list(self):
        response = self.client.get(reverse("tasks:archive"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/partials/archive/list.html")

    def test_archives_completed_task(self):
        task = TaskFactory(user=self.user, completed=True)
        response = self.client.post(
            reverse("tasks:task-archive", args=[task.id])
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertIsNotNone(task.archived_at)

    def test_does_not_archive_incomplete_task(self):
        task = TaskFactory(user=self.user)
        self.client.post(reverse("tasks:task-archive", args=[task.id]))
        task.refresh_from_db()
        self.assertIsNone(task.archived_at)

    def test_deletes_archived_task(self):
        task = TaskFactory(user=self.user, completed=True, archived=True)
        response = self.client.delete(
            reverse("tasks:archive-task-detail", args=[task.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())


class UnarchiveViewTests(BoardClientTestCase):
    def test_requires_login(self):
        task = TaskFactory(user=self.user, completed=True, archived=True)
        self.client.logout()
        response = self.client.post(
            reverse("tasks:task-unarchive", args=[task.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_clears_archived_at(self):
        task = TaskFactory(user=self.user, completed=True, archived=True)
        response = self.client.post(
            reverse("tasks:task-unarchive", args=[task.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "innerHTML:#queue-content")
        task.refresh_from_db()
        self.assertIsNone(task.archived_at)

    def test_cannot_unarchive_other_users_task(self):
        task = TaskFactory(user=UserFactory(), completed=True, archived=True)
        self.client.post(reverse("tasks:task-unarchive", args=[task.id]))
        task.refresh_from_db()
        self.assertIsNotNone(task.archived_at)


class ArchivePeriodDeleteTests(BoardClientTestCase):
    def archive_task(self, year, month, **kwargs):
        task = TaskFactory(user=self.user, completed=True, **kwargs)
        moment = timezone.make_aware(datetime(year, month, 15, 12, 0))
        Task.objects.filter(pk=task.pk).update(archived_at=moment)
        return task

    def test_requires_login(self):
        self.client.logout()
        response = self.client.delete(
            reverse("tasks:archive-period-delete", args=["2026-07"])
        )
        self.assertEqual(response.status_code, 302)

    def test_deletes_every_task_in_the_month(self):
        a = self.archive_task(2026, 7)
        b = self.archive_task(2026, 7)
        response = self.client.delete(
            reverse("tasks:archive-period-delete", args=["2026-07"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nothing archived")
        self.assertFalse(Task.objects.filter(pk__in=[a.pk, b.pk]).exists())

    def test_leaves_other_months_untouched(self):
        july = self.archive_task(2026, 7)
        may = self.archive_task(2026, 5)
        self.client.delete(reverse("tasks:archive-period-delete", args=["2026-07"]))
        self.assertFalse(Task.objects.filter(pk=july.pk).exists())
        self.assertTrue(Task.objects.filter(pk=may.pk).exists())

    def test_cascades_to_subtasks(self):
        parent = self.archive_task(2026, 7)
        subtask = TaskFactory(user=self.user, parent=parent)
        self.client.delete(reverse("tasks:archive-period-delete", args=["2026-07"]))
        self.assertFalse(Task.objects.filter(pk=subtask.pk).exists())

    def test_does_not_delete_unarchived_tasks(self):
        today = timezone.localdate()
        pending = TaskFactory(user=self.user, due_date=today)
        archived = self.archive_task(today.year, today.month)
        self.client.delete(
            reverse("tasks:archive-period-delete", args=[today.strftime("%Y-%m")])
        )
        self.assertTrue(Task.objects.filter(pk=pending.pk).exists())
        self.assertFalse(Task.objects.filter(pk=archived.pk).exists())

    def test_scoped_to_user(self):
        mine = self.archive_task(2026, 7)
        other = TaskFactory(user=UserFactory(), completed=True)
        Task.objects.filter(pk=other.pk).update(
            archived_at=timezone.make_aware(datetime(2026, 7, 15, 12, 0))
        )
        self.client.delete(reverse("tasks:archive-period-delete", args=["2026-07"]))
        self.assertFalse(Task.objects.filter(pk=mine.pk).exists())
        self.assertTrue(Task.objects.filter(pk=other.pk).exists())

    def test_invalid_period_returns_400(self):
        response = self.client.delete(
            reverse("tasks:archive-period-delete", args=["not-a-period"])
        )
        self.assertEqual(response.status_code, 400)


class TaskReorderTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("tasks:task-reorder"))
        self.assertEqual(response.status_code, 302)

    def test_unfiltered_view_reindexes_global_position(self):
        a = TaskFactory(user=self.user, position=0)
        b = TaskFactory(user=self.user, position=1)
        c = TaskFactory(user=self.user, position=2)
        response = self.client.post(
            reverse("tasks:task-reorder"),
            {"order": f"{c.id},{a.id},{b.id}"},
        )
        self.assertEqual(response.status_code, 200)
        c.refresh_from_db()
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual([c.position, a.position, b.position], [0, 1, 2])

    def test_group_view_reindexes_group_position_only(self):
        group = GroupFactory(user=self.user)
        a = TaskFactory(user=self.user, group=group, position=7, group_position=0)
        b = TaskFactory(user=self.user, group=group, position=9, group_position=1)
        response = self.client.post(
            f"{reverse('tasks:task-reorder')}?group={group.id}",
            {"order": f"{b.id},{a.id}"},
        )
        self.assertEqual(response.status_code, 200)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual([b.group_position, a.group_position], [0, 1])
        self.assertEqual([a.position, b.position], [7, 9])

    def test_rejects_partial_scope(self):
        a = TaskFactory(user=self.user, position=0)
        b = TaskFactory(user=self.user, position=1)
        c = TaskFactory(user=self.user, position=2)
        response = self.client.post(
            reverse("tasks:task-reorder"),
            {"order": f"{c.id},{a.id}"},
        )
        self.assertEqual(response.status_code, 400)
        a.refresh_from_db()
        b.refresh_from_db()
        c.refresh_from_db()
        self.assertEqual([a.position, b.position, c.position], [0, 1, 2])

    def test_rejects_foreign_id(self):
        mine = TaskFactory(user=self.user, position=0)
        other = TaskFactory(user=UserFactory(), position=0)
        response = self.client.post(
            reverse("tasks:task-reorder"),
            {"order": f"{mine.id},{other.id}"},
        )
        self.assertEqual(response.status_code, 400)
        mine.refresh_from_db()
        self.assertEqual(mine.position, 0)

    def test_completed_tasks_are_outside_the_pending_scope(self):
        pending = TaskFactory(user=self.user, position=0)
        completed = TaskFactory(user=self.user, completed=True, position=1)
        response = self.client.post(
            reverse("tasks:task-reorder"),
            {"order": f"{pending.id},{completed.id}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_noop_when_scope_empty(self):
        response = self.client.post(reverse("tasks:task-reorder"), {"order": ""})
        self.assertEqual(response.status_code, 200)


class GroupReorderTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("tasks:group-reorder"))
        self.assertEqual(response.status_code, 302)

    def test_reindexes_positions_to_submitted_order(self):
        a = GroupFactory(user=self.user, position=0)
        b = GroupFactory(user=self.user, position=1)
        response = self.client.post(
            reverse("tasks:group-reorder"),
            {"order": f"{b.id},{a.id}"},
        )
        self.assertEqual(response.status_code, 200)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual([b.position, a.position], [0, 1])

    def test_rejects_partial_scope(self):
        a = GroupFactory(user=self.user, position=0)
        b = GroupFactory(user=self.user, position=1)
        GroupFactory(user=self.user, position=2)
        response = self.client.post(
            reverse("tasks:group-reorder"),
            {"order": f"{b.id},{a.id}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_foreign_id(self):
        mine = GroupFactory(user=self.user, position=0)
        other = GroupFactory(user=UserFactory(), position=0)
        response = self.client.post(
            reverse("tasks:group-reorder"),
            {"order": f"{mine.id},{other.id}"},
        )
        self.assertEqual(response.status_code, 400)
        mine.refresh_from_db()
        self.assertEqual(mine.position, 0)


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class ManageGroupsTests(BoardClientTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("tasks:board"))
        self.assertEqual(response.status_code, 302)

    TRIGGER = "CustomEvent('open-manage-groups')"

    def test_board_renders_the_manage_drawer_and_its_trigger(self):
        GroupFactory(user=self.user)
        response = self.client.get(reverse("tasks:board"))
        self.assertContains(response, 'id="manage-groups"')
        self.assertContains(response, self.TRIGGER)

    def test_trigger_is_hidden_when_there_are_no_groups(self):
        response = self.client.get(reverse("tasks:board"))
        self.assertNotContains(response, self.TRIGGER)

    def test_list_offers_every_group_to_the_reorder_endpoint(self):
        first = GroupFactory(user=self.user, position=0)
        second = GroupFactory(user=self.user, position=1)
        response = self.client.get(reverse("tasks:board"))
        self.assertContains(response, reverse("tasks:group-reorder"))
        self.assertContains(response, f'data-id="{first.id}"')
        self.assertContains(response, f'data-id="{second.id}"')

    def test_board_response_refreshes_the_manage_list(self):
        group = GroupFactory(user=self.user, name="Old")
        response = self.client.post(
            reverse("tasks:group-create"),
            {"group_id": group.id, "name": "Renamed", "color": group.color},
        )
        self.assertContains(response, "innerHTML:#manage-groups")
        self.assertContains(response, "Renamed")

    def test_deleting_a_group_refreshes_the_manage_list(self):
        group = GroupFactory(user=self.user, name="Doomed")
        response = self.client.delete(
            reverse("tasks:group-detail", args=[group.id]),
        )
        self.assertContains(response, "innerHTML:#manage-groups")
        self.assertNotContains(response, "Doomed")
