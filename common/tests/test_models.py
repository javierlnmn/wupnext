from django.test import RequestFactory, TestCase

from common.context_processors import settings
from common.models import SiteSettings


class SiteSettingsTests(TestCase):
    def test_save_forces_singleton_pk(self):
        first = SiteSettings(notification_channels_email_enabled=True)
        first.save()
        second = SiteSettings(notification_channels_email_enabled=False)
        second.save()
        self.assertEqual(first.pk, 1)
        self.assertEqual(second.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)
        saved = SiteSettings.objects.get()
        self.assertFalse(saved.notification_channels_email_enabled)

    def test_delete_is_a_noop(self):
        obj = SiteSettings.objects.create()
        obj.delete()
        self.assertTrue(SiteSettings.objects.filter(pk=1).exists())

    def test_load_creates_the_instance_when_missing(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        loaded = SiteSettings.load()
        self.assertEqual(loaded.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_load_returns_existing_instance(self):
        SiteSettings.objects.create(notification_channels_email_enabled=False)
        loaded = SiteSettings.load()
        self.assertFalse(loaded.notification_channels_email_enabled)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_load_reflects_a_saved_change_immediately(self):
        site = SiteSettings.load()
        site.notification_channels_email_enabled = False
        site.save()

        self.assertFalse(SiteSettings.load().notification_channels_email_enabled)


class SettingsContextProcessorTests(TestCase):
    def test_exposes_site_settings(self):
        request = RequestFactory().get("/")
        context = settings(request)
        self.assertIn("settings", context)
        self.assertIsInstance(context["settings"], SiteSettings)
