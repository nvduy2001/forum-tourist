from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from gamification.models import Badge, MissionProgress, SeasonalMission, UserBadge
from gamification.services import add_points
from places.models import Place

from .models import Comment, Review
from .tasks import send_new_comment_email

DISCOVERER_BADGE_SLUG = 'nguoi-khai-pha'


@receiver(post_save, sender=Review)
def on_review_saved(sender, instance, created, **kwargs):
    if not created:
        return
    _increment_review_count(instance.place_id)
    _update_mission_progress(instance)
    add_points(instance.user, settings.POINTS_PER_REVIEW)


@receiver(post_save, sender=Comment)
def on_comment_created(sender, instance, created, **kwargs):
    if created:
        send_new_comment_email.delay(instance.id)
        add_points(instance.user, settings.POINTS_PER_COMMENT)


@receiver(post_delete, sender=Review)
def on_review_deleted(sender, instance, **kwargs):
    Place.objects.filter(pk=instance.place_id, review_count__gt=0).update(
        review_count=F('review_count') - 1
    )


def _increment_review_count(place_id):
    """Khám phá địa điểm mới: review_count đếm sẵn, 0 -> 1 thì gắn badge 'Người khai phá'."""
    with transaction.atomic():
        place = Place.objects.select_for_update().get(pk=place_id)
        place.review_count = F('review_count') + 1
        place.save(update_fields=['review_count'])
        place.refresh_from_db(fields=['review_count'])

        if place.review_count == 1:
            first_review = place.reviews.order_by('created_at').first()
            if first_review is not None:
                badge, _ = Badge.objects.get_or_create(
                    slug=DISCOVERER_BADGE_SLUG,
                    defaults={
                        'name': 'Người khai phá',
                        'description': 'Là người đầu tiên đánh giá một địa điểm mới.',
                    },
                )
                UserBadge.objects.get_or_create(user=first_review.user, badge=badge)


def _update_mission_progress(review):
    """Đại sứ khu vực theo mùa: review hợp lệ (đúng region/category, trong thời hạn mission) -> progress += 1."""
    today = timezone.localdate()
    place = review.place
    missions = SeasonalMission.objects.filter(
        is_active=True,
        region=place.region,
        category=place.category,
        start_date__lte=today,
        end_date__gte=today,
    )
    for mission in missions:
        with transaction.atomic():
            progress, _ = MissionProgress.objects.select_for_update().get_or_create(
                mission=mission, user=review.user,
            )
            if progress.completed_at:
                continue

            progress.progress_count = F('progress_count') + 1
            progress.save(update_fields=['progress_count'])
            progress.refresh_from_db(fields=['progress_count'])

            if progress.progress_count >= mission.required_count:
                progress.completed_at = timezone.now()
                progress.save(update_fields=['completed_at'])
                UserBadge.objects.get_or_create(user=review.user, badge=mission.badge)
