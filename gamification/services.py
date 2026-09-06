from django.conf import settings
from django.db import transaction
from django.db.models import F


def add_points(user, amount):
    """Cộng điểm uy tín cho user (dùng F() để tránh race condition)."""
    with transaction.atomic():
        user.__class__.objects.filter(pk=user.pk).update(points=F('points') + amount)
    user.refresh_from_db(fields=['points'])


def get_member_tier(points):
    for threshold, tier_name in settings.MEMBER_TIER_THRESHOLDS:
        if points >= threshold:
            return tier_name
    return settings.MEMBER_TIER_THRESHOLDS[-1][1]
