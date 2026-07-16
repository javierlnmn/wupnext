from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, UserPreferences


@receiver(post_save, sender=CustomUser)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        UserPreferences.objects.create(user=instance)
