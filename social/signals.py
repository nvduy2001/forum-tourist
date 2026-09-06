from django.db.models.signals import post_save
from django.dispatch import receiver

from gamification.services import add_points
from reviews.models import Review

from .models import ReviewVote, UserFollow
from .tasks import (
    notify_place_followers_of_new_review,
    send_helpful_vote_email,
    send_new_follower_email,
)


@receiver(post_save, sender=UserFollow)
def on_user_followed(sender, instance, created, **kwargs):
    if created:
        send_new_follower_email.delay(instance.id)


@receiver(post_save, sender=ReviewVote)
def on_review_voted_helpful(sender, instance, created, **kwargs):
    if not created:
        return
    from django.conf import settings

    add_points(instance.review.user, settings.POINTS_PER_HELPFUL_VOTE_RECEIVED)
    send_helpful_vote_email.delay(instance.id)


@receiver(post_save, sender=Review)
def on_review_created_notify_followers(sender, instance, created, **kwargs):
    if created:
        notify_place_followers_of_new_review.delay(instance.id)
