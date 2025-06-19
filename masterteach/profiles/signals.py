from django.db.models.signals import post_save
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile, CEFRStats

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a profile when a new user is created."""
    if created:
        Profile.objects.create(user=instance)
        CEFRStats.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when the user is saved."""
    instance.profile.save() 