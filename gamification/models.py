from django.conf import settings
from django.db import models


class Badge(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='user_badges')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'badge'], name='unique_user_badge'),
        ]

    def __str__(self):
        return f'{self.user} — {self.badge}'


class SeasonalMission(models.Model):
    """Đại sứ khu vực theo mùa: Admin tạo mission theo region/category/khoảng thời gian."""

    name = models.CharField(max_length=255)
    region = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    required_count = models.PositiveIntegerField()
    badge = models.ForeignKey(Badge, on_delete=models.PROTECT, related_name='missions')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class MissionProgress(models.Model):
    mission = models.ForeignKey(SeasonalMission, on_delete=models.CASCADE, related_name='progresses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mission_progresses')
    progress_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['mission', 'user'], name='unique_mission_user_progress'),
        ]

    def __str__(self):
        return f'{self.user} — {self.mission} ({self.progress_count}/{self.mission.required_count})'
