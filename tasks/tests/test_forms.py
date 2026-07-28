from django.test import TestCase

from accounts.tests.factories import UserFactory
from tasks.forms import GroupForm, TaskForm
from tasks.models import DEFAULT_GROUP_COLOR, GROUP_COLORS, MAX_TASK_WEIGHT

from .factories import GroupFactory, TaskFactory


class TaskFormTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def form(self, **data):
        data.setdefault('name', 'Write tests')
        return TaskForm(data=data, user=self.user)

    def test_name_is_stripped(self):
        form = self.form(name='  Buy milk  ')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'Buy milk')

    def test_blank_name_is_invalid(self):
        form = self.form(name='   ')
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_missing_weight_defaults_to_zero(self):
        form = self.form()
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['weight'], 0)

    def test_weight_below_range_is_clamped_to_zero(self):
        form = self.form(weight=-3)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['weight'], 0)

    def test_weight_above_range_is_clamped_to_max(self):
        form = self.form(weight=MAX_TASK_WEIGHT + 4)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['weight'], MAX_TASK_WEIGHT)

    def test_weight_within_range_is_kept(self):
        form = self.form(weight=3)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['weight'], 3)

    def test_group_resolves_when_owned_by_user(self):
        group = GroupFactory(user=self.user)
        form = self.form(group_id=group.id)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['group'], group)

    def test_group_of_another_user_is_ignored(self):
        group = GroupFactory(user=UserFactory())
        form = self.form(group_id=group.id)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['group'])

    def test_parent_resolves_when_owned_and_top_level(self):
        parent = TaskFactory(user=self.user)
        form = self.form(parent_id=parent.id)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['parent'], parent)

    def test_parent_of_another_user_is_ignored(self):
        parent = TaskFactory(user=UserFactory())
        form = self.form(parent_id=parent.id)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['parent'])

    def test_subtask_cannot_be_a_parent(self):
        top = TaskFactory(user=self.user)
        subtask = TaskFactory(user=self.user, parent=top)
        form = self.form(parent_id=subtask.id)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['parent'])

    def test_parent_forces_no_group(self):
        parent = TaskFactory(user=self.user)
        group = GroupFactory(user=self.user)
        form = self.form(parent_id=parent.id, group_id=group.id)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['parent'], parent)
        self.assertIsNone(form.cleaned_data['group'])

    def test_parent_forces_no_due_date(self):
        parent = TaskFactory(user=self.user)
        form = self.form(parent_id=parent.id, due_date='2026-07-21')
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['due_date'])


class GroupFormTests(TestCase):
    def test_name_is_stripped(self):
        form = GroupForm(data={'name': '  Work  '})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'Work')

    def test_blank_name_is_invalid(self):
        form = GroupForm(data={'name': '   '})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_palette_color_is_kept(self):
        color = GROUP_COLORS[3]['hex']
        form = GroupForm(data={'name': 'Work', 'color': color})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['color'], color)

    def test_color_outside_palette_falls_back_to_default(self):
        form = GroupForm(data={'name': 'Work', 'color': '#123456'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['color'], DEFAULT_GROUP_COLOR)

    def test_missing_color_falls_back_to_default(self):
        form = GroupForm(data={'name': 'Work'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['color'], DEFAULT_GROUP_COLOR)
