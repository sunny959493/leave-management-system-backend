from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import LeaveTracker


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_leave_tracker(sender, instance, created, **kwargs):
    if created and not instance.is_staff:
        LeaveTracker.objects.create(user=instance)