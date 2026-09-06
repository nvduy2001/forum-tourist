from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserBadge
from .tasks import send_badge_awarded_email


@receiver(post_save, sender=UserBadge)
def on_user_badge_awarded(sender, instance, created, **kwargs):
    if created:
        send_badge_awarded_email.delay(instance.id)
