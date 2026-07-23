from django.core.cache import cache
from django.test import RequestFactory, TestCase

from common.context_processors import settings
from common.models import SiteSettings


class SiteSettingsTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_save_forces_singleton_pk(self):
        first = SiteSettings(notifications_disabled_channels=[])
        first.save()
        second = SiteSettings(notifications_disabled_channels=["email"])
        second.save()
        self.assertEqual(first.pk, 1)
        self.assertEqual(second.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)
        saved = SiteSettings.objects.get()
        self.assertEqual(saved.notifications_disabled_channels, ["email"])

    def test_delete_is_a_noop(self):
        obj = SiteSettings.objects.create()
        obj.delete()
        self.assertTrue(SiteSettings.objects.filter(pk=1).exists())

    def test_load_creates_and_caches_instance(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        loaded = SiteSettings.load()
        self.assertEqual(loaded.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(cache.get("SiteSettings").pk, 1)

    def test_load_returns_existing_instance(self):
        SiteSettings.objects.create(notifications_disabled_channels=["email"])
        cache.clear()
        loaded = SiteSettings.load()
        self.assertEqual(loaded.notifications_disabled_channels, ["email"])
        self.assertEqual(SiteSettings.objects.count(), 1)


class SettingsContextProcessorTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_exposes_site_settings(self):
        request = RequestFactory().get("/")
        context = settings(request)
        self.assertIn("settings", context)
        self.assertIsInstance(context["settings"], SiteSettings)
