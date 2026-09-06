from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """2 actor duy nhất: User + Admin. Chủ địa điểm chỉ là User có is_business_owner=True."""

    is_business_owner = models.BooleanField(default=False)
    owned_place = models.ForeignKey(
        'places.Place',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='owners',
    )

    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
    bio = models.TextField(blank=True)

    # Điểm thưởng & uy tín — cộng dồn khi viết review/comment/được vote hữu ích
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username

    @property
    def member_tier(self):
        from gamification.services import get_member_tier

        return get_member_tier(self.points)
